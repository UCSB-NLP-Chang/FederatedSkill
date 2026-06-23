# Load Planning Formula Reference

## Input Parameters

| Parameter | Description | Typical Source |
|-----------|-------------|----------------|
| AsOfDate | Planning baseline date | Row 0, Column B |
| HorizonEnd | End of planning period | Row 0, Column D |
| CasesPerPallet | Conversion factor | Load Config / Pallet Defaults sheet, or constant |
| OnFloorCases | Current inventory | Stock Snapshot / Rack Snapshot / Lane Snapshot / Branch Stock |
| DailySalesCases | Velocity rate | Stock Snapshot / Rack Snapshot / Lane Snapshot / Branch Stock |
| ScheduledInbounds | Future arrivals | Scheduled Inbounds / Booking Feed / Arrival Board / Planned Transfers |
| Status | Shipment/Booking/Transfer reliability status | Expected Arrivals / Booking Feed / Arrival Board / Transfer Schedule |
| Lane/Branch | Storage location/zone | Lane Snapshot / Branch Stock |
| TransferID | Unique identifier for transfers | Planned Transfers / Transfer Schedule |

## Status Value Reference

Different source files use different status terminologies. Map and filter appropriately:

| Status Column Type | Include Values | Exclude Values |
|-------------------|----------------|----------------|
| Dock_Status | Committed, Arranged, Confirmed, At Dock, In Transit | Tentative, Pending, Planned, Forecasted, Requested |
| Booking_State | Firm, Locked, Confirmed | Tentative, Hold, Pending, Requested |
| Shipment_Status | Confirmed, In Transit, Arrived | Planned, Expected, Cancelled |
| Load_Status | Ready, Docked | Draft, Cancelled |
| Status (Transfers) | Confirmed | Tentative, Cancelled, Pending, Draft |

## Data Cleaning Requirements

Before performing calculations, clean input data to handle real-world quality issues:

### Filter Null Identifiers
```python
# Remove rows with null/None/NaN SKU or Item_Code
stock_data = stock_data[stock_data['Item_Code'].notna()]
inbounds = inbounds[inbounds['Item_Code'].notna()]

# For lane/branch-based variants, also filter null Lane/Branch
inbounds = inbounds[inbounds['Lane'].notna() & (inbounds['Lane'] != '')]
# or
inbounds = inbounds[inbounds['Branch'].notna() & (inbounds['Branch'] != '')]
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

### Deduplicate by Transfer/Booking ID

When the same Transfer ID appears multiple times with different statuses:

```python
# Prefer Confirmed over Tentative for same Transfer ID
def deduplicate_by_status(df, id_col='Transfer_ID', status_col='Status'):
    """Keep only the most reliable status for each unique ID."""
    CONFIRMED_STATUSES = {'Committed', 'Arranged', 'Confirmed', 'Approved', 'Firm', 'Locked', 'Ready', 'Docked'}
    
    result = []
    for transfer_id, group in df.groupby(id_col):
        # Prefer confirmed statuses
        confirmed = group[group[status_col].isin(CONFIRMED_STATUSES)]
        if len(confirmed) > 0:
            result.append(confirmed.iloc[0])
        else:
            # Keep first row if no confirmed status exists
            result.append(group.iloc[0])
    
    return pd.DataFrame(result)

# Apply before filtering by status
deduplicated = deduplicate_by_status(transfers, 'Transfer_ID', 'Status')
```

## Parsing Grouped/Sectioned Layouts

When a sheet contains multiple data blocks separated by section headers (e.g., `Lane: COOLER-A`), use `openpyxl` to parse row-by-row:

```python
import openpyxl

wb = openpyxl.load_workbook(path)
ws = wb['Lane Snapshot']

as_of_date = ws.cell(row=1, column=2).value
horizon_end = ws.cell(row=1, column=4).value

current_lane = None
rows_data = []

