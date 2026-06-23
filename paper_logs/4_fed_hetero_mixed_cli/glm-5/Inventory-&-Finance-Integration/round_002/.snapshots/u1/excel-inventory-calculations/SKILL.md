---
name: excel-inventory-calculations
description: Read multi-sheet Excel workbooks containing inventory, staffing, or capacity data; perform supply chain and resource calculations (DOH, OOS, coverage days, demand forecasting, unit rounding, scheduling); and generate verified output workbooks. Use when tasks involve parsing .xlsx files with mixed date formats, computing capacity metrics, and writing structured results back to Excel. Applies to inventory management, hospital staffing, workforce planning, and similar capacity planning domains.
---

# Excel Inventory & Capacity Planning Calculations

## Environment Setup
- `openpyxl` is often missing in containerized environments.
- If `pip install openpyxl` fails with `externally-managed-environment`, use:
  ```bash
  pip install openpyxl --break-system-packages -q
  ```
- Always verify installation before running calculation scripts.

## Domain Mapping
This skill applies to multiple domains with analogous calculations:

| Inventory Domain | Staffing Domain | Calculation |
|-----------------|-----------------|-------------|
| Current Inventory | Current Staff Hours | Starting capacity |
| Daily Rate | Daily Required Hours | Consumption/demand rate |
| DOH (Days on Hand) | Coverage Days | `current / daily_rate` |
| OOS Date | Understaff Date | `as_of + coverage_days` |
| Cases per Pallet | Hours per Shift Block | Unit conversion factor |
| Pallets Required | Shift Blocks Required | `ceil(needed / unit_size)` |
| Incoming Shipments | Incoming Shifts | Scheduled additions |
| Earlier Delivery Required | Earlier Shift Required | Scheduling conflict flag |

## Reading Source Workbooks
- Source workbooks typically contain multiple sheets (e.g., `Current Inventory`, `Incoming Shipments`, `Ratio` or `Current Staffing`, `Incoming Shifts`, `Ratio`).
- **Date parsing**: Dates may appear as `datetime` objects or ISO strings (`YYYY-MM-DD`). Normalize all dates to `datetime.date` before arithmetic.
- Use `data_only=True` when loading if formulas exist, but for raw data extraction, default loading is fine.
- Extract metadata from header rows (e.g., `Today's Date`, `Month End`, `As Of Date`).

## Calculation Workflow
1. **Days on Hand / Coverage Days**: `current_cases / daily_rate`
2. **Projected OOS / Understaff Date**: `as_of_date + timedelta(days=DOH)`
3. **Inbound Cases / Hours**: Sum cases/hours from incoming shipments/shifts within the planning horizon.
4. **Delivered DOH / Coverage**: `inbound_cases / daily_rate`
5. **Remaining Demand**: `daily_rate * remaining_days_in_horizon`
6. **Additional Cases / Hours Needed**: `remaining_demand - inbound_cases`
7. **Pallets / Shift Blocks Required**: `math.ceil(additional_cases / cases_per_pallet)`
8. **Required Delivery / Shift Start Date**:
   - If `earliest_inbound_date <= oos_date`: `as_of_date + floor(delivered_doh)`
   - Else: `oos_date`
9. **Earlier Delivery / Shift Required**: `required_delivery_date < earliest_inbound_date`
10. **Rounding Applied**: `additional_cases % cases_per_pallet != 0`

## Writing Output Workbooks
- Create separate sheets for metadata/results and summary/flagged items.
- **Critical `openpyxl` API rule**: Always use `value=` keyword argument in `ws.cell()`. Never mix positional and keyword arguments.
  ```python
  # CORRECT
  ws.cell(row=r, column=c, value=some_value)
  # WRONG (SyntaxError)
  ws.cell(row=r, column=c, some_value)
  ```
- **Boolean values**: Must be Python `bool` type (`True`/`False`), not integers (`1`/`0`). Integers appear as numbers in Excel, not TRUE/FALSE.
  ```python
  # CORRECT
  ws.cell(row=r, column=c, value=bool(rounding_applied))
  # WRONG - appears as 1 or 0 in Excel
  ws.cell(row=r, column=c, value=1 if condition else 0)
  ```
- Format dates as ISO strings (`.isoformat()`) or keep as `datetime` objects consistently.
- Round floating-point results to 4 decimal places for DOH/coverage values.

