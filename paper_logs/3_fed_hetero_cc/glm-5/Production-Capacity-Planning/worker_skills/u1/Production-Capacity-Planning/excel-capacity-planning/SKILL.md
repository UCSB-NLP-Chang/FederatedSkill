---
name: excel-capacity-planning
description: Handles tasks requiring reading Excel, CSV, or JSON demand/capacity data, computing iterative weekly or period-based backlogs or catch-up schedules, and generating Excel plans with text summaries. Use when given spreadsheet, CSV, or JSON data for production scheduling, inventory catch-up, resource allocation over time, HVAC/ductwork scheduling, ship block construction planning, or chemical production scheduling. Trigger phrases include "catch-up plan", "capacity planning", "backlog reduction", "step down to X days", "overtime schedule", "glass furnace", "initial backlog", "PCB assembly", "phases", "HVAC ductwork", "demand adjustment", "dye catch-up", "ship block", "ship construction", "initial condition", "chemical schedule".
---

# Excel, CSV & JSON Capacity & Backlog Planning

Build period-by-period production schedules where days-worked decisions depend on current backlog state.

## Critical First Step: Read the Task Prompt Completely

Before writing any code, extract these exact values from the task prompt:

| Value | Where to Find | Example Formats |
|-------|---------------|-----------------|
| Hourly production rate | "X hours per day", "X hrs/day" | 18, 20, 22, 25, 28, 30, 35, 40 |
| Capacity per days-worked | Table or bullet list | "5-day week: 100 hours" |
| Overtime formula | "OT = ", "overtime" | "10*(days-4)", "fixed 20 hrs", "2*(days-4)" |
| Threshold for 4-day | "demand <= X" | 72, 80, 88, 100, 110, 112 (28*4), 160 |
| Initial backlog | "initial backlog", "initial condition" | Direct value or derived |
| Period range | "weeks X to Y", "phases X-Y" | 3-51, 8-56, 4-52, 5-53, 10-58 |

**Do NOT assume capacity rules.** The values vary significantly between tasks. Always derive from the specific prompt.

## Core Concepts

- **Calc Start**: The mathematical backlog carried from previous period (can be negative = buffer)
- **Reported Start**: `max(0, calc_start)` - displayed as 0 when backlog is cleared
- **Decision Mode**: Determined by `reported_start > threshold` (typically 0.01), NOT by whether the chosen days would create new backlog
- **Period vs Week vs Phase**: Tasks may use "periods" (1-52), "weeks" (4-52), or "phases" (6-54, 10-58). The logic is identical; only the labeling differs.

## Environment Setup

If pandas/openpyxl are not available:
```bash
pip install --break-system-packages pandas openpyxl -q
```

**Always use `python3`**, not `python`, as many environments only have `python3` available.

## Input File Handling

### Excel Files (.xlsx)
Use `openpyxl` or `pandas`. Never use text-based `Read` tools.
```python
import pandas as pd
df = pd.read_excel('input.xlsx', sheet_name='SheetName')
```

### CSV Files (.csv)
Use standard `csv` module or `pandas.read_csv()`. CSV files are acceptable for simple demand data.
```python
import csv
with open('input.csv', 'r') as f:
    reader = csv.reader(f)
    headers = next(reader)
    demand_row = next(reader)
```

### JSON Files (.json)
Use the `json` module. JSON inputs may contain duplicate week/phase entries.
```python
import json
with open('input.json', 'r') as f:
    raw = json.load(f)
```

**JSON Deduplication**: Use first valid (non-null) occurrence:
```python
demand_map = {}
for entry in raw:
    w = entry['week']
    d = entry['data']['demand_per_week']
    if w not in demand_map and d is not None:
        demand_map[w] = d
```

For row-based data (labels in column A, period data in columns 1-N), see `references/excel-patterns.md`.

