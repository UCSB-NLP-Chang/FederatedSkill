---
name: excel-inventory-calculations
description: Read multi-sheet Excel workbooks containing inventory, shipment, and ratio data; perform supply chain calculations (DOH, OOS, demand forecasting, pallet rounding, delivery scheduling); and generate verified output workbooks. Use when tasks involve parsing .xlsx files with mixed date formats, computing inventory metrics, and writing structured results back to Excel.
---

# Excel Inventory Calculations & Workbook Generation

## Environment Setup
- `openpyxl` is often missing in containerized environments.
- If `pip install openpyxl` fails with `externally-managed-environment`, use:
  ```bash
  pip install openpyxl --break-system-packages -q
  ```
- Always verify installation before running calculation scripts.

## Reading Source Workbooks
- Source workbooks typically contain multiple sheets (e.g., `Current Inventory`, `Incoming Shipments`, `Ratio`).
- **Date parsing**: Dates may appear as `datetime` objects or ISO strings (`YYYY-MM-DD`). Normalize all dates to `datetime.date` before arithmetic.
- Use `data_only=True` when loading if formulas exist, but for raw data extraction, default loading is fine.
- Extract metadata from header rows (e.g., `Today's Date`, `Month End`).

## Calculation Workflow
1. **Days on Hand (DOH)**: `current_cases / daily_rate`
2. **Projected OOS Date**: `as_of_date + timedelta(days=DOH)`
3. **Inbound Cases**: Sum cases from incoming shipments within the planning horizon.
4. **Delivered DOH**: `inbound_cases / daily_rate`
5. **Remaining Demand**: `daily_rate * remaining_days_in_horizon`
6. **Additional Cases Needed**: `remaining_demand - inbound_cases`
7. **Pallets Required**: `math.ceil(additional_cases / cases_per_pallet)`
8. **Required Delivery Date**:
   - If `earliest_inbound_date <= oos_date`: `as_of_date + floor(delivered_doh)`
   - Else: `oos_date`
9. **Earlier Delivery Required**: `required_delivery_date < earliest_inbound_date`
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
- Format dates as ISO strings (`.isoformat()`) or keep as `datetime` objects consistently.
- Round floating-point results to 4 decimal places for DOH values.

## Output precision
This skill specifies rounding rules for certain metrics. Follow these exactly:
- **DOH values**: round to 4 decimal places (e.g., `round(doh, 4)`)
- **Other numeric outputs** (cases, pallets, demand): pass raw values, no rounding
- **DO NOT** apply additional rounding beyond what's specified above
- **DO NOT** use `format(x, ".2f")`, `f"{x:.2f}"`, or `.toFixed(N)` for any numeric output
- The verifier's tolerance decides acceptable precision; give it what the skill specifies and let it decide

## Verification Steps
1. Reload the generated workbook with `openpyxl.load_workbook()`.
2. Verify sheet names, row counts, and column headers match requirements.
3. Spot-check edge cases:
   - SKUs where `earliest_inbound_date < as_of_date`
   - SKUs where `earliest_inbound_date > oos_date` (triggers `Earlier_Delivery_Required`)
   - Division-by-zero or zero-rate scenarios
4. Confirm boolean flags and rounding logic match expected outputs.

## Anti-Patterns to Avoid
- **Do not** use f-strings with inline conditionals for formatting: `f"{val:.4f if val else 'N/A'}"` → SyntaxError. Pre-compute the formatted string.
- **Do not** assume all dates in Excel are `datetime` objects. Check `isinstance(val, str)` and parse with `datetime.fromisoformat()` or `datetime.strptime()`.
- **Do not** skip `--break-system-packages` in root containers if `pip` fails; it's safe in ephemeral environments.
- **Do not** write calculation scripts inline in the shell. Use `write_file` to create a `.py` script, then execute it. This avoids escaping issues and enables debugging.

## Troubleshooting
- `ModuleNotFoundError: No module named 'openpyxl'` → Install with `--break-system-packages`.
- `SyntaxError: positional argument follows keyword argument` → Add `value=` to all `ws.cell()` calls.
- `TypeError: unsupported operand type(s) for /: 'str' and 'float'` → Normalize date/numeric types before arithmetic.
- Incorrect delivery dates → Verify the `earliest_inbound_date <= oos_date` branching logic and ensure `floor()`/`ceil()` are applied correctly.