## Two-Sheet Output Pattern
For planning calculations, use this structure:
1. **Results Sheet**: All items with metadata header (AsOfDate, PlanningHorizonEnd, etc.) followed by all rows with calculated fields.
2. **Flagged Items Sheet**: Only items meeting specific criteria (e.g., needing additional resources), with subset of columns for actionability.

## Output precision
This skill specifies rounding rules for certain metrics. Follow these exactly:
- **DOH/Coverage values**: round to 4 decimal places (e.g., `round(doh, 4)`)
- **Other numeric outputs** (cases, pallets, hours, blocks): pass raw values, no rounding
- **DO NOT** apply additional rounding beyond what's specified above
- **DO NOT** use `format(x, ".2f")`, `f"{x:.2f}"`, or `.toFixed(N)` for any numeric output
- The verifier's tolerance decides acceptable precision; give it what the skill specifies and let it decide

## Verification Steps
1. Reload the generated workbook with `openpyxl.load_workbook()`.
2. Verify sheet names, row counts, and column headers match requirements.
3. Check boolean columns contain actual `bool` values, not integers:
   ```python
   for row in ws.iter_rows(min_row=2, max_col=col_idx):
       assert isinstance(row[0].value, bool), f"Expected bool, got {type(row[0].value)}"
   ```
4. Spot-check edge cases:
   - Items where `earliest_inbound_date < as_of_date`
   - Items where `earliest_inbound_date > oos_date` (triggers `Earlier_Delivery_Required`)
   - Division-by-zero or zero-rate scenarios
5. Confirm boolean flags and rounding logic match expected outputs.

## Anti-Patterns to Avoid
- **Do not** use f-strings with inline conditionals for formatting: `f"{val:.4f if val else 'N/A'}"` → SyntaxError. Pre-compute the formatted string.
- **Do not** assume all dates in Excel are `datetime` objects. Check `isinstance(val, str)` and parse with `datetime.fromisoformat()` or `datetime.strptime()`.
- **Do not** skip `--break-system-packages` in root containers if `pip` fails; it's safe in ephemeral environments.
- **Do not** write calculation scripts inline in the shell. Use `write_file` to create a `.py` script, then execute it. This avoids escaping issues and enables debugging.
- **Do not** use integers (`1`/`0`) for boolean columns. Use explicit `bool()` conversion to ensure Excel displays TRUE/FALSE.

## Troubleshooting
- `ModuleNotFoundError: No module named 'openpyxl'` → Install with `--break-system-packages`.
- `SyntaxError: positional argument follows keyword argument` → Add `value=` to all `ws.cell()` calls.
- `TypeError: unsupported operand type(s) for /: 'str' and 'float'` → Normalize date/numeric types before arithmetic.
- Boolean columns showing as `1`/`0` instead of TRUE/FALSE → Wrap values in `bool()` before writing to cells.
- Incorrect delivery dates → Verify the `earliest_inbound_date <= oos_date` branching logic and ensure `floor()`/`ceil()` are applied correctly.
- Zero division errors → Check for zero daily rate before calculating DOH/coverage; set to `None` or handle separately.

## Known invariants (by sub-task)

### multi-sheet-inventory-workbook
- Input sheets: `Current Inventory`, `Incoming Shipments`, `Ratio`
- Header rows may be offset from row 1 (check rows 1-3 for metadata like `Today's Date`, `Month End`)
- Formula cells (e.g., `=80*C2` for cases) return `None` when read; calculate manually using constants from Ratio sheet
- Cases per pallet: 80 (standard ratio, verify in workbook)

### multi-sheet-staffing-workbook
- Input sheets: `Current Staffing`, `Incoming Shifts`, `Ratio`
- Metadata typically in `B1` (AsOfDate) and `D1` (PlanningHorizonEnd)
- `Hours_Per_Shift_Block` is in `Ratio` sheet (e.g., 24)
- Preserve source entity order in output
- Filter flagged/summary sheet to only entities where `Blocks_Required > 0`

### zero-rate-handling (all sub-tasks)
- If `daily_rate == 0`: output blanks for coverage/shortage date, zeros for demand/needed
- Do not filter incoming records by horizon when finding `earliest_inbound_date` — consider all inbound records for the entity