**Multi-Sheet Combination**: When demand is split across sheets (e.g., base demand + adjustments), load both and combine:
```python
base_df = pd.read_excel('input.xlsx', sheet_name='Dye')
adj_df = pd.read_excel('input.xlsx', sheet_name='Adjust')
base_df['Total Demand'] = base_df['Dye Demand (Std Hrs)'] + adj_df['Demand Adjustment (Std Hrs)']
```

## Workflow

1. **Read Task Prompt First**: Extract exact capacity rules, hourly rate, overtime formula, and thresholds before touching code.

2. **Read Input Data**: Use appropriate reader for file type (Excel, CSV, or JSON). Handle duplicate entries using first occurrence only:
   ```python
   df = df.drop_duplicates(subset=['Phase'], keep='first')
   period_col = 'Week' if 'Week' in df.columns else 'Phase'
   df = df.drop_duplicates(subset=[period_col], keep='first')
   ```

3. **Extract Capacity Rules from Task Prompt**: Do not assume generic values. Common variants:
   | Days | Std Hrs | OT Hrs | Total | Hourly Rate | Pattern |
   |------|---------|--------|-------|-------------|---------|
   | 6 | 168 | 20 | 168 | 28 | 28*days, OT separate (ship block) |
   | 6 | 150 | 20 | 170 | 25 | 25*days + 20 |
   | 6 | 132 | 20 | 132 | 22 | 22*days, OT separate (glass furnace) |
   | 6 | 120 | 20 | 120 | 20 | 20*days, OT separate (PCB assembly) |
   | 6 | 210 | 0 | 210 | 35 | 35*days (HVAC) |
   | 6 | 96 | 12 | 108 | 18 | 18*days, OT=2*(days-4) (dye) |
   | 6 | 220 | 20 | 240 | 40 | 40*days, OT=10*(days-4) (chemical) |
   | 5 | 140 | 10 | 140 | 28 | 28*days, OT separate (ship block) |
   | 5 | 125 | 10 | 135 | 25 | 25*days + 10 |
   | 5 | 110 | 10 | 110 | 22 | 22*days, OT separate (glass furnace) |
   | 5 | 100 | 10 | 100 | 20 | 20*days, OT separate (PCB assembly) |
   | 5 | 175 | 0 | 175 | 35 | 35*days (HVAC) |
   | 5 | 80 | 10 | 90 | 18 | 18*days, OT=2*(days-4) (dye) |
   | 5 | 190 | 10 | 200 | 40 | 40*days, OT=10*(days-4) (chemical) |
   | 4 | 112 | 0 | 112 | 28 | 28*days (ship block) |
   | 4 | 100 | 0 | 100 | 25 | 25*days |
   | 4 | 88 | 0 | 88 | 22 | 22*days (glass furnace) |
   | 4 | 80 | 0 | 80 | 20 | 20*days (PCB assembly) |
   | 4 | 140 | 0 | 140 | 35 | 35*days (HVAC) |
   | 4 | 72 | 0 | 72 | 18 | 18*days (dye) |
   | 4 | 160 | 0 | 160 | 40 | 40*days (chemical) |

   **CRITICAL**: The "Total" column is the capacity used for backlog calculation. Verify from task whether OT is included or tracked separately.

   **Overtime formula**: Often `OT = 10 * (days - 4)` for PCB assembly, HVAC, ship block, and chemical tasks, or `OT = 2 * (days - 4)` for dye tasks. Verify against task prompt.

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

8. **Debug Transition Weeks**: Before finalizing, print intermediate values around expected step-down weeks to verify logic:
   ```python
   for i in range(transition_week - 3, transition_week + 3):
       print(f"Wk {i}: past_due={calc_start:.2f} demand={demand:.2f} days={days} cap={cap} eow={calc_end:.2f}")
   ```
   This catches off-by-one errors in step-down timing.

