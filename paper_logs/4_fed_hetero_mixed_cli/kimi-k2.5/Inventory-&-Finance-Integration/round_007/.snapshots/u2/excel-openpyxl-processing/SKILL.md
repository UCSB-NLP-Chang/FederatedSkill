---
name: excel-openpyxl-processing
description: Read, transform, and write Excel workbooks for inventory, staffing, and capacity calculations. Handles multi-sheet workbooks with mixed date formats, performs DOH/coverage/OOS calculations, demand forecasting, unit rounding, scheduling flags, and generates verified output. Use for inventory management, hospital staffing, workforce planning, maintenance resupply, perishable/freshness inventory, and similar capacity planning domains.
---

# Excel Processing with Python (openpyxl)

## Environment Setup

**If** `import openpyxl` fails **OR** `pip install` returns `externally-managed-environment`:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install openpyxl -q
```

**Then** prefix all subsequent Python commands with venv activation:
```bash
source .venv/bin/activate && python3 script.py
```

## Universal Calculation Rules

### Inclusive Date Counting (Critical)
**Always use inclusive counting for days within a planning horizon.**
```python
# CORRECT - inclusive (includes both start and end dates)
remaining_days = (horizon_end - as_of_date).days + 1

# WRONG - exclusive (misses the last day)
remaining_days = (horizon_end - as_of_date).days
```
This applies to ALL domains: inventory, staffing, maintenance parts, meal kits, freshness, etc.

## Domain Mapping

| Inventory | Staffing | Maintenance Parts | Freshness/Meal Kits | Calculation |
|-----------|----------|-------------------|---------------------|-------------|
| Current Inventory | Current Staff Hours | Current Parts | Current Boxes | Starting capacity |
| Daily Rate | Daily Required Hours | Daily Consumption | Daily Order Rate | Consumption/demand rate |
| DOH | Coverage Days | Current DOH | Current DOH (usable) | `usable / rate` |
| OOS Date | Understaff Date | Stockout Date | Projected OOS | `as_of + coverage` |
| Cases per Pallet | Hours per Block | Units per Crate | Boxes per Pallet | Unit conversion |
| Pallets Required | Blocks Required | Crates Required | Pallets Required | `ceil(needed / unit)` |
| Earlier Delivery Required | Earlier Shift Required | Earlier Delivery Required | Earlier Delivery Required | Schedule conflict |
| Rounding Applied | Rounding Applied | Rounding Applied | Rounding Applied | Non-divisible remainder |
| — | — | — | Boxes Expiring | Usable = Current - Expiring |

## Core Calculation Workflow

1. **Usable Inventory** (freshness only): `usable = current_amount - expiring_amount` (max 0)
2. **Coverage Days / DOH**: `usable_amount / daily_rate` (None if rate=0)
3. **Projected Shortage/OOS Date**: `as_of_date + timedelta(days=floor(coverage_days))`
4. **Inbound Amount**: Sum amounts from incoming records where `date <= PlanningHorizonEnd`
5. **Delivered Coverage**: `(usable_amount + inbound_amount) / daily_rate`
6. **Remaining Demand**: `daily_rate * remaining_days_in_horizon`
7. **Additional Needed**: `max(0, remaining_demand - usable_amount - inbound_amount)`
8. **Blocks/Pallets/Crates Required**: `math.ceil(additional_amount / units_per_block)` (0 if additional <= 0)
9. **Required Start/Delivery Date**:
   - If `blocks == 0`: None/blank
   - If `earliest_inbound_date` exists and `<= shortage_date`: `as_of + floor(delivered_coverage)`
   - Else: `shortage_date`
10. **Earlier_Delivery_Required**: `blocks > 0 AND (earliest_inbound_date is None OR required_date < earliest_inbound_date)`
11. **Rounding_Applied**: `blocks > 0 AND (additional_amount % units_per_block) != 0`

## Reading Source Workbooks

- Sheets: `Current [Entity]`, `Incoming/Scheduled [Entity]`, `Ratio` or `Shelf_Life`
- **Date parsing**: Dates may be `datetime` objects or ISO strings. Normalize to `date`:
  ```python
  def to_date(val):
      if isinstance(val, str): return datetime.strptime(val, "%Y-%m-%d").date()
      if isinstance(val, datetime): return val.date()
      return val
  ```
- Extract metadata from header cells (B1=AsOfDate, D1=PlanningHorizonEnd typical)
- Formula cells (e.g., `=80*C2`) return `None`; calculate manually using Ratio/Shelf_Life constants
- **Freshness variant**: Look for `Boxes_Expiring_By_[Date]` or similar columns

## Writing Output Workbooks

- **Two-sheet structure**: Results (all items + metadata) + Filtered Action (items where blocks/crates > 0)
- **Critical API rule**: Always use `value=` keyword: `ws.cell(row=r, column=c, value=x)`
- **Boolean values**: Must be Python `bool` (`True`/`False`), not integers (`1`/`0`)
  ```python
  ws.cell(row=r, column=c, value=bool(flag))  # CORRECT
  ws.cell(row=r, column=c, value=1 if flag else 0)  # WRONG - shows as 1/0
  ```
- Dates as ISO strings: `date_obj.isoformat()`

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Verification Steps

1. Reload output workbook with `openpyxl.load_workbook()`
2. Verify sheet names, row counts, column headers
3. Check boolean columns contain `bool` values, not integers
4. Spot-check: earliest_inbound < as_of, earliest_inbound > shortage_date, zero-rate
5. Confirm filtered sheet only has rows where blocks/crates > 0
6. **Freshness check**: Verify Usable_Current_Boxes = Current - Expiring (not raw Current)
7. **Inclusive date check**: Verify `remaining_days = (horizon_end - as_of_date).days + 1`

## Anti-Patterns

- Do NOT use `--break-system-packages`; use venv approach for PEP 668
- Do NOT use f-strings with inline conditionals: `f"{val:.4f if val else 'N/A'}"` → SyntaxError
- Do NOT filter incoming records by horizon when finding `earliest_inbound_date` — use ALL records
- Do NOT use integers (`1`/`0`) for boolean columns
- Do NOT use total Current_Boxes for DOH when Expiring column exists; use Usable amount
- Do NOT use exclusive date counting: `(end - start).days` misses the last day. Always add 1.

## Known invariants (by sub-task)

### multi-sheet-inventory-workbook
- Sheets: `Current Inventory`, `Incoming Shipments`, `Ratio`
- Headers may be offset from row 1; check rows 1-3 for metadata
- Formula cells return `None`; calculate manually with Ratio constants
- Cases per pallet: typically 80 (verify in workbook)

### multi-sheet-staffing-workbook
- Sheets: `Current Staffing`, `Incoming Shifts`, `Ratio`
- Metadata: B1=AsOfDate, D1=PlanningHorizonEnd
- Preserve source entity order in output
- Filter action sheet to only `Blocks_Required > 0`

### maintenance-parts-workbook
- Sheets: `Current Parts`, `Scheduled Deliveries`, `Ratio`
- Scheduled Deliveries has both `Crates` and `Units` columns; use `Units` for calculation
- **Remaining days**: `(horizon_end - as_of).days + 1` (inclusive counting)
- **Earliest scheduled delivery**: Min date per part; `None` if no deliveries scheduled
- Filter action sheet to only `Crates_Required > 0`

### freshness-mealkit-inventory
- Sheets: `Current Inventory`, `Incoming Deliveries`, `Shelf_Life`
- **Critical**: Current Inventory includes `Boxes_Expiring_By_[Date]` column
- **Usable calculation**: `Usable_Current_Boxes = Current_Boxes - Boxes_Expiring` (use max(0, ...))
- All downstream calculations (DOH, coverage, additional needed) must use `Usable_Current_Boxes` as the starting point
- Shelf_Life sheet provides `Boxes_Per_Pallet` and `Minimum_RSL_Days`
- Daily_Rate is `Daily_Order_Rate_Boxes` from Current Inventory
- Otherwise follows standard 11-step calculation workflow

### zero-rate-handling (all variants)
- If `daily_rate == 0`: output blanks for coverage/shortage date, zeros for demand/needed
- Do not crash on division by zero

## References

See `references/code-patterns.md` for copy-paste templates including complete processing scripts, date utilities, calculation helpers, and freshness-specific patterns.
