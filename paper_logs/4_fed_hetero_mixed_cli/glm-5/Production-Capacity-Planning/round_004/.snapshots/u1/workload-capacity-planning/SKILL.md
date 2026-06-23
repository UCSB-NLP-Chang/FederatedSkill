---
name: workload-capacity-planning
description: Simulates deterministic weekly (or period-based) capacity, backlog, and overtime policies from Excel input data. Generates structured Excel plans and strictly formatted summary text files. Use when tasks require week-by-week (or period-by-period) workload simulation, backlog burn-down calculations, catch-up plans, and output validation against strict formatting constraints. Trigger when you see Excel capacity data, weekly/period demand schedules, step-down plans, or phrases like 'catch-up plan', 'backlog clearance', 'overtime policy', 'days worked schedule'.
---

# Workload & Capacity Planning Simulation

## Quick Check: Excel Layout — Mandatory Inspection Step
**Never assume layout orientation.** Always run a quick inspection before parsing. Use `python3` (not `python`).
```python
import openpyxl
wb = openpyxl.load_workbook('input.xlsx', data_only=True)
ws = wb.active
print(f"Dimensions: {ws.dimensions}, MaxRow: {ws.max_row}, MaxCol: {ws.max_column}")
for r in range(1, min(4, ws.max_row+1)):
    print(f"Row {r}: {[ws.cell(row=r, column=c).value for c in range(1, min(4, ws.max_column+1))]}")
```
**Decision Rule**:
- If `max_column <= 3` and Row 1 contains labels like "Week", "Demand" → **Vertical Layout**. Parse with `ws.iter_rows(min_row=2, values_only=True)`.
- If `max_column > 10` and headers contain week numbers (e.g., `4, 5, 6...`) → **Horizontal Layout**. See `references/horizontal-data-parsing.md`.

## Workflow
1. **Extract Input Data**: Read the source Excel file. Identify sheet orientation (horizontal vs vertical). Parse week/period-to-demand mapping carefully.
2. **Resolve Initial State**: Carefully separate "Start of Week Past Due" from "Scheduled Demand" if the prompt provides a combined initial condition. Avoid double-counting demand in the first period's calculation.
   - Formula: `backlog = combined_value - first_period_demand`
3. **Define Policy Rules**: Map the deterministic decision tree:
   - Capacity per day (e.g., 25 or 30 std hrs/day)
   - Days-to-capacity mapping (e.g., 4 days = 100, 5 days = 125, 6 days = 150 for 25 hrs/day)
   - Backlog clearing logic (choose minimum days to drive `End of Period <= 0`)
   - Steady-state logic (if demand <= 4-day capacity, use 4 days; else if <= 5-day capacity, use 5 days, etc.)
   - Overtime calculation: typically `10 * max(0, days_worked - 4)`
4. **Run Simulation**: Iterate period-by-period. Track:
   - `prior_end`: Signed backlog/buffer from previous period
   - `sow_past_due`: `max(0, prior_end)` for reporting
   - `capacity`: Based on days selected by policy
   - `overtime`: Based on days worked
   - `end_of_period`: `sow_past_due + demand - capacity`
   
   Record first occurrences: first 4-day period, first 5-day period (track as `None` initially, assign period number when first triggered).
5. **Generate Excel Output**: Create workbook. Name sheet exactly as specified (e.g., `Plan`). Write headers and data rows. **Never round numeric values**—pass raw floats. Ensure period sequences are contiguous.
6. **Generate Summary Text**: Format strictly per task spec. Common pattern: 3 lines (First_Period_5_Days, First_Period_4_Days, Summary).
   - Use `N/A` for transitions never triggered
   - Summary: typically max 60 words, max 3 sentences
   - Must explicitly mention step-down period numbers or `N/A`
7. **Verify Programmatically**: Run assertions before submitting. See `references/validation-checklist.md`.

## Step-Down Logic for Catch-Up Plans

When starting with a backlog that must be cleared:

1. **Backlog Phase**: Use maximum days (typically 6) until `end_of_period <= 0`
2. **Transition Detection**: First period where backlog clears → may use 5 days if demand allows
3. **Steady-State Phase**: After backlog clears, use minimum days to meet demand:
   - If `demand <= 4_day_capacity`: use 4 days
   - If `4_day_capacity < demand <= 5_day_capacity`: use 5 days
   - If `demand > 5_day_capacity`: use 6 days

```python
# Example step-down logic
if backlog > 0:
    days = 6  # Maximum capacity to clear backlog
elif demand <= four_day_capacity:
    days = 4
elif demand <= five_day_capacity:
    days = 5
else:
    days = 6
```

Track `first_5_day_period` and `first_4_day_period` as state variables, set once when first encountered.

## Critical Decision Rules
- **Excel Orientation**: If you see week/period numbers in column headers rather than row values, use column-based parsing. See `references/horizontal-data-parsing.md`.
- **Initial Condition Parsing**: If given combined initial value, subtract first period's demand to avoid double-counting.
- **State Tracking**: Use `max(0, prior_end)` for reporting `Start of Period Past Due`, but keep signed `prior_end` for actual backlog/buffer calculations. Negative values indicate buffer (ahead of schedule).
- **N/A Handling**: If a policy state is never triggered, explicitly output `N/A` in both tracking variables and summary text.
- **Summary Constraints**: Count words and sentences programmatically. Ensure summary explicitly mentions step-down period numbers.

## Output Precision
Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly.
- **DO NOT**: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- **DO**: `ws.cell(row=r, column=c, value=x)` with x as a raw float

## Verification
Always validate before submitting. See `references/validation-checklist.md` for reusable assertion templates.

## Anti-Patterns
- **Do not** assume vertical/table layout for Excel input. Always run the layout inspection first.
- **Do not** assume initial condition is purely backlog; verify if it includes scheduled demand.
- **Do not** use string formatting on numeric outputs (no rounding).
- **Do not** hardcode summary text; generate dynamically from tracked variables.
- **Do not** skip verification; formatting constraints are strict and easily violated.
- **Do not** use `python` command; always use `python3`.

## Known invariants

- Initial condition statements often combine "Start of Week Past Due" with "Scheduled Demand" — parse carefully to avoid double-counting.
- Summary text must be generated dynamically from tracked variables; hardcoded text goes stale.
- Word/sentence count constraints are strict and easily violated by minor phrasing changes.
- Horizontal Excel layouts (periods as columns) require column-wise iteration instead of row-wise.
- Capacity values (hrs/day) are task-specific; do not hardcode 25 or 30 — read from task description.