9. **Generate Outputs**:
   - Write plan to new Excel sheet with exact headers requested.
   - Write summary to `.txt` with exact formatting. Use `N/A` for non-applicable transition periods.
   - **Check length constraints**: If prompt specifies max words/sentences, enforce programmatically before writing.
   - **Sentence counting pitfall**: Decimal points (e.g., "645.11") miscount as sentence boundaries. Round to integers in summary or use robust splitter.

10. **Verify**: Re-read output files to confirm row counts, headers, and data integrity. Run verification code:
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
    ```

## Output Precision

**CRITICAL**: Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

**Common violation**: Agents often round backlog values to 2 decimal places before writing to Excel. This causes verifier failures. Write raw floats only.

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
- [ ] Multi-sheet demand combined correctly if input has separate adjustment sheet
- [ ] **No rounding applied to numeric output values**

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Assuming capacity = rate × days | Verifier rejects | Use exact totals from task prompt table |
| Not reading task prompt first | Wrong capacity values | Extract rules before coding |
| Using text reader on `.xlsx` | Garbage data, wrong columns | Use `openpyxl.load_workbook(path, data_only=True)` or `pd.read_excel()` |
| Missing pandas | ImportError | Use `--break-system-packages` flag |
| Using `python` instead of `python3` | Command not found | Always use `python3` |
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
| Sentence count off by 1 | Summary rejected | Decimal points in numbers count as sentence boundaries in naive regex |
| Rounding output values | Verifier rejects due to precision mismatch | Write raw floats only; never use `round()`, `format()`, or f-string formatting |

## Anti-Patterns

- **Do not** assume capacity rules. Always extract from the task prompt.
- **Do not** use generic file readers for `.xlsx`. Always use `openpyxl` or `pandas`.
- **Do not** assume backlog clears exactly at 0. It often goes slightly negative; treat `<= 0` as cleared.
- **Do not** add conditional logic to "fix" the policy. The policy is deterministic.
- **Do not** skip verification. Always re-read output and check row counts, headers, period sequences.
- **Do not** write inline Python for backlog loop without consulting template script.
- **Do not** assume initial backlog is given directly. Check for "initial condition" phrasing.
- **Do not** ignore duplicate entries. Always check for and handle duplicate phase/week rows.
- **Do not** ignore secondary sheets. Check for "Adjust", "Adjustment" sheets that modify base demand.
- **Do not** use naive sentence counting on text containing decimal numbers.
- **Do not** round numeric values before writing to Excel. Write raw floats only.

## Scripts

- `scripts/capacity_planner_template.py` - Template for iterative capacity/backlog planning. Adapt `CAPACITY_RULES`, `HOURLY_RATE`, and decision thresholds to match task prompt before execution.
- `scripts/verify_plan.py` - Validate output structure: row counts, column headers, state-carry consistency.

## References

- `references/excel-patterns.md` - Common Excel data layouts and extraction patterns for production planning inputs, including multi-sheet combination.

## Known Invariants (by sub-task)

- **Glass furnace tasks**: 22 hrs/day production rate, OT = 10*(days-4), threshold 0.01, demand threshold for 4-day = 110
- **PCB assembly tasks**: 20 hrs/day production rate, OT = 10*(days-4), capacity: 6-day=120, 5-day=100, 4-day=80
- **HVAC/Ductwork tasks**: 35 hrs/day production rate, OT = 10*(days-4), capacity: 6-day=210, 5-day=175, 4-day=140
- **Dye catch-up tasks**: 18 hrs/day production rate, OT = 2*(days-4), capacity: 6-day=108, 5-day=90, 4-day=72
- **Ship block tasks**: 28 hrs/day production rate, OT = 10*(days-4), capacity: 6-day=168, 5-day=140, 4-day=112 (OT tracked separately)
- **Chemical production tasks**: 40 hrs/day production rate, OT = 10*(days-4), capacity: 6-day=240, 5-day=200, 4-day=160, demand threshold for 4-day = 160
- **Derived initial backlog**: When given "initial condition = X" and week 1 demand, calculate `backlog = X - demand`