# Load Planning Variant Patterns

Tested configurations from production runs.

## Pattern A: Standard Layout
| Element | Location | Notes |
|---------|----------|-------|
| Sheet: Stock | 'Stock Snapshot' | AsOfDate B1, HorizonEnd D1 |
| Stock headers | Row 3 | Item_Code, On_Floor_Cases, Daily_Sales_Cases_Per_Day |
| Sheet: Inbound | 'Scheduled Inbounds' | Headers row 1, no status column |
| Sheet: Config | 'Load Config' | Cases_Per_Pallet in A2 |

## Pattern B: Midmonth/Petcare Variant
| Element | Location | Notes |
|---------|----------|-------|
| Sheet: Stock | 'Current Stock' | AsOfDate B1, HorizonEnd D1, headers row 4 |
| Columns | SKU, Units On Hand, Daily Rate | 'Units' not 'Cases' |
| Sheet: Inbound | 'Expected Arrivals' | Headers: SKU, Arrival Date, Cases Expected, **Dock Status** |
| Status filter | Dock Status | **Only Committed, Arranged** |
| Sheet: Config | 'Pallet Guide' | Cases Per Pallet in A2 |
| Output names | SKU_Coverage, Pallet_Gap_List | Not Load_Detail |

## Pattern C: Bakery/Rack Weekly Variant
| Element | Location | Notes |
|---------|----------|-------|
| Sheet: Stock | 'Rack Snapshot' | AsOfDate B1, HorizonEnd D1, headers row 3 |
| Columns | SKU Ref, Cases on Rack, Avg Daily Pull | 'Rack' not 'Floor', 'Pull' not 'Sales' |
| Sheet: Inbound | 'Booking Feed' | Headers: SKU Ref, ETA, Booked Cases, **Booking State**, Comment |
| Status filter | Booking State | **Only Firm, Locked** (exclude Tentative, Hold) |
| Data quality | Common issues | Null SKUs, bad dates in ETA, 'planner note' rows |
| Sheet: Config | 'Pallet Defaults' | 'Cases Per Pallet' in A1, value in A2 |
| Output names | Rack_Coverage, Commit_Gap_Actions | Industry-specific terminology |

## Pattern D: Produce/Lane Variant
| Element | Location | Notes |
|---------|----------|-------|
| Sheet: Stock | 'Lane Snapshot' | AsOfDate B1, HorizonEnd D1; **hierarchical structure** |
| Structure | Lane headers | 'Lane: COOLER-A' in col 1, then SKU sub-table below |
| SKU sub-table | 3 columns | SKU, Cases, Daily Pull |
| Lane/SKU key | Composite | Must track (Lane, SKU) pairs, not SKU alone |
| Sheet: Inbound | 'Arrival Board' | Headers: Lane, SKU, ETA, Cases, **Load Status** |
| Status filter | Load Status | **Only Ready, Docked** (exclude Draft, Cancelled) |
| Null lane rows | Data quality | Lane=None with valid SKU/data - skip (unattributable) |
| Output names | Lane_Coverage, Restock_Actions | Produce-specific terminology |

## Pattern E: Clinic/Branch Transfer Variant
| Element | Location | Notes |
|---------|----------|-------|
| Sheet: Stock | 'Branch Stock', 'Site Inventory' | AsOfDate B1, HorizonEnd D1; headers row 2 |
| Columns | Branch, Item/SKU, Units, Daily Use | 'Daily Use' not 'Sales' |
| Branch/Item key | Composite | Must track (Branch, Item) pairs |
| Sheet: Transfers | 'Planned Transfers', 'Transfer Schedule' | Headers: Transfer_ID, Branch, Item, Transfer_Date, Units, Status |
| Status filter | Status | **Only Confirmed** (exclude Tentative, Cancelled) |
| **Critical**: Deduplication | Transfer_ID duplicates | Keep latest Transfer_Date per Transfer_ID before status filter |
| Earlier_Delivery check | Transfer_Date < OOS_Date | TRUE if no confirmed transfer arrives before stock-out |
| Sheet: Config | 'Pallet Guide' | Units Per Pallet in A2 (often 48 for medical supplies) |
| Output names | Branch_Item_Coverage, Transfer_Gap_List | Healthcare/transfer terminology |

