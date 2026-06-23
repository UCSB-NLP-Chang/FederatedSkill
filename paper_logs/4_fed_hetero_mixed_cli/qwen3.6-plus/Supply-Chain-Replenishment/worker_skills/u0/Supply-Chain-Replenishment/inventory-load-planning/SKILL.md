---
name: inventory-load-planning
description: Calculate inventory load plans from stock snapshots and scheduled inbounds/bookings. Use when building OOS projections, pallet/load requirements, delivery schedules, or replenishment action summaries from Excel inventory data. Trigger on tasks involving stock snapshots, booking/recovery/transfer feeds, rack coverage, commit-gap analysis, inbound planning workbooks, branch transfer gap analysis, route dispatch tracker refreshes, alias-to-canonical route mapping, or template-based tracker refreshes.
---

# Inventory Load Planning

## Workflow

1. **Inspect Source Structure**
   - Source files often have metadata rows before headers (AsOfDate, HorizonEnd)
   - If `pd.read_excel()` returns wrong columns, use `header=None` and inspect raw rows
   - Data typically starts 2-3 rows down with actual headers in row 2 or 3

2. **Read source workbook**: Parse stock/rack/route snapshot, booking/inbound/transfer/recovery/queue feed, and config/pallet guide/pack matrix sheets

3. **Extract Parameters**: Read `AsOfDate`, `HorizonEnd`, compute `PlanningDays = (HorizonEnd - AsOfDate).days`. Extract `CasesPerPallet` (or `UnitsPerPallet`, `CasesPerLoad`) from config/pallet guide sheet, or from a per-route/SKU Pack Matrix.

4. **Pre-filter by Row Type** (if applicable):
   - Some feeds include a `Row Type` column with values like `DISPATCH`, `COMMENT`, `HEADER`, `NOTE`
   - Only process rows where Row Type matches the candidate type (e.g., `DISPATCH`)
   - Apply this filter BEFORE deduplication and status filtering

5. **Resolve Aliases to Canonical Keys** (if applicable):
   - When source data uses aliases (e.g., `NORTH-100`, `R100-A`) that must map to canonical identifiers (e.g., `R-100`):
   - Load the alias map from the template or config sheet
   - Build a lookup dict: `{alias: canonical_route}`
   - Apply mapping to inbound/queue rows before matching against stock rows
   - Discard rows with unknown/unmapped aliases
   - **Normalize group keys**: Strip prefixes like `"Route "` from section headers before matching against Pack Matrix or alias maps

6. **Deduplicate Transfer/Booking/Load/Queue IDs** (critical — do this FIRST):
   - When the same ID appears multiple times, deduplicate before status filtering.
   - **Date-based**: Keep row with latest date:
     ```python
     df = df.sort_values(date_col, ascending=False).drop_duplicates(subset=[id_col], keep='first')
     ```
   - **Revision-based**: If a numeric `Revision` or `Version` column exists, keep highest revision:
     ```python
     df['Revision'] = pd.to_numeric(df['Revision'], errors='coerce')
     df = df.sort_values('Revision', ascending=False).drop_duplicates(subset=[id_col], keep='first')
     ```
   - Only after deduplication, apply status filtering (step 7).

7. **Filter Inbounds/Bookings by Status** (critical step):
   - Check if inbound data includes a status column (e.g., 'Dock Status', 'Booking State', 'Status', 'Load Status', 'Transfer Status', 'Queue State', 'Stage')
   - Only count inbounds with confirmed statuses: `Committed`, `Arranged`, `Confirmed`, `Firm`, `Locked`, `Approved`, `Ready`, `Docked`, `In Transit`, `Booked`, `Loaded`, `Released`
   - Exclude uncertain statuses: `Pending`, `Tentative`, `Planned`, `Proposed`, `Hold`, `Unconfirmed`, `Draft`, `Cancelled`
   - If no status column exists, include all inbounds
   - Exclude rows with missing grouping keys (e.g., blank Lane/Zone/SKU/Branch+Item/Route)

