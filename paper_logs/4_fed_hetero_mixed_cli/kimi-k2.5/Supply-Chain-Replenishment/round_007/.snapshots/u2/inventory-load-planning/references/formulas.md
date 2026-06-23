# Load Planning Formula Reference

## Input Parameters

| Parameter | Description | Typical Source |
|-----------|-------------|----------------|
| AsOfDate | Planning baseline date | Row 0, Column B |
| HorizonEnd | End of planning period | Row 0, Column D |
| CasesPerPallet | Conversion factor | Load Config / Pallet Defaults sheet |
| OnFloorCases | Current inventory | Stock Snapshot / Rack Snapshot / Lane Snapshot / Branch Stock |
| DailySalesCases | Velocity rate | Stock Snapshot / Rack Snapshot / Lane Snapshot / Branch Stock |
| ScheduledInbounds | Future arrivals | Scheduled Inbounds / Booking Feed / Arrival Board / Planned Transfers |
| Status | Shipment/Booking reliability status | Expected Arrivals / Booking Feed / Arrival Board / Planned Transfers |
| Lane | Storage location/zone | Lane Snapshot |
| Branch | Location identifier | Branch Stock |

## Deduplication Requirements

When source data contains duplicate identifiers (e.g., Transfer_ID appears multiple times), deduplicate **FIRST** before status filtering.

### Pattern 1: Latest Date Wins
```python
def deduplicate_transfers(df, id_col='Transfer_ID', date_col='Transfer_Date'):
    """
    Keep only the latest date entry per ID.
    Handles cases where a transfer was revised from Tentative to Confirmed with new date.
    """
    df = df.sort_values([id_col, date_col], ascending=[True, False])
    return df.drop_duplicates(subset=[id_col], keep='first')
```

### Pattern 2: Highest Revision Wins (R5)
When a numeric `Revision` or `Version` column exists, keep the row with highest revision:
```python
def deduplicate_by_revision(df, id_col='Transfer_ID', rev_col='Revision'):
    """
    Keep highest revision entry per ID.
    Use when booking/transfer feed has Revision column indicating updates.
    """
    df[rev_col] = pd.to_numeric(df[rev_col], errors='coerce')
    df = df.sort_values(rev_col, ascending=False)
    return df.drop_duplicates(subset=[id_col], keep='first')
```

### Pattern 3: Status Priority
```python
def deduplicate_by_status(df, id_col='Transfer_ID', status_col='Status',
                          priority=['Confirmed', 'Tentative', 'Draft']):
    """
    Keep highest priority status per ID, breaking ties by latest date.
    """
    status_order = {s: i for i, s in enumerate(priority)}
    df['status_rank'] = df[status_col].map(status_order)
    df = df.sort_values([id_col, 'status_rank', 'Transfer_Date'],
                        ascending=[True, True, False])
    return df.drop_duplicates(subset=[id_col], keep='first').drop('status_rank', axis=1)
```

## Status Value Reference

Different source files use different status terminologies. Map and filter appropriately:

| Status Column Type | Include Values | Exclude Values |
|-------------------|----------------|----------------|
| Dock_Status | Committed, Arranged, Confirmed, At Dock, In Transit | Tentative, Pending, Planned, Forecasted, Requested |
| Booking_State | Firm, Locked, Confirmed | Tentative, Hold, Pending, Requested |
| Shipment_Status | Confirmed, In Transit, Arrived | Planned, Expected, Cancelled |
| Load Status | Ready, Docked, Confirmed | Draft, Cancelled, Pending, Tentative |
| Status (Transfers) | Confirmed | Tentative, Cancelled, Draft, Pending |

## Data Cleaning Requirements

Before performing calculations, clean input data to handle real-world quality issues:

### Filter Null Identifiers
```python
# Remove rows with null/None/NaN SKU or Item_Code
stock_data = stock_data[stock_data['Item_Code'].notna()]
inbounds = inbounds[inbounds['Item_Code'].notna()]
```

### Handle Invalid Dates
```python
# Convert to datetime with error coercion, then drop invalid
inbounds['Arrival_Date'] = pd.to_datetime(inbounds['Arrival_Date'], errors='coerce')
inbounds = inbounds[inbounds['Arrival_Date'].notna()]
```