## Pattern F: Simple Shipment Planning (No Status Column)
| Element | Location | Notes |
|---------|----------|-------|
| Sheet: Stock | 'Current Inventory' | Metadata in row 0: 'Today's Date' B1, 'Month End' D1; headers row 2 |
| Columns | Product SKU, In Stock (cases), Rate of Sale (cases/day) | Simple flat structure |
| Sheet: Inbound | 'Incoming Shipments' | No status column - include all rows |
| Headers | Product SKU, Delivery Date, Number of Pallets, Number of Cases Left | Pallet count provided directly |
| Sheet: Config | 'Ratio' | Cases per Pallet in simple two-column or single value format |
| Data quality | Date formats | Mixed datetime and date-only in Delivery Date |
| Output metadata | Field/Value pairs | AsOfDate, PlanningHorizonEnd, RemainingDaysInJuly in rows 1-3 |
| Boolean flags | Rounding_Applied, Earlier_Delivery_Required | Include in output for traceability |
| **Key difference** | No status filtering | All shipments considered committed |

## Status Column Detection

### When to Skip Status Filtering
Skip status filtering when:
- No column headers contain: 'status', 'dock', 'confirm', 'booking', 'state', 'load', 'stage'
- Data is simple 'Incoming Shipments' with Delivery Date and Cases only
- Source is manually curated list, not booking feed

### Detection heuristics:
```python
# Check for status column in headers
has_status_col = any(
    any(term in str(h).lower() for term in ['status', 'dock', 'confirm', 'booking', 'state', 'load', 'stage'])
    for h in headers
)

if has_status_col:
    # Apply status filtering
    allowed = {'committed', 'arranged', 'confirmed', 'approved', 'firm', 'locked', 'ready', 'docked'}
    df = df[df['Status'].str.lower().isin(allowed)]
else:
    # No status column - include all rows, filter by date only
    pass
```

## Transfer Deduplication Pattern

Transfer schedules often contain duplicate Transfer IDs with different dates:

```
Transfer_ID  Branch  Item   Transfer_Date  Units  Status
T-001        BR-01   MED-X  2025-10-10     100    Confirmed
T-002        BR-01   MED-Y  2025-10-08      80    Tentative  <- dedupe: same ID
T-002        BR-01   MED-Y  2025-10-12      80    Confirmed  <- keep: latest date
```

**Algorithm:**
```python
# Group by Transfer_ID, keep row with max Transfer_Date
deduped = df.loc[df.groupby('Transfer_ID')['Transfer_Date'].idxmax()]

# Then filter for confirmed status only
confirmed = deduped[deduped['Status'] == 'Confirmed']
```

## Status Values by Reliability

| Status | Include? | Rationale | Common In |
|--------|----------|-----------|-----------|
| Committed | ✓ | Firm arrival, counted | Logistics, shipping |
| Arranged | ✓ | Scheduled and confirmed | Logistics, shipping |
| Confirmed | ✓ | Alternative term | General, transfers |
| Approved | ✓ | Alternative term | General |
| Firm | ✓ | Confirmed booking | Retail, bakery |
| Locked | ✓ | Frozen/committed | Retail, planning systems |
| Ready | ✓ | Cleared for receipt | Produce, warehousing |
| Docked | ✓ | Arrived/at dock | Produce, warehousing |
| Released | ✓ | Approved for dispatch | Dispatch, routing |
| Staged | ✓ | Prepared for loading | Warehousing |
| Tentative | ✗ | Not reliable for planning | All variants |
| Pending | ✗ | Not yet approved | All variants |
| Draft |  | Incomplete | All variants |
| Proposed | ✗ | Not committed | All variants |
| Cancelled | ✗ | Explicitly excluded | All variants, transfers |
| Hold | ✗ | Suspended, not firm | Retail, planning |

## Data Quality Patterns by Source

### Booking Feed / Inbound Shipment Files
Common issues encountered:
- **Null SKU rows**: ETA and cases present but SKU Ref is None (unattributable inventory)
- **Null Lane rows**: Lane=None but SKU has valid data (cannot attribute to location)
- **String dates**: 'bad-date', 'TBD' in date columns instead of datetime
- **Mixed types**: Same column contains datetime and string values
- **Metadata rows**: Rows with Comment like 'planner note row' or all-None values
- **After-horizon data**: Valid bookings past planning horizon (exclude from sums)

