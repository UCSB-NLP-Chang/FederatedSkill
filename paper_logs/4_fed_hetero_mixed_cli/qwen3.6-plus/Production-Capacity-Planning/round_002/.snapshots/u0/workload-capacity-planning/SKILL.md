---
name: workload-capacity-planning
description: Simulates deterministic weekly capacity, backlog, and overtime policies from Excel input data. Generates structured Excel plans and strictly formatted summary text files. Use when tasks require week-by-week workload simulation, backlog burn-down calculations, and output validation against strict formatting constraints. Trigger when you see Excel capacity data, weekly demand schedules, step-down plans, or phrases like 'catch-up plan', 'backlog clearance', 'overtime policy'.
---

# Workload & Capacity Planning Simulation

## Quick Check: Excel Layout
**Critical**: Before parsing, determine if the data is:
- **Vertical**: Weeks in rows (standard table) → Use `ws.iter_rows()` or `pd.read_excel()`
- **Horizontal**: Weeks in columns (transposed) → See `references/horizontal-data-parsing.md`

Signs of horizontal layout: Week numbers (4, 5, 6...) appear as column headers with data values extending rightward, or multiple week ranges shown in adjacent header rows.

## Workflow
1. **Extract Input Data**: Read the source Excel file. Identify sheet orientation (horizontal vs vertical). Parse week-to-demand mapping carefully—see parsing reference if weeks are columns.
2. **Resolve Initial State**: Carefully separate "Start of Week Past Due" from "Scheduled Demand" if the prompt provides a combined initial condition (e.g., "438.81 hours including Week 4 demand"). Avoid double-counting demand in the first week's calculation.
   - Formula: `backlog = combined_value - week_4_demand`
3. **Define Policy Rules**: Map the deterministic decision tree:
   - Capacity per day (e.g., 30 std hrs)
   - Days-to-capacity mapping (4 days = 120, 5 days = 150, 6 days = 180)
   - Backlog clearing logic (choose minimum days to drive `End of Week <= 0`)
   - Steady-state logic (if demand <= 120, use 4 days; else if <= 150, use 5 days, etc.)
   - Overtime calculation: `10 * max(0, days_worked - 4)`
4. **Run Simulation**: Iterate week-by-week. Track:
   - `prior_end`: Signed backlog/buffer from previous week
   - `sow_past_due`: `max(0, prior_end)` for reporting
   - `capacity`: Based on days selected by policy
   - `overtime`: Based on days worked
   - `end_of_week`: `sow_past_due + demand - capacity`
   
   Record first occurrences: first 4-day week, first 5-day week (track as `None` initially, assign week number when first triggered).
5. **Generate Excel Output**: Create workbook. Name sheet exactly as specified (e.g., `Plan`). Write headers and data rows. **Never round numeric values**—pass raw floats. Ensure week sequences are contiguous.
6. **Generate Summary Text**: Format strictly per task spec. Common pattern: 3 lines (First_Week_5_Days, First_Week_4_Days, Summary).
   - Use `N/A` for transitions never triggered
   - Summary: max 60 words, max 3 sentences
   - Must explicitly mention step-down week numbers or `N/A`
7. **Verify Programmatically**: Run assertions before submitting. See `references/validation-checklist.md`.

## Critical Decision Rules
- **Excel Orientation**: If you see `(1):Week` or row 4 with week numbers `(2):4 (3):5...` in the raw cell output, you're looking at horizontal/transposed data. Use column-based parsing. See `references/horizontal-data-parsing.md`.
- **Initial Condition Parsing**: If given `Start of Week Past Due + Scheduled Demand = X`, compute `Calc Start = X - Demand[Week 4]` to prevent double-counting when applying `End = Calc Start + Demand - Capacity`.
- **State Tracking**: Use `max(0, prior_end)` for reporting `Start of Week Past Due`, but keep the signed `prior_end` for actual backlog/buffer calculations. Negative values indicate buffer (ahead of schedule).
- **N/A Handling**: If a policy state (e.g., 5-day week) is never triggered, explicitly output `N/A` in both the tracking variables and the summary text. Do not invent placeholder weeks.
- **Summary Constraints**: Count words and sentences programmatically. Ensure the summary explicitly mentions both step-down week numbers (or `N/A`).

## Output Precision
Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly.
- **DO NOT**: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- **DO**: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- Rationale: The verifier's tolerance (often 1e-4) decides precision; provide full precision.

## Verification
Always validate before submitting. See `references/validation-checklist.md` for reusable assertion templates covering:
- Excel: Sheet name, headers, row count, week contiguity
- Text: Line count, word/sentence limits, mandatory value presence

## Anti-Patterns
- **Do not** assume vertical/table layout for Excel input. Check for horizontal/transposed data (weeks as columns).
- **Do not** assume initial condition is purely backlog; verify if it includes scheduled demand and subtract Week 4 demand if so.
- **Do not** use string formatting on numeric outputs (no rounding).
- **Do not** hardcode summary text; generate dynamically from tracked variables.
- **Do not** skip verification; formatting constraints are strict and easily violated.

## Known invariants (by sub-task)

### capacity-backlog-simulation
- Initial condition statements often combine "Start of Week Past Due" with "Scheduled Demand" — parse carefully to avoid double-counting in Week 1.
- Summary text must be generated dynamically from tracked variables; hardcoded text goes stale.
- Word/sentence count constraints are strict and easily violated by minor phrasing changes.
- Horizontal Excel layouts (weeks as columns) require column-wise iteration instead of row-wise.
