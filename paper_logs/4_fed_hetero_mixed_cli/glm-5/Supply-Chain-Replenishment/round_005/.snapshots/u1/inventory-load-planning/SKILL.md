---
name: inventory-load-planning
description: Calculate inventory load plans from stock snapshots and scheduled inbounds/bookings/transfers. Use when building OOS projections, pallet requirements, delivery schedules, or replenishment action summaries from Excel inventory data. Trigger on tasks involving stock snapshots, booking feeds, rack coverage, commit-gap analysis, inbound planning workbooks, lane-based restock, produce/cooler inventory, branch-level stock, or transfer gap analysis.
---

# Inventory Load Planning

## Workflow

1. **Inspect Source Structure**
   - Source files often have metadata rows before headers (AsOfDate, HorizonEnd)
   - If `pd.read_excel()` returns wrong columns, use `header=None` and inspect raw rows
   - Data typically starts 2-3 rows down with actual headers in row 2 or 3
   - **Lane-based variant**: Inventory may be grouped by location (e.g., "Lane: COOLER-A") with repeated headers per section
   - **Branch-based variant**: Inventory keyed by Branch+Item composite

2. **Read source workbook**: Parse stock/rack/lane/branch snapshot, booking/inbound/transfer feed, and config sheets

3. **Extract Parameters**: Read `AsOfDate`, `HorizonEnd`, compute `PlanningDays = (HorizonEnd - AsOfDate).days`. Extract `CasesPerPallet` or `UnitsPerPallet`.

4. **Filter Inbounds/Bookings/Transfers by Status** (critical step):
   - Check if inbound/transfer data includes a status column (e.g., 'Dock Status', 'Booking State', 'Status', 'Load Status')
   - Only count inbounds with confirmed statuses: `Committed`, `Arranged`, `Confirmed`, `Firm`, `Locked`, `Approved`, `Ready`, `Docked`
   - Exclude uncertain statuses: `Pending`, `Tentative`, `Planned`, `Proposed`, `Hold`, `Unconfirmed`, `Draft`, `Cancelled`
   - If no status column exists, include all inbounds
   - **Inference Rule**: If unfamiliar statuses appear, infer reliability from context. Words implying physical presence or finalization (`Ready`, `Docked`, `At Dock`, `In Transit`, `Confirmed`) are safe to include. Words implying planning or uncertainty (`Draft`, `Planned`, `Tentative`, `Forecasted`, `Cancelled`) must be excluded.
   - Exclude rows with missing grouping keys (e.g., blank Lane/Branch/Zone/SKU)

5. **Deduplicate by ID if Present**:
   - Some sources have duplicate Transfer/Booking IDs with different statuses or dates
   - When same ID appears multiple times, prefer Confirmed over Tentative/other uncertain statuses
   - If same ID has multiple Confirmed entries, use the latest date or sum quantities as appropriate
   - Example: T-002 appears with Tentative (2025-10-08) and Confirmed (2025-10-12) → keep Confirmed version only

6. **Clean Booking/Inbound/Transfer Data**:
   - Skip rows with invalid/unparseable dates (e.g., "bad-date", text in date columns)
   - Skip rows with missing item references (blank SKU/Item_Code/Branch/Lane cells)
   - Skip metadata/note rows (e.g., "planner note row", comment-only rows)
   - Validate dates are within reasonable range before processing

7. **Calculate per-item metrics** (preserve source order):
   - `cur_doh = on_floor / daily_sales`
   - `oos_date = as_of_date + timedelta(days=floor(cur_doh))`
   - `inbound_cases = sum(cases for qualifying inbounds where arrival_date <= horizon_end)`
   - `delivered_doh = (on_floor + inbound_cases) / daily_sales`
   - `remaining_demand = daily_sales * planning_days`
   - `additional = max(0, remaining_demand - on_floor - inbound_cases)`
   - `pallets = ceil(additional / cases_per_pallet)` if `additional > 0` else `0`
   - `req_date = oos_date` if `pallets > 0` else `None`
   - `earlier = True` if `no qualifying inbounds exist` OR `earliest_inbound > req_date` else `False`

