---
name: excel-inventory-coverage
description: Analyze multi-sheet Excel inventory workbooks to compute rack coverage, filter valid bookings, and generate commit gap reports. Use when tasks involve calculating days-on-hand, projecting out-of-stock dates, and identifying pallet delivery requirements from snapshot and booking feeds.
---

# Excel Inventory Coverage & Gap Analysis

## When to Use
- Input is a multi-sheet `.xlsx` file containing inventory snapshots, booking feeds, and pallet defaults.
- Task requires calculating coverage gaps, filtering invalid/tentative bookings, and outputting a structured gap report.
- **Do not** use generic text/`Read` tools on `.xlsx` files; they will fail. Use `openpyxl` via Python.

## Core Workflow
1. **Load Workbook**: Use `openpyxl.load_workbook()` in Python.
2. **Normalize Dates**: Immediately convert all date/datetime values to a single type (`datetime.date`) before any comparisons. Mixing `datetime.datetime` and `datetime.date` causes `TypeError`.
3. **Filter Bookings**: Exclude rows with:
   - Blank SKU references
   - Non-firm states (`Tentative`, `Hold`, `Cancelled`)
   - Invalid or non-parseable ETA dates
   - ETAs strictly after `HorizonEnd`
4. **Calculate Coverage**:
   - `Days_On_Hand = Cases_On_Rack / Avg_Daily_Pull`
   - `Projected_OOS = AsOfDate + Days_On_Hand`
   - `Remaining_Demand = Avg_Daily_Pull * PlanningDays`
   - `Additional_Needed = max(0, Remaining_Demand - (Cases_On_Rack + Valid_Booked_Cases))`
   - `Pallets_Required = ceil(Additional_Needed / Cases_Per_Pallet)`
5. **Determine Delivery Urgency**: Compare `Required_Delivery_Date` (usually OOS date) against existing valid booking ETAs. Set `Earlier_Delivery_Required = True` if no valid booking exists or if the earliest valid booking ETA > Required Delivery Date.
6. **Generate Output**: Create a new `.xlsx` with `Rack_Coverage` (metadata + SKU rows) and `Commit_Gap_Actions` (only SKUs with `Additional_Needed > 0`).

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-Patterns & Troubleshooting
- **TypeError on date comparison**: Always wrap date values with a normalization helper before `>` or `<` checks.
- **Tentative/Hold bookings**: Never count these toward firm coverage.
- **Blank/Invalid rows**: Skip rows where SKU is `None` or ETA fails parsing.
- **Source modification**: Always open source workbooks in read-only mode or verify checksums post-run to ensure no accidental writes.

## Execution
Run `scripts/calculate_coverage.py <input.xlsx> <output.xlsx>` for a deterministic baseline. Adjust column indices in the script if the source schema varies. Ensure `openpyxl` is installed (`pip install openpyxl`.