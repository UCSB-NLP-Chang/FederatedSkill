---
name: excel-capacity-planning
description: Handles tasks requiring reading Excel demand/capacity data, computing iterative weekly backlogs or catch-up schedules, and generating Excel plans with text summaries. Use when given spreadsheet data for production scheduling, inventory catch-up, or resource allocation over time.
---

# Excel Capacity & Backlog Planning

Build week-by-week production schedules where days-worked decisions depend on current backlog state.

## Core Concepts

- **Calc Start**: The mathematical backlog carried from previous week (can be negative = buffer)
- **Reported Start**: `max(0, calc_start)` - displayed as 0 when backlog is cleared
- **Decision Mode**: Determined by `reported_start > threshold` (typically 0.01), NOT by whether the chosen days would create new backlog

## Workflow

1. **Read Excel Data**: Use `openpyxl` in Python. Never use text-based `Read` tools on `.xlsx` files.
   ```python
   import openpyxl
   wb = openpyxl.load_workbook('input.xlsx', data_only=True)
   ws = wb.active
   data = [(row[0].value, row[1].value) for row in ws.iter_rows(min_row=2, values_only=True)]
   ```

   For row-based data (labels in column A, week data in columns 1-49), see `references/excel-patterns.md`.

2. **Define Capacity Rules**: Map days worked to standard hours and overtime limits based on task prompt.
   - Typical: 6 days = 180 hrs (20 OT), 5 days = 150 hrs, 4 days = 120 hrs.

3. **Iterative Calculation**: Loop through periods, updating backlog:
   - `calc_start[n+1] = calc_end[n]` (carry the mathematical value, including negatives)
   - `reported_start = max(0, calc_start)`
   - `calc_end = calc_start + demand - capacity`

   **Critical**: Treat `calc_end <= 0` as cleared. Do not force it to exactly 0.

4. **Apply Deterministic Policy** (follow exactly, do not add "smart" checks):
   ```
   IF reported_start > threshold:
       # Catch-up mode: try 5 days first, then 6
       FOR days IN [5, 6]:
           IF calc_start + demand - capacity(days) <= 0:
               chosen_days = days; BREAK
       ELSE:
           chosen_days = 6
   ELSE:
       # Normal mode: demand-based only
       IF demand <= 120: chosen_days = 4
       ELSE: chosen_days = 5
   ```

   **Do NOT add**: "if chosen days would create backlog, switch to catch-up mode". This violates the deterministic policy.

5. **Step-Down Logic**: When backlog clears, check demand against capacity thresholds. Skip intermediate steps (e.g., 5-day weeks) if demand is already low enough for 4-day capacity.
   - **Oscillation Handling**: If demand exceeds the stepped-down capacity, backlog will re-accumulate. Allow the schedule to step back up to 6 days if `calc_backlog > 0` or `demand > capacity`.

6. **Generate Outputs**:
   - Write plan to new Excel sheet with exact headers requested.
   - Write summary to `.txt` with exact formatting. Use `N/A` for non-applicable transition weeks.

7. **Verify**: Re-read output files to confirm row counts, headers, and data integrity before finishing.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Validation Checklist

Before submitting output, verify:
- [ ] Row count matches expected weeks (check for off-by-one: weeks 4-52 = 49 rows)
- [ ] Column order matches specification exactly
- [ ] Worksheet name is exactly as specified (case-sensitive)
- [ ] First occurrence tracking: record first week with 5 days, first with 4 days
- [ ] State carries correctly: `calc_end[n] == calc_start[n+1]` (mathematical, not reported)
- [ ] Reported start uses `max(0, calc_start)`
- [ ] No negative values where disallowed (e.g., reported_start = max(0, calc_start))

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Using text reader on `.xlsx` | Garbage data, wrong columns | Use `openpyxl.load_workbook(path, data_only=True)` |
| Adding "smart" backlog checks | Verifier rejects | Follow policy exactly; don't check if chosen days create backlog |
| Confusing calc_start vs reported_start | Wrong mode selection | Use reported_start for decisions, calc_start for math |
| Forcing backlog to exactly 0 | Verifier rejects | Treat `<= 0` as cleared, keep negative as buffer |
| Integer division | Capacity calculations wrong | Ensure `30 * days` not `30 / days` |
| Off-by-one in week range | Missing first or last week | Use `range(4, 53)` for weeks 4-52 inclusive |
| Column name drift | Verifier rejects | Copy column names exactly from spec |
| Sheet name case mismatch | Excel read fails | Match exact case from task prompt |

## Anti-Patterns

- **Do not** use generic file readers for `.xlsx`. Always use `openpyxl` or `pandas`.
- **Do not** assume backlog clears exactly at 0. It often goes slightly negative; treat `<= 0` as cleared.
- **Do not** add conditional logic to "fix" the policy. The policy is deterministic: reported_start threshold → mode → days choice.
- **Do not** skip verification. Always re-read output and check row counts, headers, week sequences.
- **Do not** write inline Python for backlog loop without consulting template script.

## Scripts

- `scripts/capacity_planner_template.py` - Template for iterative capacity/backlog planning. Adapt `CAPACITY_RULES` and decision thresholds to match task prompt before execution.
- `scripts/verify_plan.py` - Validate output structure: row counts, column headers, state-carry consistency.

## References

- `references/excel-patterns.md` - Common Excel data layouts and extraction patterns for production planning inputs.

## Known Invariants (by sub-task)

(No sub-task-specific invariants recorded yet. Update this section when verifier messages reveal task-specific rules.)