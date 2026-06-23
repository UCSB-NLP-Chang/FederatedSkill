---
name: excel-capacity-planning
description: Handles tasks requiring reading Excel demand/capacity data, computing iterative weekly or period-based backlogs or catch-up schedules, and generating Excel plans with text summaries. Use when given spreadsheet data for production scheduling, inventory catch-up, resource allocation over time, or HVAC/ductwork scheduling. Trigger phrases include "catch-up plan", "capacity planning", "backlog reduction", "step down to X days", "overtime schedule", "glass furnace", "initial backlog", "PCB assembly", "phases", "HVAC ductwork", "demand adjustment", "dye catch-up".
---

# Excel Capacity & Backlog Planning

Build period-by-period production schedules where days-worked decisions depend on current backlog state.

## Critical First Step: Read the Task Prompt Completely

Before writing any code, extract these exact values from the task prompt:

| Value | Where to Find | Example Formats |
|-------|---------------|-----------------|
| Hourly production rate | "X hours per day", "X hrs/day" | 18, 20, 22, 25, 30, 35 |
| Capacity per days-worked | Table or bullet list | "5-day week: 100 hours" |
| Overtime formula | "OT = ", "overtime" | "10*(days-4)", "fixed 20 hrs", "2*(days-4)" |
| Threshold for 4-day | "demand <= X" | 72, 80, 88, 100, 110, 120 |
| Initial backlog | "initial backlog", "initial condition" | Direct value or derived |
| Period range | "weeks X to Y", "phases X-Y" | 3-51, 8-56, 4-52 |

**Do NOT assume capacity rules.** The values vary significantly between tasks. Always derive from the specific prompt. See `references/capacity-derivation.md` for extraction methodology.

## Core Concepts

- **Calc Start**: The mathematical backlog carried from previous period (can be negative = buffer)
- **Reported Start**: `max(0, calc_start)` - displayed as 0 when backlog is cleared
- **Decision Mode**: Determined by `reported_start > threshold` (typically 0.01), NOT by whether the chosen days would create new backlog
- **Period vs Week vs Phase**: Tasks may use "periods" (1-52), "weeks" (4-52), or "phases" (6-54). The logic is identical; only the labeling differs.

## Environment Setup

If pandas/openpyxl are not available:
```bash
pip install --break-system-packages pandas openpyxl -q
```

## Workflow

1. **Read Task Prompt First**: Extract exact capacity rules, hourly rate, overtime formula, and thresholds before touching code.

2. **Read Excel Data**: Use `openpyxl` or `pandas` in Python. Never use text-based `Read` tools on `.xlsx` files.
   ```python
   import pandas as pd
   df = pd.read_excel('input.xlsx', sheet_name='SheetName')
   ```

   For row-based data (labels in column A, period data in columns 1-N), see `references/excel-patterns.md`.

   **Multi-Sheet Combination**: When demand is split across sheets (e.g., base demand + adjustments), load both and combine:
   ```python
   base_df = pd.read_excel('input.xlsx', sheet_name='Dye')
   adj_df = pd.read_excel('input.xlsx', sheet_name='Adjust')
   # Assuming same week structure, add adjustment column to base demand
   base_df['Total Demand'] = base_df['Dye Demand (Std Hrs)'] + adj_df['Demand Adjustment (Std Hrs)']
   ```

3. **Handle Duplicate Entries**: Input data may contain duplicate phase/week rows. Use **first occurrence only**:
   ```python
   df = df.drop_duplicates(subset=['Phase'], keep='first')
   # or for generic period column:
   period_col = 'Week' if 'Week' in df.columns else 'Phase'
   df = df.drop_duplicates(subset=[period_col], keep='first')
   ```