8. **Write Output**: Create two sheets: primary coverage sheet (metadata + full calculations) and action summary sheet (filtered to items where additional > 0)

9. **Verify**: Read back output. Spot-check 2-3 items manually. Ensure sheet order and item order match requirements.

## Critical Parsing Rule

When standard pandas reading fails (e.g., "ValueError: could not convert string to float"):

```python
# Read without headers first to inspect structure
raw = pd.read_excel(path, sheet_name='Stock Snapshot', header=None)

# Extract metadata from specific cells
as_of_date = pd.to_datetime(raw.iloc[0, 1])
horizon_end = pd.to_datetime(raw.iloc[0, 3])

# Skip to actual data (row 2 or 3 = headers, row 3+ or 4+ = data)
data = raw.iloc[3:].copy()
data.columns = ['Item_Code', 'On_Floor_Cases', 'Daily_Sales', '_drop']
data = data.drop('_drop', axis=1).reset_index(drop=True)
```

## Lane-Based Inventory Variant

Some workbooks organize inventory by location/lane within a single sheet:

```
Row 1: AsOfDate | 2026-01-05 | HorizonEnd | 2026-01-20
Row 2: (blank)
Row 3: Lane: COOLER-A
Row 4: SKU | Cases | Daily Pull
Row 5: PRD-APPLE | 100 | 12
Row 6: PRD-BANANA | 40 | 8
Row 7: (blank)
Row 8: Lane: COOLER-B
Row 9: SKU | Cases | Daily Pull
...
```

**Parsing approach** (use openpyxl for grouped/sectioned layouts — pandas misaligns columns):

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

**Key differences**:
- Composite key: Lane + SKU (same SKU may appear in multiple lanes)
- Headers repeat per section
- Blank rows separate sections
- Output includes Lane column

## Sheet Name Variations

Source files use varying terminology for sheets:

| Standard | Alternative Names |
|----------|-------------------|
| Stock Snapshot | Rack Snapshot, Inventory Snapshot, Current Stock, Lane Snapshot, Branch Stock |
| Scheduled Inbounds | Booking Feed, Expected Arrivals, Inbound Shipments, Arrivals, Arrival Board, Planned Transfers, Transfer Schedule |
| Load Config | Pallet Defaults, Config, Parameters |

## Column Name Variations

Source files use varying terminology. Map these common synonyms:

| Concept | Common Column Names |
|---------|---------------------|
| Item Code | SKU, SKU Ref, Item_Code, Product_ID, Material, Item |
| Lane/Location/Branch | Lane, Cooler, Zone, Location, Area, Branch |
| On Hand | On_Floor_Cases, Cases_On_Rack, Cases, Units_On_Hand, Cases_On_Hand, Current_Stock, Units, Units_On_Hand |
| Daily Rate | Daily_Sales, Daily_Pull, Avg_Daily_Pull, Daily_Rate, Sales_Velocity, Daily_Usage, Daily_Use, Daily_Use_Units_Per_Day |
| Arrivals | Scheduled_Inbounds, Booking_Feed, Expected_Arrivals, Inbound_Shipments, Planned_Transfers, Transfer_Schedule |
| Arrival Date | Arrival_Date, ETA, Expected_Date, Dock_Date, Transfer_Date |
| Dock Status | Dock_Status, Booking_State, Status, Shipment_Status, Confirm_Status, Load_Status |
| Cases Due | Booked_Cases, Cases_Due, Qty, Cases, Units_Planned, Units |
| Transfer ID | Transfer_ID, Transfer_ID, Shipment_ID, Booking_Ref |

## Status Filtering

When inbound/booking/transfer data includes a status column, filter before aggregating:

