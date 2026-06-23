---
name: inventory-metrics-calculation
description: Read multi-sheet Excel workbooks containing entity, incoming, and ratio data; perform capacity/coverage calculations (DOH/coverage days, shortage dates, inbound aggregation, delivered coverage, demand forecasting, block/pallet rounding, scheduling); and generate verified output workbooks. Use when tasks involve parsing .xlsx files with mixed date formats, computing inventory or staffing metrics, and writing structured results back to Excel.
---

# Inventory & Capacity Metrics Calculation

## Environment Setup
- `openpyxl` is often missing in containerized environments.
- If `pip install openpyxl` fails with `externally-managed-environment`, use:
  ```bash
  pip install openpyxl --break-system-packages -q
  ```
- Always verify installation before running calculation scripts.

## Reading Source Workbooks
- Source workbooks typically contain three sheets: `Current [Entity]`, `Incoming [Entity]`, `Ratio`.
- **Date parsing**: Dates may appear as `datetime` objects or ISO strings (`YYYY-MM-DD`). Normalize all dates to `datetime.date` before arithmetic.
- Use `data_only=True` when loading if formulas exist, but for raw data extraction, default loading is fine.
- Extract metadata from header rows (e.g., `Today's Date`, `Month End`, `AsOfDate`, `PlanningHorizonEnd`).

## Core Calculation Workflow
1. **Coverage Days / DOH**: `current_amount / daily_rate`
2. **Projected Shortage Date**: `as_of_date + timedelta(days=Coverage_Days)`
3. **Inbound Amount**: Sum amounts from incoming records where `date <= PlanningHorizonEnd`.
4. **Delivered Coverage**: `(current_amount + inbound_amount) / daily_rate`
5. **Remaining Demand**: `daily_rate * remaining_days_in_horizon`
6. **Additional Amount Needed**: `max(0, remaining_demand - current_amount - inbound_amount)`
7. **Blocks/Pallets Required**: `math.ceil(additional_amount / units_per_block)`
8. **Required Start/Delivery Date**:
   - If `earliest_inbound_date <= projected_shortage_date`: `as_of_date + floor(delivered_coverage)`
   - Else: `projected_shortage_date`
9. **Earlier Delivery/Shift Required**: `blocks > 0 AND required_date < earliest_inbound_date`
10. **Rounding Applied**: `additional_amount % units_per_block != 0`

## Staffing & Shift Scheduling Variant
When the domain is hospital staffing or shift scheduling, map columns as follows:
- `Current_Staff_Hours` → `current_amount`
- `Daily_Required_Hours` → `daily_rate`
- `Current_Coverage_Days` → `Coverage Days`
- `Projected_Understaff_Date` → `Projected Shortage Date`
- `Incoming_Hours_By_Horizon` → `Inbound Amount`
- `Delivered_Coverage_To_Horizon` → `Delivered Coverage`
- `Remaining_Demand_Hours` → `Remaining Demand`
- `Additional_Hours_Needed` → `Additional Amount Needed`
- `Shift_Blocks_Required_Rounded_Up` → `Blocks Required`
- `Hours_Per_Shift_Block` → `units_per_block`
- **Zero-rate handling**: If `daily_rate == 0`, output blanks for coverage days, shortage date, and delivered coverage. Set remaining demand and additional hours to `0`.

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
  # CORRECT - displays as TRUE/FALSE in Excel
  ws.cell(row=r, column=c, value=bool(rounding_applied))
  # WRONG - displays as 1 or 0 in Excel
  ws.cell(row=r, column=c, value=1 if condition else 0)
  ```
- Format dates as ISO strings (`.isoformat()`) or keep as `datetime` objects consistently.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Verification Steps
1. Reload the generated workbook with `openpyxl.load_workbook()`.
2. Verify sheet names, row counts, and column headers match requirements.
3. Spot-check edge cases:
   - Entities where `earliest_inbound_date < as_of_date`
   - Entities where `earliest_inbound_date > shortage_date` (triggers `Earlier_Required`)
   - Division-by-zero or zero-rate scenarios (must output blanks/zeros, not crash)
4. Confirm boolean flags and rounding logic match expected outputs.

## Anti-Patterns to Avoid
- **Do not** use f-strings with inline conditionals for formatting: `f"{val:.4f if val else 'N/A'}"` → SyntaxError. Pre-compute the formatted string.
- **Do not** assume all dates in Excel are `datetime` objects. Check `isinstance(val, str)` and parse with `datetime.fromisoformat()` or `datetime.strptime()`.
- **Do not** skip `--break-system-packages` in root containers if `pip` fails; it's safe in ephemeral environments.
- **Do not** write calculation scripts inline in the shell. Use `write_file` to create a `.py` script, then execute it. This avoids escaping issues and enables debugging.
- **Do not** filter incoming records by horizon when finding `earliest_inbound_date`. The earliest date should consider *all* inbound records for the entity, not just those within the planning horizon.

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
- Preserve source entity order in output.
- Filter `Additional_Shifts_Needed` sheet to only entities where `Blocks_Required > 0`.

## Troubleshooting
- `ModuleNotFoundError: No module named 'openpyxl'` → Install with `--break-system-packages`.
- `SyntaxError: positional argument follows keyword argument` → Add `value=` to all `ws.cell()` calls.
- `TypeError: unsupported operand type(s) for /: 'str' and 'float'` → Normalize date/numeric types before arithmetic.
- Incorrect delivery/shift dates → Verify the `earliest_inbound_date <= shortage_date` branching logic and ensure `floor()`/`ceil()` are applied correctly.
- Zero-rate crashes → Guard division with `if rate == 0: coverage = None` before computing dates.