### Handle Invalid Numeric Values
```python
stock_data['On_Floor_Cases'] = pd.to_numeric(stock_data['On_Floor_Cases'], errors='coerce')
stock_data = stock_data[stock_data['On_Floor_Cases'].notna()]
```

### Remove Duplicate IDs
```python
# Critical for transfer data with revised dates
if 'Transfer_ID' in inbounds.columns:
    inbounds = inbounds.sort_values(['Transfer_ID', 'Transfer_Date'], 
                                    ascending=[True, False])
    inbounds = inbounds.drop_duplicates(subset=['Transfer_ID'], keep='first')
```

## Lane Section Parsing

For Excel files with section headers indicating lanes/zones:

```python
def parse_lane_sections(df):
    """
    Parse DataFrame with 'Lane: XXX' section headers.
    Returns DataFrame with Lane, SKU, Cases_On_Hand, Daily_Pull columns.
    """
    records = []
    current_lane = None
    
    for _, row in df.iterrows():
        first_col = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ''
        
        if first_col.startswith('Lane:'):
            current_lane = first_col.split(':', 1)[1].strip()
        elif first_col in ['SKU', 'nan', 'NaN'] or pd.isna(row.iloc[0]):
            continue  # Skip header rows and empty rows
        elif current_lane and pd.notna(row.iloc[0]):
            records.append({
                'Lane': current_lane,
                'SKU': row.iloc[0],
                'Cases_On_Hand': pd.to_numeric(row.iloc[1], errors='coerce'),
                'Daily_Pull': pd.to_numeric(row.iloc[2], errors='coerce')
            })
    
    result = pd.DataFrame(records)
    return result.dropna(subset=['SKU', 'Cases_On_Hand'])
```

## Calculation Specifications

### 1. Current Days On Hand
**Formula**: `OnFloorCases / DailySalesCases`

**Edge Cases**: 
- If DailySalesCases is 0, set to 999 to avoid division by zero
- Represents days until stock depletion at current velocity

### 2. Projected Stock-Out Date
**Formula**: `AsOfDate + floor(CurrentDaysOnHand)`

**Notes**:
- Use `math.floor()` to round down to whole days
- Add as `pd.DateOffset(days=floor_value)` or convert to datetime.date
- Ensure AsOfDate is datetime.date type to avoid type errors

### 3. Planning Days
**Formula**: `(HorizonEnd - AsOfDate).days`

**Type Safety**:
```python
# Ensure both are datetime.date objects
as_of_date = pd.to_datetime(as_of_date).date()
horizon_end = pd.to_datetime(horizon_end).date()
planning_days = (horizon_end - as_of_date).days
```

### 4. Inbound Cases By Horizon
**Formula**: `Sum(CasesDue) where ArrivalDate <= HorizonEnd AND Status in [reliable_values]`

**Implementation**:
```python
# Clean data first
inbounds['Arrival_Date'] = pd.to_datetime(inbounds['Arrival_Date'], errors='coerce')
inbounds = inbounds[inbounds['Arrival_Date'].notna()]
inbounds = inbounds[inbounds['Item_Code'].notna()]

# Deduplicate if Transfer_ID exists
if 'Transfer_ID' in inbounds.columns:
    inbounds = inbounds.sort_values(['Transfer_ID', 'Arrival_Date'], 
                                    ascending=[True, False])
    inbounds = inbounds.drop_duplicates(subset=['Transfer_ID'], keep='first')

# Filter by status if column exists
if 'Dock_Status' in inbounds.columns:
    reliable = ['Committed', 'Arranged', 'Confirmed']
    inbounds = inbounds[inbounds['Dock_Status'].isin(reliable)]
elif 'Booking_State' in inbounds.columns:
    reliable = ['Firm', 'Locked']
    inbounds = inbounds[inbounds['Booking_State'].isin(reliable)]
elif 'Load Status' in inbounds.columns:
    reliable = ['Ready', 'Docked', 'Confirmed']
    inbounds = inbounds[inbounds['Load Status'].isin(reliable)]
elif 'Status' in inbounds.columns:
    reliable = ['Confirmed']
    inbounds = inbounds[inbounds['Status'].isin(reliable)]

item_inbounds = inbounds[inbounds['Item_Code'] == item]
inbound_by_horizon = item_inbounds[
    item_inbounds['Arrival_Date'] <= horizon_end
]['Cases_Due'].sum()
```