for row in ws.iter_rows(min_row=3, values_only=True):
    # Detect section header (e.g., "Lane: COOLER-A" in column A)
    if row[0] and str(row[0]).startswith("Lane:"):
        current_lane = str(row[0]).split(":")[1].strip()
        continue
    # Skip header rows or empty rows
    if not row[0] or row[0] in ["SKU", "Item_Code", "Product"]:
        continue
    # Append data with extracted group key
    if current_lane:
        rows_data.append({
            "Lane": current_lane,
            "SKU": row[0],
            "Cases": row[1],
            "Daily_Pull": row[2]
        })
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

# Filter by status if column exists
if 'Dock_Status' in inbounds.columns:
    reliable = ['Committed', 'Arranged', 'Confirmed']
    inbounds = inbounds[inbounds['Dock_Status'].isin(reliable)]
elif 'Booking_State' in inbounds.columns:
    reliable = ['Firm', 'Locked']
    inbounds = inbounds[inbounds['Booking_State'].isin(reliable)]
elif 'Load_Status' in inbounds.columns:
    reliable = ['Ready', 'Docked']
    inbounds = inbounds[inbounds['Load_Status'].isin(reliable)]
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

## Variant: Lane-Based Inventory

For lane/cooler-based scenarios (e.g., produce operations):
- Sheet names: Lane Snapshot, Arrival Board
- Inventory grouped by lane within single sheet
- Columns: Lane, SKU, Cases, Daily Pull, ETA, Load Status
- Status values: Ready, Docked (include), Draft, Cancelled (exclude)
- Composite key: Lane + SKU (same SKU can appear in multiple lanes)
- CasesPerPallet often constant (e.g., 54) rather than in config sheet

**Parsing lane-grouped data**:
```python
items = []
current_lane = None
for idx, row in raw.iterrows():
    first_cell = str(row[0]).strip() if pd.notna(row[0]) else ''
    if first_cell.startswith('Lane:'):
        current_lane = first_cell.replace('Lane:', '').strip()
    elif first_cell in ['SKU', 'Item_Code']:
        continue  # Skip header rows within sections
    elif current_lane and first_cell:
        items.append({
            'Lane': current_lane,
            'SKU': row[0],
            'Cases': float(row[1]) if pd.notna(row[1]) else 0,
            'Daily_Pull': float(row[2]) if pd.notna(row[2]) else 0
        })
```

**Matching arrivals to lanes**:
- Arrivals reference both Lane and SKU
- Filter arrivals by Lane+SKU composite key
- Exclude arrivals with blank Lane or SKU

## Variant: Branch-Based Transfers

For branch/clinic inventory scenarios:
- Sheet names: Branch Stock, Planned Transfers (or Transfer Schedule)
- Columns: Branch, Item, Units, Daily Use (stock); Transfer ID, Branch, Item, Transfer Date, Units Planned, Status (transfers)
- Status values: Confirmed (include), Tentative, Cancelled (exclude)
- Composite key: Branch + Item (same item can appear in multiple branches)
- UnitsPerPallet often constant (e.g., 50) rather than in config sheet
- **Deduplication required**: Same Transfer ID may appear multiple times with different statuses

**Deduplication logic**:
```python
# When same Transfer ID has multiple entries with different statuses
# Prefer Confirmed over Tentative
CONFIRMED_STATUSES = {'Committed', 'Arranged', 'Confirmed', 'Approved', 'Firm', 'Locked', 'Ready', 'Docked'}

def deduplicate_transfers(df):
    result = []
    for transfer_id, group in df.groupby('Transfer_ID'):
        confirmed = group[group['Status'].isin(CONFIRMED_STATUSES)]
        if len(confirmed) > 0:
            result.append(confirmed.iloc[0])
        else:
            # Keep first if no confirmed status
            result.append(group.iloc[0])
    return pd.DataFrame(result)
```

**Matching transfers to branches**:
- Transfers reference both Branch and Item
- Filter transfers by Branch+Item composite key
- Exclude transfers with blank Branch or Item
- Only count transfers where Transfer Date <= HorizonEnd