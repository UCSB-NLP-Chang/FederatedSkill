---
name: excel-capacity-planning
description: Handles tasks requiring reading Excel demand/capacity data, computing iterative weekly backlogs or catch-up schedules, and generating Excel plans with text summaries. Use when given spreadsheet data for production scheduling, inventory catch-up, or resource allocation over time.
---

# Excel Capacity & Backlog Planning

## Workflow
1. **Read Excel Data**: Use `openpyxl` in Python. Never use text-based `Read` tools on `.xlsx` files.
   - **Detect Orientation**: Weeks may be in columns (transposed) or rows. Scan headers to find week numbers. If transposed, extract the demand row and align it with weeks.
   ```python
   # Example transposed extraction
   ws = wb.active
   weeks = [cell.value for cell in ws[header_row][start_col:] if cell.value is not None]
   demands = [cell.value for cell in ws[demand_row][start_col:]]
   ```
2. **Define Capacity Rules**: Map days worked to standard hours and overtime limits based on task prompt.
   - Typical: 6 days = 180 hrs (20 OT), 5 days = 150 hrs, 4 days = 120 hrs.
3. **Iterative Calculation**: Loop through periods, updating backlog:
   - Maintain `calc_backlog` (can be negative, acts as buffer).
   - `calc_backlog = calc_backlog + demand - capacity`
   - For output columns like "Start of Week Past Due", use `max(0, calc_backlog)`.
   - If `calc_backlog <= 0`, backlog is cleared. Do not force it to exactly 0 in calculations.
4. **Step-Down Logic**: When backlog clears, check demand against capacity thresholds. Skip intermediate steps (e.g., 5-day weeks) if demand is already low enough for 4-day capacity.
   - **Oscillation Handling**: If demand exceeds the stepped-down capacity, backlog will re-accumulate. Allow the schedule to step back up to 6 days if `calc_backlog > 0` or `demand > capacity`.
5. **Generate Outputs**:
   - Write plan to new Excel sheet with exact headers requested.
   - Write summary to `.txt` with exact formatting. Use `N/A` for non-applicable transition weeks.
6. **Verify**: Re-read output files to confirm row counts, headers, and data integrity before finishing.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.
- Backlog calculations often produce non-zero values (e.g., 0.5 hrs remaining);
  do not force to exactly 0. Use `<= 0` threshold for "cleared" status.

## Anti-Patterns & Troubleshooting
- **Do not** use generic file readers for `.xlsx`. Always use `openpyxl` or `pandas`.
- **Do not** assume vertical layout. Many capacity sheets place weeks in columns and metrics in rows. Always scan for week headers first.
- **Do not** assume backlog clears exactly at 0. It often goes slightly negative; treat `<= 0` as cleared.
- **Do not** use `round()` or `float` equality checks for backlog thresholds. Use `> 0.01` for "significant" backlog.
- **Summary constraints**: Count words/sentences if constrained. Ensure exact key-value formatting.
- **Verification**: Always run a quick read-back script to validate headers, row counts, and week ranges.

## Scripts
- Run `scripts/capacity_planner_template.py` when starting a new capacity planning task. It provides the iterative calculation loop, Excel I/O boilerplate, and summary generation. Adapt `CAPACITY_RULES` and decision thresholds to match the specific task prompt before execution.