---
name: inventory-load-planning
description: Calculate inventory load plans from stock snapshots and scheduled inbounds. Use when building OOS projections, pallet requirements, delivery schedules, or replenishment action summaries from Excel inventory data.
---

# Inventory Load Planning

## Workflow

1. **Inspect Source Structure**
   - Source files often have metadata rows before headers (AsOfDate, HorizonEnd)
   - If `pd.read_excel()` returns wrong columns, use `header=None` and inspect raw rows
   - Data typically starts 2-3 rows down with actual headers in row 2

2. **Read source workbook**: Parse stock snapshot, scheduled inbounds, and config sheets

3. **Extract Parameters**: Read `AsOfDate`, `HorizonEnd`, compute `PlanningDays = (HorizonEnd - AsOfDate).days`. Extract `CasesPerPallet`.

4. **Filter Inbounds by Status** (critical step):
   - Check if inbound data includes a status column (e.g., 'Dock Status', 'Status')
   - Only count inbounds with confirmed statuses: `Committed`, `Arranged`, `Confirmed`
   - Exclude uncertain statuses: `Pending`, `Tentative`, `Planned`, `Proposed`
   - If no status column exists, include all inbounds

5. **Calculate per-item metrics** (preserve source order):
   - `cur_doh = on_floor / daily_sales`
   - `oos_date = asof_date + timedelta(days=floor(cur_doh))`
   - `inbound_cases = sum(cases for qualifying inbounds where arrival_date <= horizon_end)`
   - `delivered_doh = (on_floor + inbound_cases) / daily_sales`
   - `remaining_demand = daily_sales * planning_days`
   - `additional = max(0, remaining_demand - on_floor - inbound_cases)`
   - `pallets = ceil(additional / cases_per_pallet)` if `additional > 0` else `0`
   - `req_date = oos_date` if `pallets > 0` else `None`
   - `earlier = True` if `no qualifying inbounds exist` OR `earliest_inbound > req_date` else `False`

6. **Write Output**: Create two sheets: `Load_Detail` (metadata + full calculations) and `Load_Action_Summary` (item, req_date, pallets, additional, earlier)

7. **Verify**: Read back output. Spot-check 2-3 items manually. Ensure sheet order and item order match requirements.

## Critical Parsing Rule

When standard pandas reading fails (e.g., "ValueError: could not convert string to float"):

```python
# Read without headers first to inspect structure
raw = pd.read_excel(path, sheet_name='Stock Snapshot', header=None)

# Extract metadata from specific cells
as_of_date = pd.to_datetime(raw.iloc[0, 1])
horizon_end = pd.to_datetime(raw.iloc[0, 3])

# Skip to actual data (row 2=headers, row 3+=data)
data = raw.iloc[3:].copy()
data.columns = ['Item_Code', 'On_Floor_Cases', 'Daily_Sales', '_drop']
data = data.drop('_drop', axis=1).reset_index(drop=True)
```

## Inbound Status Filtering

When inbound data includes a status column, filter before aggregating:

```python
CONFIRMED_STATUSES = {'Committed', 'Arranged', 'Confirmed', 'Approved'}
UNCERTAIN_STATUSES = {'Pending', 'Tentative', 'Planned', 'Proposed', 'Unconfirmed'}

# Filter to only confirmed inbounds
qualifying = inbounds[inbounds['Status'].isin(CONFIRMED_STATUSES)]
# Or exclude uncertain ones
qualifying = inbounds[~inbounds['Status'].isin(UNCERTAIN_STATUSES)]
```

**Why this matters**: Counting pending or tentative arrivals overstates available inventory, leading to missed reorder points and stockouts.

## Key Formulas

| Metric | Formula |
|--------|----------|
| Current Days On Hand | `on_floor / daily_sales` |
| Projected OOS Date | `as_of_date + floor(days_on_hand)` |
| Delivered Days On Hand | `(on_floor + inbound_cases) / daily_sales` |
| Remaining Demand Cases | `daily_sales × planning_days - on_floor - inbound_cases` |
| Additional Cases Needed | `max(0, remaining_demand)` |
| Pallets Required | `ceil(additional_cases / cases_per_pallet)` |
| Required Delivery Date | `projected_oos_date` (or earlier if stockout imminent) |
| Earlier Delivery Required | `True` if no qualifying inbound OR earliest inbound > required_date |

## Edge Cases

- **Zero on_floor**: Days on hand = 0, OOS date = as_of_date, immediate action needed
- **No scheduled inbound**: Treat inbound_cases = 0, still calculate requirements
- **Inbound after horizon**: Include in calculations but flag for earlier delivery
- **Excess inventory**: Additional cases needed = 0, no pallets required
- **All inbounds uncertain**: Treat as no inbound, set earlier_delivery = True

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
- **Zero Daily Sales**: Guard against division by zero. If `daily_sales == 0`, set DOH to `None`.
- **Negative Additional Needed**: Always apply `max(0, ...)`.
- **Skipping verification**: Always confirm output workbook structure and calculations.
- **Counting uncertain inbounds**: Exclude Pending/Tentative statuses to avoid false coverage.

## Scripts

- Run `scripts/load_plan_calculator.py` for reference implementation of all calculations.
- See `references/formulas.md` for detailed formula specification with examples.