```python
CONFIRMED_STATUSES = {'Committed', 'Arranged', 'Confirmed', 'Approved', 'Firm', 'Locked', 'Ready', 'Docked'}
UNCERTAIN_STATUSES = {'Pending', 'Tentative', 'Planned', 'Proposed', 'Unconfirmed', 'Hold', 'Draft', 'Cancelled'}

# Filter to only confirmed inbounds
qualifying = inbounds[inbounds['Status'].isin(CONFIRMED_STATUSES)]
# Or exclude uncertain ones
qualifying = inbounds[~inbounds['Status'].isin(UNCERTAIN_STATUSES)]
```

**Why this matters**: Counting pending, tentative, or held arrivals overstates available inventory, leading to missed reorder points and stockouts.

## Deduplication by Transfer/Booking ID

When the same Transfer ID or Booking Ref appears multiple times with different statuses:

```python
# Group by Transfer ID and resolve conflicts
def deduplicate_transfers(df):
    # For each Transfer ID, prefer Confirmed over Tentative
    result = []
    for transfer_id, group in df.groupby('Transfer_ID'):
        confirmed = group[group['Status'] == 'Confirmed']
        if len(confirmed) > 0:
            result.append(confirmed.iloc[0])  # Take first Confirmed
        else:
            # No confirmed, check for other reliable statuses
            reliable = group[group['Status'].isin(CONFIRMED_STATUSES)]
            if len(reliable) > 0:
                result.append(reliable.iloc[0])
    return pd.DataFrame(result)
```

**Why this matters**: Duplicate entries with conflicting statuses can double-count inventory or use stale dates.

## Key Formulas

| Metric | Formula |
|--------|----------|
| Current Days On Hand | `on_floor / daily_sales` |
| Projected OOS Date | `as_of_date + floor(days_on_hand)` |
| Delivered Days On Hand | `(on_floor + inbound_cases) / daily_sales` |
| Remaining Demand Cases | `daily_sales × planning_days` |
| Additional Cases Needed | `max(0, remaining_demand - on_floor - inbound_cases)` |
| Pallets Required | `ceil(additional_cases / cases_per_pallet)` |
| Required Delivery Date | `projected_oos_date` |
| Earlier Delivery Required | `True` if no qualifying inbound OR earliest inbound > required_date |

## Edge Cases

- **Zero on_floor**: Days on hand = 0, OOS date = as_of_date, immediate action needed
- **No scheduled inbound**: Treat inbound_cases = 0, still calculate requirements
- **Inbound after horizon**: Exclude from booked_cases count; triggers earlier delivery flag if OOS before horizon
- **Excess inventory**: Additional cases needed = 0, no pallets required
- **All inbounds uncertain**: Treat as no inbound, set earlier_delivery = True
- **Invalid dates in booking feed**: Skip rows with unparseable dates (e.g., text strings, blanks)
- **Missing item references**: Skip booking rows where SKU/Item_Code is blank
- **Missing lane/branch references**: Skip booking rows where Lane/Branch is blank (lane/branch-based variants)
- **Note/metadata rows in booking feed**: Skip rows that contain only comments or planner notes
- **Duplicate Transfer IDs**: Deduplicate by preferring Confirmed status over Tentative/other uncertain statuses

## Known invariants (by sub-task)

### excel-inventory-load-planning (B1)
- Source workbook structure: metadata rows precede headers in Stock Snapshot sheet
- AsOfDate typically in row 0 column B; HorizonEnd in row 0 column D
- Data headers at row index 2; data rows start at row index 3+
- Scheduled Inbounds sheet: headers at row 0, data starts row 1
- Load Config sheet: CasesPerPallet at cell A2 (or similar)
- Output must have exactly two sheets: coverage sheet (first), action summary (second)
- Action summary includes only items where Additional_Cases_Needed > 0

### bakery-commit-gap (variant)
- Sheet names: "Rack Snapshot", "Booking Feed", "Pallet Defaults"
- Metadata in row 1 (A1=AsOfDate label, B1=value, C1=HorizonEnd label, D1=value)
- Headers at row 3, data starts row 4
- Booking Feed: headers at row 1, data starts row 2
- May contain invalid dates, missing SKU refs, and note rows in booking feed
- Output sheets: "Rack_Coverage" (metadata + calculations), "Commit_Gap_Actions" (filtered actions)