**Detection heuristics:**
```python
# Skip null SKU
if cell is None or str(cell).strip() == '':
    continue

# Skip null Lane (for lane-based structures)
if lane_col is not None and (row[lane_col] is None or str(row[lane_col]).strip() == ''):
    continue

# Skip invalid dates
date_val = row[date_col]
if isinstance(date_val, str) or date_val is None:
    continue
try:
    arrival = date_val.date() if hasattr(date_val, 'date') else date_val
except:
    continue

# Skip note rows
if 'planner note' in str(row.get(comment_col, '')).lower():
    continue
```

### Transfer Schedule Files
Common issues encountered:
- **Duplicate Transfer_IDs**: Same ID with different dates/status (deduplicate to latest)
- **Mixed statuses per ID**: Tentative and Confirmed for same transfer (dedupe then filter)
- **Cancelled transfers**: Explicitly cancelled but still in file (exclude by status)
- **After-horizon transfers**: Valid transfers past planning horizon (exclude from sums)
- **Null Branch rows**: Transfer without branch attribution (skip)

**Detection heuristics:**
```python
# Deduplicate: keep latest date per Transfer_ID
df = df.loc[df.groupby('Transfer_ID')['Transfer_Date'].idxmax()]

# Filter to confirmed only
df = df[df['Status'] == 'Confirmed']

# Filter to horizon
df = df[df['Transfer_Date'] <= horizon_end]
```

## Detection Heuristics for Sheet Discovery

```python
# Detect stock sheet
if any(x in sheet_name.lower() for x in ['stock', 'current', 'inventory', 'position', 'rack', 'snapshot', 'lane', 'branch']):
    likely_stock_sheet = sheet_name

# Detect inbound/booking sheet  
if any(x in sheet_name.lower() for x in ['arrival', 'inbound', 'expected', 'scheduled', 'shipment', 'booking', 'feed', 'commit', 'board', 'transfer', 'shipment']):
    likely_inbound_sheet = sheet_name

# Detect config sheet
if any(x in sheet_name.lower() for x in ['config', 'guide', 'pallet', 'parameter', 'default', 'ratio']):
    likely_config_sheet = sheet_name

# Detect hierarchical/lane structure (check for 'Lane:' prefix in first 20 rows)
for row_idx in range(1, min(20, sheet.max_row)):
    cell_val = sheet.cell(row=row_idx, column=1).value
    if isinstance(cell_val, str) and cell_val.startswith('Lane:'):
        has_hierarchical_lanes = True
        break

# Detect branch structure (check for 'Branch' column)
for cell in header_row:
    if cell and 'branch' in str(cell).lower():
        has_branch_structure = True
        break

# Detect status column (check multiple terms)
for cell in header_row:
    if cell and any(x in str(cell).lower() for x in ['status', 'dock', 'confirm', 'booking', 'state', 'load']):
        status_col = idx
        has_status_filter = True
```

## Terminology Mapping

| Generic Term | Bakery/Rack Variant | Petcare Variant | Produce/Lane Variant | Branch/Transfer Variant | Simple Shipment Variant |
|--------------|---------------------|-----------------|----------------------|------------------------|------------------------|
| On Floor | Cases on Rack | Units On Hand | Cases | Units On Hand | In Stock (cases) |
| Daily Sales | Avg Daily Pull | Daily Rate | Daily Pull | Daily Use | Rate of Sale (cases/day) |
| Inbound | Booking | Expected Arrival | Arrival Board | Planned Transfer | Incoming Shipments |
| Status | Booking State | Dock Status | Load Status | Status | *(none)* |
| SKU | SKU Ref | SKU | SKU | Item | Product SKU |
| Location | - | - | Lane | Branch | - |
| Load_Detail | Rack_Coverage | SKU_Coverage | Lane_Coverage | Branch_Item_Coverage | SKU_Results |
| Load_Action_Summary | Commit_Gap_Actions | Pallet_Gap_List | Restock_Actions | Transfer_Gap_List | Additional_Shipments_Needed |
| Transfer ID | - | - | - | Transfer_ID | - |
| Date Label | - | - | - | - | Today's Date / Month End |

## Composite Key Patterns

| Variant | Primary Key | Secondary Key | Matching Logic |
|---------|-------------|---------------|----------------|
| Standard | SKU | - | Direct equality |
| Lane | Lane | SKU | (Lane, SKU) tuple |
| Branch | Branch | SKU/Item | (Branch, SKU) tuple |

When building composite keys, ensure both components are non-null before inclusion.
