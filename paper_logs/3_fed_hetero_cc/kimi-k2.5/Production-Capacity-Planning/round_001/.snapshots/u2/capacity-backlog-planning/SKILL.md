---
name: capacity-backlog-planning
description: Create week-by-week production schedules with state-carry backlog calculations and threshold-driven scheduling decisions. Use when tasks require computing capacity, overtime, and backlog reduction across multiple periods (e.g., production catch-up plans, inventory recovery schedules, resource allocation over time).
---

# Capacity & Backlog Planning

Build week-by-week production schedules where days-worked decisions depend on current backlog state.

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

## Decision Rules for Days Worked

```
IF current_backlog > threshold:
    # Need to catch up - try minimal days that clear backlog
    FOR days IN [5, 6]:  # Try fewer days first
        IF current_backlog + demand - (daily_capacity * days) <= 0:
            days_worked = days
            BREAK
    ELSE:
        days_worked = 6  # Default if neither clears
ELSE:
    # No significant backlog - use demand-based schedule
    IF demand <= threshold: days_worked = 4
    ELSE: days_worked = 5
```

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
- [ ] State carries correctly: end_of_week[n] == start_of_week[n+1]
- [ ] No negative values where disallowed (e.g., reported_start = max(0, calc_start))

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Using text reader on `.xlsx` | Garbage data, wrong columns | Use `openpyxl.load_workbook(path, data_only=True)` |
| Backlog forced to exactly 0 | Verifier rejects | Treat `<= 0` as cleared, keep negative as buffer |
| Integer division | Capacity calculations wrong | Ensure `30 * days` not `30 / days` |
| Off-by-one in week range | Missing first or last week | Use `range(4, 53)` for weeks 4-52 inclusive |
| Column name drift | Verifier rejects | Copy column names exactly from spec |
| Sheet name case mismatch | Excel read fails | Match exact case from task prompt |

## Anti-Patterns

- **Do not** use generic file readers for `.xlsx`. Always use `openpyxl` or `pandas`.
- **Do not** assume backlog clears exactly at 0. It often goes slightly negative; treat `<= 0` as cleared.
- **Do not** skip verification. Always re-read output and check row counts, headers, week sequences.
- **Do not** write inline Python for backlog loop without consulting template script.

## Scripts

- `scripts/capacity_planner_template.py` - Template for iterative capacity/backlog planning. Adapt `CAPACITY_RULES` and decision thresholds to match task prompt before execution.
- `scripts/verify_plan.py` - Validate output structure: row counts, column headers, state-carry consistency.

## Known Invariants (by sub-task)

(No sub-task-specific invariants recorded yet. Update this section when verifier messages reveal task-specific rules.)