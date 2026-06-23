---
name: excel-capacity-planning
description: Handles tasks requiring reading Excel demand/capacity data, computing iterative weekly or period-based backlogs or catch-up schedules, and generating Excel plans with text summaries. Use when given spreadsheet data for production scheduling, inventory catch-up, or resource allocation over time. Trigger phrases include "catch-up plan", "capacity planning", "backlog reduction", "step down to X days", "overtime schedule", "glass furnace", "HVAC", "initial backlog", "phase".
---

# Excel Capacity & Backlog Planning

Build period-by-period production schedules where days-worked decisions depend on current backlog state.

## Core Concepts

- **Calc Start**: The mathematical backlog carried from previous period (can be negative = buffer)
- **Reported Start**: `max(0, calc_start)` - displayed as 0 when backlog is cleared
- **Decision Mode**: Determined by `reported_start > threshold` (typically 0.01), NOT by whether the chosen days would create new backlog
- **Period vs Week vs Phase**: Tasks may use "periods" (1-52), "weeks" (4-52), or "phases" (8-56). The logic is identical; only the labeling differs.

## Environment Setup

If pandas/openpyxl are not available:
```bash
pip install --break-system-packages pandas openpyxl -q
```

## Workflow

1. **Read Excel Data**: Use `openpyxl` or `pandas` in Python. Never use text-based `Read` tools on `.xlsx` files.
   ```python
   import pandas as pd
   df = pd.read_excel('input.xlsx', sheet_name='SheetName')
   ```

   For row-based data (labels in column A, period data in columns 1-N), see `references/excel-patterns.md`.

2. **Handle Duplicate Periods**: Check for duplicate phase/week numbers in input data. If found, aggregate demands by summing:
   ```python
   # Check for duplicates
   duplicates = df[df.duplicated(subset=['Phase'], keep=False)]
   if not duplicates.empty:
       df = df.groupby('Phase', as_index=False).agg({'Demand': 'sum'})
   ```

3. **Extract Capacity Rules from Task**: Do not assume generic values. Common variants:
   | Days | Std Hrs | OT Hrs | Total | Pattern |
   |------|---------|--------|-------|---------|
   | 6 | 160 | 20 | 180 | 160+20 OT |
   | 6 | 150 | 20 | 170 | 30*days + 20 |
   | 6 | 132 | 20 | 152 | 22*days + 20 |
   | 6 | 112 | 20 | 132 | 22*days + 20 |
   | 5 | 140 | 10 | 150 | 140+10 OT |
   | 5 | 125 | 10 | 135 | 25*days + 10 |
   | 5 | 110 | 10 | 120 | 22*days - 0 |
   | 4 | 120 | 0 | 120 | 30*days |
   | 4 | 100 | 0 | 100 | 25*days |
   | 4 | 88 | 0 | 88 | 22*days |
   | 4 | 80 | 0 | 80 | 20*days |

   **OT Formula Patterns**:
   - `OT = 10 * (days - 4)` for days > 4 (glass furnace, HVAC)
   - `OT = 20` for 6-day only (assembly)
   - `OT = 0` for 4-day always

   **Critical**: Derive the hourly rate from context. Common rates: 30 hrs/day, 25 hrs/day (5-day week basis), 22 hrs/day (glass furnace tasks), 20 hrs/day (assembly tasks). Capacity rules vary significantly between tasks.

4. **Determine Initial Backlog**: Two common patterns:
   - **Direct**: Given as "initial backlog = X hours"
   - **Derived**: Given as "initial condition = Y" where Y = backlog + week_1_demand, so `backlog = Y - week_1_demand`

5. **Iterative Calculation**: Loop through periods, updating backlog:
   - `calc_start[n+1] = calc_end[n]` (carry the mathematical value, including negatives)
   - `reported_start = max(0, calc_start)`
   - `calc_end = calc_start + demand - capacity`

   **Critical**: Treat `calc_end <= 0` as cleared. Do not force it to exactly 0.

6. **Apply Deterministic Policy** (follow exactly, do not add "smart" checks):
   ```
   IF reported_start > threshold (typically 0.01):
       # Catch-up mode: try 5 days first, then 6
       FOR days IN [5, 6]:
           IF calc_start + demand - capacity(days) <= 0:
               chosen_days = days; BREAK
       ELSE:
           chosen_days = 6
   ELSE:
       # Normal mode: demand-based only
       IF demand <= threshold_capacity: chosen_days = 4
       ELSE: chosen_days = 5
   ```

   **Do NOT add**: "if chosen days would create backlog, switch to catch-up mode". This violates the deterministic policy.

7. **Step-Down Logic**: When backlog clears, check demand against capacity thresholds. Skip intermediate steps if demand is already low enough for fewer days.
   - **Oscillation Handling**: If demand exceeds the stepped-down capacity, backlog will re-accumulate. Allow the schedule to step back up if `calc_backlog > 0` or `demand > capacity`.

8. **Generate Outputs**:
   - Write plan to new Excel sheet with exact headers requested.
   - Write summary to `.txt` with exact formatting. Use `N/A` for non-applicable transition periods.
   - **Check length constraints**: If the prompt specifies max words or sentences for the summary, enforce them before writing.

