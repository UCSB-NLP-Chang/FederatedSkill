---
name: inventory-load-planning
description: Calculate inventory load plans from stock snapshots and scheduled inbounds/bookings. Use when building OOS projections, pallet requirements, delivery schedules, or replenishment action summaries from Excel inventory data. Trigger on tasks involving stock snapshots, booking feeds, rack coverage, commit-gap analysis, or inbound planning workbooks.
---

# Inventory Load Planning

## Workflow

1. **Inspect Source Structure**
   - Source files often have metadata rows before headers (AsOfDate, HorizonEnd)
   - If `pd.read_excel()` returns wrong columns, use `header=None` and inspect raw rows
   - Data typically starts 2-3 rows down with actual headers in row 2 or 3

2. **Read source workbook**: Parse stock/rack snapshot, booking/inbound feed, and config sheets

3. **Extract Parameters**: Read `AsOfDate`, `HorizonEnd`, compute `PlanningDays = (HorizonEnd - AsOfDate).days`. Extract `CasesPerPallet`.

4. **Filter Inbounds/Bookings by Status** (critical step):
   - Check if inbound data includes a status column (e.g., 'Dock Status', 'Booking State', 'Status', 'Load Status')
   - Only count inbounds with confirmed statuses: `Committed`, `Arranged`, `Confirmed`, `Firm`, `Locked`, `Approved`, `Ready`, `Docked`, `In Transit`
   - Exclude uncertain statuses: `Pending`, `Tentative`, `Planned`, `Proposed`, `Hold`, `Unconfirmed`, `Draft`, `Cancelled`
   - If no status column exists, include all inbounds
   - Exclude rows with missing grouping keys (e.g., blank Lane/Zone/SKU)

5. **Clean Booking/Inbound Data**:
   - Skip rows with invalid/unparseable dates (e.g., "bad-date", text in date columns)
   - Skip rows with missing item references (blank SKU/Item_Code cells)
   - Skip metadata/note rows (e.g., "planner note row", comment-only rows)
   - Validate dates are within reasonable range before processing

6. **Calculate per-item metrics** (preserve source order):
   - `cur_doh = on_floor / daily_sales`
   - `oos_date = as_of_date + timedelta(days=floor(cur_doh))`
   - `inbound_cases = sum(cases for qualifying inbounds where arrival_date <= horizon_end)`
   - `delivered_doh = (on_floor + inbound_cases) / daily_sales`
   - `remaining_demand = daily_sales * planning_days`
   - `additional = max(0, remaining_demand - on_floor - inbound_cases)`
   - `pallets = ceil(additional / cases_per_pallet)` if `additional > 0` else `0`
   - `req_date = oos_date` if `pallets > 0` else `None`
   - `earlier = True` if `no qualifying inbounds exist` OR `earliest_inbound > req_date` else `False`

7. **Write Output**: Create two sheets: primary coverage sheet (metadata + full calculations) and action summary sheet (filtered to items where additional > 0)

8. **Verify**: Read back output. Spot-check 2-3 items manually. Ensure sheet order and item order match requirements.

## Grouped/Sectioned Sheet Layouts
When inventory data is split into blocks separated by section headers (e.g., `Lane: COOLER-A`, `Zone: B`), `pandas` will misalign columns. Use `openpyxl` row-by-row iteration:
1. Scan rows sequentially.
2. Detect section headers: typically a single non-empty cell or a cell starting with a known prefix (e.g., "Lane:", "Zone:", "Aisle:").
3. Extract the group key (e.g., `COOLER-A`) from the header text.
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

## Column Name Variations

Source files use varying terminology. Map these common synonyms:

| Concept | Common Column Names |
|---------|---------------------|
| Item Code | SKU, SKU Ref, Item_Code, Product_ID, Material |
| On Hand | On_Floor_Cases, Cases_On_Rack, Units_On_Hand, Cases_On_Hand, Current_Stock |
| Daily Rate | Daily_Sales, Avg_Daily_Pull, Daily_Rate, Sales_Velocity, Daily_Usage |
| Arrivals | Scheduled_Inbounds, Booking_Feed, Expected_Arrivals, Inbound_Shipments |
| Arrival Date | Arrival_Date, ETA, Expected_Date, Dock_Date |
| Dock Status | Dock_Status, Booking_State, Status, Shipment_Status, Confirm_Status, Load_Status |
| Cases Due | Booked_Cases, Cases_Due, Qty, Cases |

## Status Filtering

When inbound/booking data includes a status column, filter before aggregating:

```python
CONFIRMED_STATUSES = {'Committed', 'Arranged', 'Confirmed', 'Approved', 'Firm', 'Locked', 'Ready', 'Docked', 'In Transit'}
UNCERTAIN_STATUSES = {'Pending', 'Tentative', 'Planned', 'Proposed', 'Unconfirmed', 'Hold', 'Draft', 'Cancelled'}

# Filter to only confirmed inbounds
qualifying = inbounds[inbounds['Status'].isin(CONFIRMED_STATUSES)]
# Or exclude uncertain ones
qualifying = inbounds[~inbounds['Status'].isin(UNCERTAIN_STATUSES)]
```

**Inference Rule**: If unfamiliar statuses appear, infer reliability from context. Words implying physical presence or finalization (`Ready`, `Docked`, `At Dock`, `In Transit`, `Confirmed`) are safe to include. Words implying planning or uncertainty (`Draft`, `Planned`, `Tentative`, `Forecasted`, `Cancelled`) must be excluded.

**Why this matters**: Counting pending, tentative, or held arrivals overstates available inventory, leading to missed reorder points and stockouts.

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
- **Note/metadata rows in booking feed**: Skip rows that contain only comments or planner notes

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

## Scripts

- Run `scripts/load_plan_calculator.py` for reference implementation of all calculations.
- See `references/formulas.md` for detailed formula specification, status mapping tables, and `openpyxl` grouped layout parser examples.