### 5. Remaining Demand Cases
**Formula**: `DailySalesCases * PlanningDays`

### 6. Additional Cases Needed
**Formula**: `max(0, RemainingDemand - OnFloorCases - InboundByHorizon)`

**Critical**: Never return negative values. Use `max(0, result)`.

### 7. Pallets Required
**Formula**: 
- If AdditionalCasesNeeded > 0: `ceil(AdditionalCasesNeeded / CasesPerPallet)`
- Else: 0

### 8. Earlier Delivery Required
**Formula**: `RequiredDeliveryDate < EarliestInboundDate`

**Where**:
- RequiredDeliveryDate = ProjectedOOSDate
- EarliestInboundDate = min(ArrivalDate) for the item (None if no inbounds)

**Logic**: TRUE if the stock-out happens before any scheduled inbound arrives.

### 9. Delivered Days On Hand
**Formula**: `(OnFloorCases + InboundByHorizon) / DailySalesCases`

**Purpose**: Days of coverage after including scheduled reliable inbound inventory. Use when output spec requests "Delivered Days On Hand" or post-inbound coverage metrics.

## Example Walkthrough

**Given**:
- AsOfDate: 2025-08-01, HorizonEnd: 2025-08-31
- Item: SNK-101, OnFloor: 240, DailySales: 28.5
- CasesPerPallet: 80
- Inbound: 200 cases arriving 2025-08-10, Status: "Committed"

**Step-by-step**:
1. Current DOH: 240 / 28.5 = 8.42 days
2. Projected OOS: 2025-08-01 + 8 = 2025-08-09
3. Planning Days: 30
4. Inbound by Horizon: 200 (arrives before 2025-08-31, status is reliable)
5. Remaining Demand: 28.5 × 30 = 855
6. Additional Needed: max(0, 855 - 240 - 200) = 415
7. Pallets: ceil(415 / 80) = 6
8. Earlier Delivery: 2025-08-09 < 2025-08-10 = TRUE
9. Delivered DOH: (240 + 200) / 28.5 = 15.44 days

## Variant: Rack-Based Storage

For rack-based scenarios (e.g., bakery operations):
- Sheet names: Rack Snapshot, Booking Feed, Pallet Defaults
- Columns: SKU Ref, Cases on Rack, Avg Daily Pull, ETA, Booking State
- Status values: Firm, Locked (include), Tentative, Hold (exclude)

Calculations remain identical; only column and sheet names differ.

## Variant: Lane-Based Produce

For produce lane restock scenarios:
- Sheet names: Lane Snapshot, Arrival Board
- Structure: Lane Snapshot has section headers "Lane: COOLER-X" with embedded SKU tables
- Columns: Lane, SKU, Cases, Daily Pull (Lane Snapshot); Lane, SKU, ETA, Cases, Load Status (Arrival Board)
- Status values: Ready, Docked (include), Draft, Cancelled (exclude)
- Output: Lane_Coverage (all items), Restock_Actions (Pallets_Required > 0)
- Required calculation: Delivered_Days_On_Hand

Key parsing requirement: Iterate rows to detect "Lane:" prefixes and associate subsequent rows with that lane until next lane header.

## Variant: Branch/Clinic Transfers

For healthcare clinic branch transfer scenarios:
- Sheet names: Branch Stock, Planned Transfers
- Structure: Branch Stock has metadata row 0, headers row 2, data row 3+
- Columns: Branch, Item, Units, Daily Use (Branch Stock); Transfer_ID, Branch, Item, Transfer_Date, Units_Planned, Status (Planned Transfers)
- Critical complexity: Duplicate Transfer_IDs may exist (e.g., T-002 appears twice - once Tentative with early date, once Confirmed with later date)
- Deduplication rule: Keep latest Transfer_Date per Transfer_ID
- Status values: Confirmed (include), Tentative/Cancelled/Draft (exclude)
- Output: Branch_Item_Coverage (all branch-item combinations), Transfer_Gap_List (Pallets_Required > 0)
- Required calculation: Delivered_Days_On_Hand
- Planning unit: Units (not Cases), but calculations identical

Key processing requirement: Deduplicate before status filtering to avoid counting both Tentative and Confirmed versions of same transfer.