### produce-lane-restock (variant)
- Sheet names: "Lane Snapshot", "Arrival Board"
- Inventory grouped by lane within single sheet (Lane: COOLER-A, Lane: COOLER-B, etc.)
- Headers repeat per lane section
- Arrival Board status column: "Load Status" with values Ready/Docked (include), Draft/Cancelled (exclude)
- Composite key: Lane + SKU (same SKU can appear in multiple lanes)
- CasesPerPallet may be constant (e.g., 54) rather than in config sheet
- Output sheets: "Lane_Coverage", "Restock_Actions"
- **Required calculation**: Delivered_Days_On_Hand must be computed and included in output

### clinic-branch-transfer (variant)
- Sheet names: "Branch Stock", "Planned Transfers" (or similar)
- Metadata in row 1 (A1=AsOfDate label, B1=value, C1=HorizonEnd label, D1=value)
- Headers at row 3, data starts row 4
- Transfer schedule: headers at row 1, data starts row 2
- Columns: Branch, Item, Units, Daily Use (stock); Transfer ID, Branch, Item, Transfer Date, Units Planned, Status (transfers)
- Composite key: Branch + Item (same item can appear in multiple branches)
- Status values: Confirmed (include), Tentative/Cancelled (exclude)
- **Deduplication required**: Same Transfer ID may appear multiple times with different statuses — prefer Confirmed over Tentative
- UnitsPerPallet may be constant (e.g., 50) rather than in config sheet
- Output sheets: "Branch_Item_Coverage", "Transfer_Gap_List"
- **Required calculation**: Delivered_Days_On_Hand must be computed and included in output

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-Patterns & Pitfalls

- **Import Error**: Use `from datetime import timedelta`, not `date.timedelta`.
- **Header Pollution**: Don't assume headers are in row 0. Metadata rows may precede data.
- **String in Calculations**: Filter out rows containing "On Floor" or "Item Code" before math.
- **Using `floor()` for pallets**: Must use `ceil()` — underestimates truck space.
- **Forgetting items with zero stock**: They need immediate attention.
- **Ignoring inbounds after OOS date**: These trigger earlier delivery flags.
- **Zero Daily Sales**: Guard against division by zero. If `daily_sales == 0`, set DOH to `None` or 0.
- **Negative Additional Needed**: Always apply `max(0, ...)`.
- **Skipping verification**: Always confirm output workbook structure and calculations.
- **Counting uncertain inbounds**: Exclude Pending/Tentative/Hold/Draft/Cancelled statuses to avoid false coverage.
- **Assuming all dates are valid**: Booking feeds may contain text like "bad-date" or blank cells in date columns — validate before comparison.
- **Assuming all rows have item codes**: Some booking rows may be missing SKU references — filter these out.
- **Ignoring lane/branch grouping**: In lane/branch-based variants, same SKU can exist in multiple locations — use Lane/Branch+SKU as composite key.
- **Assuming pandas handles grouped layouts**: Use `openpyxl` row-by-row parsing when sheets contain interleaved section headers.
- **Duplicate Transfer IDs**: Same ID may appear with different statuses — deduplicate by preferring Confirmed over Tentative.

## Validation Steps

- Verify Additional Cases Needed never negative
- Confirm pallet calculations use `math.ceil()`, not `round()`
- Check Earlier Delivery Required compares datetime objects
- Validate items with sufficient inbound coverage show Earlier Delivery Required = False
- Verify status filtering applied if column present in source
- Confirm Delivered_Days_On_Hand calculation if required by output specification
- Check that null/None rows were filtered from inbound data before summing
- For lane-based variants: verify Lane column present in output and items correctly grouped
- For branch-based variants: verify Branch column present in output and items correctly grouped
- For transfer schedules: verify duplicate Transfer IDs were deduplicated correctly

## Scripts

- Run `scripts/load_plan_calculator.py` for reference implementation of all calculations.
- See `references/formulas.md` for detailed formula specification with examples.