8. **Clean Booking/Inbound Data**:
   - Skip rows with invalid/unparseable dates (e.g., "bad-date", text in date columns)
   - Skip rows with missing item references (blank SKU/Item_Code/Branch cells)
   - Skip metadata/note rows (e.g., "planner note row", comment-only rows)
   - Validate dates are within reasonable range before processing

9. **Calculate per-item metrics** (preserve source order):
   - `cur_doh = on_floor / daily_sales`
   - `oos_date = as_of_date + timedelta(days=floor(cur_doh))`
   - `inbound_cases = sum(cases for qualifying inbounds where arrival_date <= horizon_end)`
   - `delivered_doh = (on_floor + inbound_cases) / daily_sales`
   - `remaining_demand = daily_sales * planning_days`
   - `additional = max(0, remaining_demand - on_floor - inbound_cases)`
   - `pallets = ceil(additional / cases_per_pallet)` if `additional > 0` else `0`
   - `req_date = oos_date` if `pallets > 0` else `None`
   - `earlier = True` if `pallets > 0` AND (`no qualifying inbounds exist` OR `earliest_qualifying_inbound > req_date`) else `False`

10. **Write Output**: Create output sheets matching template structure. If working from a template workbook, copy pre-populated sheets (Instructions, Pallet Guide, Pack Matrix, Route Alias Map, Overview) and fill computed sheets (Coverage, Actions).

11. **Verify**: Read back output. Spot-check 2-3 items manually. Ensure sheet order and item order match requirements.

## Environment Setup

When openpyxl or other Python packages are needed in externally-managed environments (Debian/Ubuntu with PEP 668):
```bash
pip install openpyxl --break-system-packages -q
```

## Template Workbook Handling

When the task provides a template workbook with pre-existing sheets:
1. Open template with `openpyxl.load_workbook(template_path)`
2. Create new workbook: `wb = openpyxl.Workbook()`
3. **Remove default sheet**: `wb.remove(wb.active)` (openpyxl always creates a default "Sheet")
4. Copy static sheets from template (Instructions, Pallet Guide, Pack Matrix, Route Alias Map, Overview, etc.) using row-by-row cell copy
5. Create and populate computed sheets (Coverage_Detail, Recovery_Loads, Dispatch_Plan, etc.)
6. Save to output path

## Earlier Delivery Logic — Out-of-Horizon Loads

**Critical distinction**: "Qualifying loads" for the `Earlier_Delivery_Required` check includes ALL reliable loads (Booked/Loaded/Confirmed/Released/Approved) regardless of whether their arrival date falls within the planning horizon.

- `Inbound_Units_By_Horizon` only counts loads with `arrival_date <= horizon_end`
- `Earlier_Delivery_Required` compares `Required_Delivery_Date` against the earliest arrival date among ALL qualifying loads (even those after horizon)
- Example: A load arriving 2025-11-22 is excluded from inbound count when horizon ends 2025-11-20, but if it's the only qualifying load for a SKU, `Earlier_Delivery_Required` = TRUE when OOS date (e.g., 2025-11-14) is before 2025-11-22.

## Required Delivery Date Variants

Tasks may specify different logic for `Required_Delivery_Date`. Check the output spec carefully:

**Variant A (Simple)**: `Required_Delivery_Date = Projected_OOS_Date` (when pallets > 0)

**Variant B (Conditional)**: 
- If `Earliest_Scheduled_Inbound_Date <= Projected_OOS_Date`: use `AsOfDate + floor(Delivered_DOH)`
- Else: use `Projected_OOS_Date`
- Blank when `Pallets_Required = 0`

**Variant B triggers** when the task spec mentions "if inbound arrives before OOS, use delivered coverage date" or similar conditional language. Always verify which variant the task requires.

## Rounding Applied Column

Some output specs include a `Rounding_Applied` boolean column:
- `TRUE` if `ceil(additional / cases_per_pallet) != (additional / cases_per_pallet)`
- `FALSE` if the division is exact (no rounding needed)
- Always `FALSE` when `additional <= 0` or `pallets = 0`