4. **Extract Capacity Rules from Task Prompt**: This is the most common failure source. Common variants:
   | Days | Std Hrs | OT Hrs | Total | Hourly Rate | Pattern |
   |------|---------|--------|-------|-------------|---------|
   | 6 | 150 | 20 | 170 | 25 | 25*days + 20 |
   | 6 | 132 | 20 | 152 | 22 | 22*days + 20 (glass) |
   | 6 | 120 | 20 | 140 | 20 | 20*days + 20 (PCB) |
   | 6 | 180 | 20 | 200 | 30 | 30*days + 20 |
   | 6 | 210 | 0 | 210 | 35 | 35*days (HVAC) |
   | 6 | 96 | 12 | 108 | 18 | 18*days, OT=2*(days-4) (dye) |
   | 5 | 125 | 10 | 135 | 25 | 25*days + 10 |
   | 5 | 110 | 10 | 120 | 22 | 22*days + 10 (glass) |
   | 5 | 100 | 10 | 110 | 20 | 20*days + 10 (PCB) |
   | 5 | 150 | 0 | 150 | 30 | 30*days |
   | 5 | 175 | 0 | 175 | 35 | 35*days (HVAC) |
   | 5 | 80 | 10 | 90 | 18 | 18*days, OT=2*(days-4) (dye) |
   | 4 | 100 | 0 | 100 | 25 | 25*days |
   | 4 | 88 | 0 | 88 | 22 | 22*days (glass) |
   | 4 | 80 | 0 | 80 | 20 | 20*days (PCB) |
   | 4 | 120 | 0 | 120 | 30 | 30*days |
   | 4 | 140 | 0 | 140 | 35 | 35*days (HVAC) |
   | 4 | 72 | 0 | 72 | 18 | 18*days (dye) |

   **CRITICAL**: The "Total" column in the task is what matters for capacity calculations. Do not recalculate as `rate * days` unless the task explicitly states this formula.

   **Overtime formula**: Often `OT = 10 * (days - 4)` for PCB assembly and HVAC tasks, or `OT = 2 * (days - 4)` for dye tasks. Verify against task prompt.

5. **Determine Initial Backlog**: Two common patterns:
   - **Direct**: Given as "initial backlog = X hours"
   - **Derived**: Given as "initial condition = Y" where Y = backlog + week_1_demand, so `backlog = Y - week_1_demand`

6. **Iterative Calculation**: Loop through periods, updating backlog:
   - `calc_start[n+1] = calc_end[n]` (carry the mathematical value, including negatives)
   - `reported_start = max(0, calc_start)`
   - `calc_end = calc_start + demand - capacity`

   **Critical**: Treat `calc_end <= 0` as cleared. Do not force it to exactly 0.

7. **Apply Deterministic Policy** (follow exactly, do not add "smart" checks):
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

   **Do NOT add**: "if chosen days would create backlog, switch to catch-up mode". This violates the deterministic policy. See `references/deterministic-policy.md`.

8. **Step-Down Logic**: When backlog clears, check demand against capacity thresholds. Skip intermediate steps if demand is already low enough for fewer days.
   - **Oscillation Handling**: If demand exceeds the stepped-down capacity, backlog will re-accumulate. Allow the schedule to step back up if `calc_backlog > 0` or `demand > capacity`.

9. **Generate Outputs**:
   - Write plan to new Excel sheet with exact headers requested.
   - Write summary to `.txt` with exact formatting. Use `N/A` for non-applicable transition periods.
   - **Summary format for catch-up plans**: Often requires lines like:
     ```
     First_Week_5_Days: <week_num or N/A>
     First_Week_4_Days: <week_num or N/A>
     Summary: <text within word/sentence limits>
     ```
   - **Check length constraints**: If the prompt specifies max words or sentences for the summary, enforce them programmatically before writing.
   - **Sentence counting pitfall**: Decimal points in numbers (e.g., "645.11") can be miscounted as sentence boundaries by naive regex. Round to integers in summary text or use a sentence counter that ignores decimal points.

10. **Verify**: Re-read output files to confirm row counts, headers, and data integrity before finishing. Run `scripts/verify_plan.py` if available. See verification patterns below.

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
    expected_ot = OT_FORMULA(days)  # Adjust formula per task
    assert ot == expected_ot, f"OT mismatch"