9. **Verify**: Re-read output files to confirm row counts, headers, and data integrity before finishing. See verification patterns below.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Verification Patterns

Before submitting output, verify programmatically:

```python
import pandas as pd
df = pd.read_excel('output.xlsx', sheet_name='Plan')

# 1. Check all periods present in sequence
expected_phases = list(range(start_phase, end_phase + 1))
actual_phases = df['Phase'].tolist()
assert actual_phases == expected_phases, f"Phase mismatch"

# 2. Check state carries correctly (calc_end[n] == calc_start[n+1])
for i in range(len(df) - 1):
    end_backlog = df.iloc[i]['End of Phase Backlog/Buffer (Std Hrs)']
    next_start = df.iloc[i+1]['Start of Phase Past Due (Std Hrs)']
    if end_backlog > 0:
        assert abs(end_backlog - next_start) < 0.01, f"State mismatch at {i}"
    else:
        assert next_start == 0, f"Reported start should be 0 when backlog cleared"

# 3. Check days worked in valid range
assert set(df['Days Worked'].unique()).issubset({4, 5, 6})

# 4. Check OT formula matches days worked
for _, row in df.iterrows():
    days = row['Days Worked']
    ot = row['Overtime Hours']
    expected_ot = 10 * (days - 4) if days > 4 else 0  # Adjust formula per task
    assert ot == expected_ot, f"OT mismatch"
```

## Validation Checklist

Before submitting output, verify:
- [ ] Row count matches expected periods (check for off-by-one)
- [ ] Duplicate periods aggregated (sum demands for same phase/week)
- [ ] Column order matches specification exactly
- [ ] Worksheet name is exactly as specified (case-sensitive)
- [ ] First occurrence tracking: record first period with 5 days, first with 4 days
- [ ] State carries correctly: `calc_end[n] == calc_start[n+1]` (mathematical, not reported)
- [ ] Reported start uses `max(0, calc_start)`
- [ ] No negative values where disallowed (e.g., reported_start = max(0, calc_start))
- [ ] Capacity values match task specification exactly (not generic assumptions)
- [ ] Initial backlog calculated correctly (direct vs derived pattern)
- [ ] Summary meets explicit word/sentence limits if specified in prompt

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Using text reader on `.xlsx` | Garbage data, wrong columns | Use `openpyxl.load_workbook(path, data_only=True)` or `pd.read_excel()` |
| Missing pandas | ImportError | Use `--break-system-packages` flag |
| Adding "smart" backlog checks | Verifier rejects | Follow policy exactly; don't check if chosen days create backlog |
| Confusing calc_start vs reported_start | Wrong mode selection | Use reported_start for decisions, calc_start for math |
| Forcing backlog to exactly 0 | Verifier rejects | Treat `<= 0` as cleared, keep negative as buffer |
| Integer division | Capacity calculations wrong | Ensure `22 * days` not `22 / days` |
| Off-by-one in period range | Missing first or last period | Verify range boundaries match task |
| Column name drift | Verifier rejects | Copy column names exactly from spec |
| Sheet name case mismatch | Excel read fails | Match exact case from task prompt |
| Assuming generic capacity rules | Wrong totals, verifier rejects | Extract exact std/OT values and hourly rate from task prompt |
| Wrong initial backlog | First period calculations off | Check if backlog is given directly or derived from "initial condition" |
| Duplicate periods not aggregated | Wrong demand totals | Check for duplicates with `df.duplicated()`, sum demands by period |

## Anti-Patterns

- **Do not** use generic file readers for `.xlsx`. Always use `openpyxl` or `pandas`.
- **Do not** assume backlog clears exactly at 0. It often goes slightly negative; treat `<= 0` as cleared.
- **Do not** add conditional logic to "fix" the policy. The policy is deterministic: reported_start threshold → mode → days choice.
- **Do not** skip verification. Always re-read output and check row counts, headers, period sequences.
- **Do not** write inline Python for backlog loop without consulting template script.
- **Do not** assume capacity rules. Tasks vary: 6-day capacity might be 120, 132, 150, 170, or 180 depending on hourly rate and OT rules.
- **Do not** assume initial backlog is given directly. Check for "initial condition" phrasing that requires derivation.
- **Do not** ignore duplicate periods. Aggregate demands before processing.

## Scripts

- `scripts/capacity_planner_template.py` - Template for iterative capacity/backlog planning. Adapt `CAPACITY_RULES`, `HOURLY_RATE`, and decision thresholds to match task prompt before execution.
- `scripts/verify_plan.py` - Validate output structure: row counts, column headers, state-carry consistency.

## References

- `references/excel-patterns.md` - Common Excel data layouts and extraction patterns for production planning inputs.

## Known Invariants (by sub-task)

- **Glass furnace tasks**: 22 hrs/day production rate, OT = 10*(days-4), threshold 0.01, demand threshold for 4-day = 110
- **HVAC/Ductwork tasks**: 35 hrs/day production rate, OT = 10*(days-4), capacity: 6-day=210, 5-day=175, 4-day=140
- **PCB assembly tasks**: 20 hrs/day production rate, OT = 10*(days-4), capacity: 6-day=120, 5-day=100, 4-day=80
- **Derived initial backlog**: When given "initial condition = X" and week 2 demand, calculate `backlog = X - demand`