## Composite Grouping Keys

When inventory data is keyed by multiple dimensions (e.g., Branch+Item, Zone+SKU, Route+SKU, Aisle+Product), treat the **full composite key** as the grouping identifier for inbound aggregation. Do not aggregate by Item alone if the same Item appears in multiple Branches/Zones/Routes.

```python
# Group by composite key for inbound matching
transfers['group_key'] = transfers['Branch'].astype(str) + '|' + transfers['Item'].astype(str)
# Match stock rows using the same composite key
```

## Per-Composite-Key Load Size Lookup (Pack Matrix Pattern)

When load/pallet size varies by route+SKU (not a single global value):
1. Load the Pack Matrix sheet: columns typically `[Route, SKU, Cases_Per_Load]`
2. Build a lookup dict keyed by composite: `{(route, sku): cases_per_load}`
3. Use this dict during pallet/load calculation instead of a single `CasesPerPallet` value:
   ```python
   cases_per_load = pack_matrix.get((route, sku), default_cases_per_load)
   pallets = ceil(additional / cases_per_load) if additional > 0 else 0
   ```
4. **Normalize keys**: Strip prefixes like `"Route "` from parsed route values before building the lookup.

## Grouped/Sectioned Sheet Layouts
When inventory data is split into blocks separated by section headers (e.g., `Lane: COOLER-A`, `Zone: B`, `Route R-100`), `pandas` will misalign columns. Use `openpyxl` row-by-row iteration:
1. Scan rows sequentially.
2. Detect section headers: typically a single non-empty cell or a cell starting with a known prefix (e.g., "Lane:", "Zone:", "Aisle:", "Route ").
3. Extract the group key (e.g., `COOLER-A`, `R-100`) from the header text. **Strip the prefix** (e.g., `"Route "`) to get the canonical key for matching.
4. Assign the group key to all subsequent data rows until the next section header or EOF.
5. Skip the section header row and any intermediate blank rows when building the data frame.

See `references/formulas.md` for a complete `openpyxl` grouped parser implementation.

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

## Handling Excel Formulas in Source Data

When source cells contain formulas (e.g., `=80*C2`), openpyxl returns the formula string, not the computed value. Evaluate manually:

```python
# If column contains formulas like '=80*C2', calculate from referenced cells
for row_idx, row in enumerate(shipment_rows, start=2):  # Excel is 1-indexed
    pallets = ws.cell(row=row_idx, column=3).value  # Column C
    cases = pallets * cases_per_pallet  # Calculate instead of reading formula
```

## Mixed Date Format Handling

Source files may contain dates in multiple formats within the same column:
- Python datetime objects (from openpyxl): `datetime.datetime(2025, 7, 6, 0, 0)`
- ISO strings: `'2025-07-03'`
- Excel serial dates: numbers like `45832`

```python
from datetime import datetime, timedelta

def parse_date(val):
    if isinstance(val, datetime):
        return val.date() if hasattr(val, 'date') else val
    if isinstance(val, str):
        return datetime.strptime(val, '%Y-%m-%d').date()
    if isinstance(val, (int, float)):
        return datetime(1899, 12, 30) + timedelta(days=int(val))
    return None
```

## Column Name Variations

Source files use varying terminology. Map these common synonyms:

| Concept | Common Column Names |
|---------|---------------------|
| Item Code | SKU, SKU Ref, Item_Code, Product_ID, Material, Item |
| On Hand | On_Floor_Cases, Cases_On_Rack, Units_On_Hand, Cases_On_Hand, Current_Stock, Units, Stock_Units, Units_On_Hand, On_Hand_Cases |
| Daily Rate | Daily_Sales, Avg_Daily_Pull, Daily_Rate, Sales_Velocity, Daily_Usage, Daily_Use_Units_Per_Day, Daily_Rate_Units_Per_Day, Daily_Demand, Daily_Demand_Cases_Per_Day |
| Arrivals | Scheduled_Inbounds, Booking_Feed, Expected_Arrivals, Inbound_Shipments, Planned_Transfers, Transfer_Schedule, Recovery_Log, Queue_Export |
| Arrival Date | Arrival_Date, ETA, Expected_Date, Dock_Date, Transfer_Date, Load_Date, Ship_Date |
| Dock Status | Dock_Status, Booking_State, Status, Shipment_Status, Confirm_Status, Load_Status, Transfer_Status, Queue_State, Stage |
| Cases/Units Due | Booked_Cases, Cases_Due, Qty, Cases, Units_Planned, Transfer_Units, Units, Revision |
| Grouping Key | Branch, Lane, Zone, Aisle, Warehouse, Location, Route |
| Pallet/Load Size | CasesPerPallet, UnitsPerPallet, Cases_Per_Pallet, CasesPerLoad, Units_Per_Load, Cases_Per_Load |
| Row Type | Row_Type, Record_Type, Entry_Type |
| Route Alias | Route_Alias, Alias_Name, Dispatch_Alias, Alias |
| Revision | Revision_No, Revision, Version, Rev |

## Status Filtering

When inbound/booking data includes a status column, filter before aggregating:

```python
CONFIRMED_STATUSES = {'Committed', 'Arranged', 'Confirmed', 'Approved', 'Firm', 'Locked', 'Ready', 'Docked', 'In Transit', 'Booked', 'Loaded', 'Released'}
UNCERTAIN_STATUSES = {'Pending', 'Tentative', 'Planned', 'Proposed', 'Unconfirmed', 'Hold', 'Draft', 'Cancelled'}

# Filter to only confirmed inbounds
qualifying = inbounds[inbounds['Status'].isin(CONFIRMED_STATUSES)]
# Or exclude uncertain ones
qualifying = inbounds[~inbounds['Status'].isin(UNCERTAIN_STATUSES)]
```

**Inference Rule**: If unfamiliar statuses appear, infer reliability from context. Words implying physical presence or finalization (`Ready`, `Docked`, `At Dock`, `In Transit`, `Confirmed`, `Booked`, `Loaded`, `Released`, `Approved`) are safe to include. Words implying planning or uncertainty (`Draft`, `Planned`, `Tentative`, `Forecasted`, `Cancelled`, `Pending`) must be excluded.

**Why this matters**: Counting pending, tentative, or held arrivals overstates available inventory, leading to missed reorder points and stockouts.

## Key Formulas

| Metric | Formula |
|--------|----------|
| Current Days On Hand | `on_floor / daily_sales` |
| Projected OOS Date | `as_of_date + floor(days_on_hand)` |
| Delivered Days On Hand | `(on_floor + inbound_cases) / daily_sales` |
| Remaining Demand Cases | `daily_sales × planning_days` |
| Additional Cases Needed | `max(0, remaining_demand - on_floor - inbound_cases)` |
| Pallets/Loads Required | `ceil(additional_cases / cases_per_pallet)` |
| Required Delivery Date | See "Required Delivery Date Variants" above |
| Earlier Delivery Required | `True` if loads > 0 AND (no qualifying inbound OR earliest qualifying inbound > required_date) |

## Edge Cases

- **Zero on_floor**: Days on hand = 0, OOS date = as_of_date, immediate action needed
- **No scheduled inbound**: Treat inbound_cases = 0, still calculate requirements
- **Inbound after horizon**: Exclude from booked_cases count; still consider for earlier delivery flag if OOS before that inbound's date
- **Excess inventory**: Additional cases needed = 0, no pallets required
- **All inbounds uncertain**: Treat as no inbound, set earlier_delivery = True
- **Invalid dates in booking feed**: Skip rows with unparseable dates (e.g., text strings, blanks)
- **Missing item references**: Skip booking rows where SKU/Item_Code is blank
- **Note/metadata rows in booking feed**: Skip rows that contain only comments or planner notes
- **Duplicate transfer/booking/load IDs**: Deduplicate by latest date or highest revision FIRST, then filter by status
- **Unknown aliases**: Discard inbound rows whose alias cannot be resolved to a canonical key
- **Missing load size in Pack Matrix**: Warn and skip loads calculation for that route/SKU, or use a default

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