```

## Validation Checklist

Before submitting output, verify:
- [ ] Capacity rules extracted from task prompt, not assumed
- [ ] Hourly rate verified from task (not defaulting to common value)
- [ ] Overtime formula matches task specification
- [ ] Row count matches expected periods (check for off-by-one)
- [ ] Column order matches specification exactly
- [ ] Worksheet name is exactly as specified (case-sensitive)
- [ ] Duplicate entries handled (first occurrence kept)
- [ ] First occurrence tracking: record first period with 5 days, first with 4 days
- [ ] State carries correctly: `calc_end[n] == calc_start[n+1]` (mathematical, not reported)
- [ ] Reported start uses `max(0, calc_start)`
- [ ] No negative values where disallowed (e.g., reported_start = max(0, calc_start))
- [ ] Capacity values match task specification exactly (not generic assumptions)
- [ ] Initial backlog calculated correctly (direct vs derived pattern)
- [ ] Summary meets explicit word/sentence limits if specified in prompt
- [ ] Summary format matches expected structure (First_Week_X_Days lines if required)
- [ ] Multi-sheet demand combined correctly if input has separate adjustment sheet

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Assuming capacity = rate × days | Verifier rejects | Use exact totals from task prompt table |
| Not reading task prompt first | Wrong capacity values | Extract rules before coding |
| Using text reader on `.xlsx` | Garbage data, wrong columns | Use `openpyxl.load_workbook(path, data_only=True)` or `pd.read_excel()` |
| Missing pandas | ImportError | Use `--break-system-packages` flag |
| Duplicate phase/week entries | Wrong row count, inflated totals | Use `drop_duplicates(keep='first')` |
| Adding "smart" backlog checks | Verifier rejects | Follow policy exactly; don't check if chosen days create backlog |
| Confusing calc_start vs reported_start | Wrong mode selection | Use reported_start for decisions, calc_start for math |
| Forcing backlog to exactly 0 | Verifier rejects | Treat `<= 0` as cleared, keep negative as buffer |
| Integer division | Capacity calculations wrong | Ensure `22 * days` not `22 / days` |
| Off-by-one in period range | Missing first or last period | Verify range boundaries match task |
| Column name drift | Verifier rejects | Copy column names exactly from spec |
| Sheet name case mismatch | Excel read fails | Match exact case from task prompt |
| Wrong initial backlog | First period calculations off | Check if backlog is given directly or derived from "initial condition" |
| Ignoring adjustment sheet | Demand values wrong | Check for secondary sheets with demand adjustments and combine |
| Sentence count off by 1 | Summary rejected | Decimal points in numbers count as sentence boundaries in naive regex; round numbers in summary or use robust sentence splitter |

## Anti-Patterns

- **Do not** assume capacity rules. Always extract from the task prompt.
- **Do not** use generic file readers for `.xlsx`. Always use `openpyxl` or `pandas`.
- **Do not** assume backlog clears exactly at 0. It often goes slightly negative; treat `<= 0` as cleared.
- **Do not** add conditional logic to "fix" the policy. The policy is deterministic: reported_start threshold → mode → days choice.
- **Do not** skip verification. Always re-read output and check row counts, headers, period sequences.
- **Do not** write inline Python for backlog loop without consulting template script.
- **Do not** assume initial backlog is given directly. Check for "initial condition" phrasing that requires derivation.
- **Do not** ignore duplicate entries. Always check for and handle duplicate phase/week rows using first occurrence.
- **Do not** ignore secondary sheets. Check for "Adjust", "Adjustment", or similar sheets that modify base demand.
- **Do not** use naive sentence counting on text containing decimal numbers. Round to integers in summaries or use a sentence splitter that ignores decimal points.

## Scripts

- `scripts/capacity_planner_template.py` - Template for iterative capacity/backlog planning. **Must adapt `CAPACITY_RULES`, `HOURLY_RATE`, and decision thresholds to match task prompt before execution.**
- `scripts/verify_plan.py` - Validate output structure: row counts, column headers, state-carry consistency.

## References

- `references/excel-patterns.md` - Common Excel data layouts and extraction patterns for production planning inputs, including multi-sheet combination.
- `references/deterministic-policy.md` - Exact policy implementation with examples of correct vs incorrect approaches.
- `references/capacity-derivation.md` - How to extract and verify capacity rules from task prompts.

## Known Invariants (by sub-task)

These are **examples only** - always verify against your specific task:

- **Glass furnace tasks**: 22 hrs/day production rate, OT = 10*(days-4), threshold 0.01, demand threshold for 4-day = 110
- **PCB assembly tasks**: 20 hrs/day production rate, OT = 10*(days-4), capacity: 6-day=120, 5-day=100, 4-day=80
- **HVAC/Ductwork tasks**: 35 hrs/day production rate, OT = 10*(days-4), capacity: 6-day=210, 5-day=175, 4-day=140
- **Dye catch-up tasks**: 18 hrs/day production rate, OT = 2*(days-4), capacity: 6-day=108, 5-day=90, 4-day=72
- **Derived initial backlog**: When given "initial condition = X" and week 2 demand, calculate `backlog = X - demand`