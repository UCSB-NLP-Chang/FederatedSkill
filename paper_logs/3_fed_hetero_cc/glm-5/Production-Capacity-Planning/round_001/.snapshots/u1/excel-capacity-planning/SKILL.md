---
name: excel-capacity-planning
description: Handles tasks requiring reading Excel demand/capacity data, computing iterative weekly backlogs or catch-up schedules, and generating Excel plans with text summaries. Use when given spreadsheet data for production scheduling, inventory catch-up, or resource allocation over time.
---

# Excel Capacity & Backlog Planning

## Workflow
1. **Read Excel Data**: Use `openpyxl` in Python. Never use text-based `Read` tools on `.xlsx` files.
   ```python
   import openpyxl
   wb = openpyxl.load_workbook('input.xlsx', data_only=True)
   ws = wb.active
   data = [(row[0].value, row[1].value) for row in ws.iter_rows(min_row=2, values_only=True)]
   ```
2. **Define Capacity Rules**: Map days worked to standard hours and overtime limits based on task prompt.
   - Typical: 6 days = 180 hrs (20 OT), 5 days = 150 hrs, 4 days = 120 hrs.
3. **Iterative Calculation**: Loop through periods, updating backlog:
   `end_backlog = start_backlog + demand - capacity`
   - If `end_backlog > 0`, carry over to next period.
   - Adjust days worked/overtime based on backlog clearance rules.
   - Treat `end_backlog <= 0` as cleared. Do not force it to exactly 0.
4. **Step-Down Logic**: When backlog clears, check demand against capacity thresholds. Skip intermediate steps (e.g., 5-day weeks) if demand is already low enough for 4-day capacity.
5. **Generate Outputs**:
   - Write plan to new Excel sheet with exact headers requested.
   - Write summary to `.txt` with exact formatting. Use `N/A` for non-applicable transition weeks.
6. **Verify**: Re-read output files to confirm row counts, headers, and data integrity before finishing.

## Anti-Patterns & Troubleshooting
- **Do not** use generic file readers for `.xlsx`. Always use `openpyxl` or `pandas`.
- **Do not** assume backlog clears exactly at 0. It often goes slightly negative; treat `<= 0` as cleared.
- **Summary constraints**: Count words/sentences if constrained. Ensure exact key-value formatting.
- **Verification**: Always run a quick read-back script to validate headers, row counts, and week ranges.

## Scripts
- Run `scripts/capacity_planner_template.py` when starting a new capacity planning task. It provides the iterative calculation loop, Excel I/O boilerplate, and summary generation. Adapt `CAPACITY_RULES` and decision thresholds to match the specific task prompt before execution.