### clinic-branch-transfer-gap (variant)
- Sheet names: "Branch Stock", "Planned Transfers"
- Metadata in row 0 (A1=AsOfDate label, B1=value, C1=HorizonEnd label, D1=value)
- Headers at row 2, data starts row 3
- Transfer feed: headers at row 0, data starts row 1
- Composite grouping key: Branch + Item
- Transfer IDs may appear multiple times; deduplicate by latest date before status filtering
- Output sheets: "Branch_Item_Coverage" (metadata + calculations), "Transfer_Gap_List" (filtered actions)

### route-dispatch-tracker (variant)
- Sheet names: "Route Snapshot", "Queue Export", "Pack Matrix", "Route Alias Map", "Overview"
- Route Snapshot: section headers like `"Route R-100"` followed by SKU rows (SKU, On Hand Cases, Daily Demand)
- Metadata in row 0 (A1=AsOfDate, B1=value, C1=HorizonEnd, D1=value)
- Queue Export: columns include Row Type, Queue ID, Revision No, Route Alias, SKU, Ship Date, Cases, Queue State
- Row Type filter: only process rows where Row Type = "DISPATCH"
- Dedup by Queue ID (highest Revision No), then filter to Approved/Released states
- Alias resolution: Route Alias Map sheet maps aliases (NORTH-100, R100-A) to canonical routes (R-100)
- Pack Matrix: per-route/SKU Cases Per Load lookup (Route, SKU, Cases Per Load)
- **Critical**: Strip `"Route "` prefix from parsed route section headers before matching Pack Matrix or alias map
- Output sheets: "Coverage_Detail" (metadata row 1-4, then header row 6, then data), "Dispatch_Plan" (header row 1, then filtered actions)
- Preserve Overview, Pack Matrix, Route Alias Map sheets unchanged

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
- **Assuming pandas handles grouped layouts**: Use `openpyxl` row-by-row parsing when sheets contain interleaved section headers.
- **Filtering status before deduplication**: When duplicate IDs exist, deduplicate by latest date or highest revision FIRST, then filter by status. Filtering first may discard the correct row.
- **Aggregating by single key when composite is needed**: If data is keyed by Branch+Item or Zone+SKU or Route+SKU, use the full composite key for inbound matching.
- **Forgetting to remove openpyxl default sheet**: `openpyxl.Workbook()` always creates a default "Sheet". Remove it before saving: `wb.remove(wb.active)` if `wb.active.title == "Sheet"`.
- **Confusing horizon-filtered inbound with all qualifying loads**: Inbound count only includes loads within horizon; earlier delivery check considers ALL qualifying loads regardless of date.
- **Not normalizing group keys**: Section headers like `"Route R-100"` must be stripped to `"R-100"` before matching against Pack Matrix or alias maps. Mismatched keys cause silent lookup failures.
- **Skipping alias resolution**: When source data uses aliases, resolve them to canonical keys BEFORE matching against stock rows. Unknown aliases should be discarded.
- **Using global CasesPerPallet when per-item lookup exists**: Check for a Pack Matrix or per-route/SKU load size table before falling back to a single global value.
- **Assuming simple Required_Delivery_Date formula**: Some tasks use conditional logic (see "Required Delivery Date Variants"). Always check the output spec.
- **Reading formula cells as values**: openpyxl returns formula strings, not computed values. Calculate from source cells instead.
- **Assuming uniform date formats**: Source files may mix datetime objects, ISO strings, and Excel serial dates in the same column. Use a unified parser function.

## Scripts

- Run `scripts/load_plan_calculator.py` for reference implementation of all calculations.
- See `references/formulas.md` for detailed formula specification, status mapping tables, deduplication patterns, and `openpyxl` grouped layout parser examples.