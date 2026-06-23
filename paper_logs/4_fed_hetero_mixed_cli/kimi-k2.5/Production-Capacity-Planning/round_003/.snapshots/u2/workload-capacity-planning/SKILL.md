---
name: workload-capacity-planning
description: Simulates deterministic weekly capacity, backlog, and overtime policies from Excel input data. Generates structured Excel plans and strictly formatted summary text files. Use when tasks require week-by-week workload simulation, backlog burn-down calculations, and output validation against strict formatting constraints. Trigger when you see Excel capacity data, weekly demand schedules, step-down plans, or phrases like 'catch-up plan', 'backlog clearance', 'overtime policy'.
---

# Workload & Capacity Planning Simulation

## Quick Check: Excel Layout
**Critical**: Before parsing, determine if the data is:
- **Vertical**: Weeks/Periods in rows (standard table) → Use `ws.iter_rows()` or `pd.read_excel()`
- **Horizontal**: Weeks/Periods in columns (transposed) → See `references/horizontal-data-parsing.md`

Signs of horizontal layout: Week numbers (4, 5, 6...) appear as column headers with data values extending rightward, or multiple week ranges shown in adjacent header rows.

**Terminology note**: Tasks may use "Week" or "Period" interchangeably. Headers may say "Start of Week" or "Start of Period"—treat these as equivalent.

## Workflow
1. **Extract Input Data**: Read the source Excel file. Identify sheet orientation (horizontal vs vertical). Parse week-to-demand mapping carefully—see parsing reference if weeks are columns.
2. **Resolve Initial State**: Carefully separate "Start of Week/Period Past Due" from "Scheduled Demand" if the prompt provides a combined initial condition (e.g., "538.08 hours including Period 1 demand of 138.08"). Avoid double-counting demand in the first period's calculation.
   - Formula: `backlog = combined_value - first_period_demand`
3. **Define Policy Rules**: Map the deterministic decision tree:
   - Capacity per day (e.g., 30 std hrs)
   - Days-to-capacity mapping (4 days = 120, 5 days = 150, 6 days = 180)
   - Backlog clearing logic (choose minimum days to drive `End of Week/Period <= 0`)
   - Steady-state logic (if demand <= 120, use 4 days; else if <= 150, use 5 days, etc.)
   - Overtime calculation: `10 * max(0, days_worked - 4)`
4. **Run Simulation**: Iterate period-by-period. Track:
   - `prior_end`: Signed backlog/buffer from previous period
   - `sow_past_due`: `max(0, prior_end)` for reporting
   - `capacity`: Based on days selected by policy
   - `overtime`: Based on days worked
   - `end_of_period`: `sow_past_due + demand - capacity`
   
   Record first occurrences: first 4-day period, first 5-day period (track as `None` initially, assign period number when first triggered).
5. **Generate Excel Output**: Create workbook. Name sheet exactly as specified (e.g., `Plan`). Write headers and data rows. **Never round numeric values**—pass raw floats. Ensure period sequences are contiguous.
6. **Generate Summary Text**: Format strictly per task spec. Common pattern: 3 lines (First_Week_5_Days/First_Period_5_Days, First_Week_4_Days/First_Period_4_Days, Summary).
   - Use `N/A` for transitions never triggered
   - Summary: max 60 words, max 3 sentences
   - Must explicitly mention step-down period numbers or `N/A`
7. **Verify Programmatically**: Run assertions before submitting. See `references/validation-checklist.md`.

## Critical Decision Rules
- **Excel Orientation**: If you see `(1):Week` or row 4 with period numbers `(2):4 (3):5...` in the raw cell output, you're looking at horizontal/transposed data. Use column-based parsing. See `references/horizontal-data-parsing.md`.
- **Initial Condition Parsing**: If given `Start of Week/Period Past Due + Scheduled Demand = X`, compute `Calc Start = X - Demand[First_Period]` to prevent double-counting when applying `End = Calc Start + Demand - Capacity`.
- **State Tracking**: Use `max(0, prior_end)` for reporting `Start of Week/Period Past Due`, but keep the signed `prior_end` for actual backlog/buffer calculations. Negative values indicate buffer (ahead of schedule).
- **N/A Handling**: If a policy state (e.g., 5-day period) is never triggered, explicitly output `N/A` in both the tracking variables and the summary text. Do not invent placeholder periods.
- **Summary Constraints**: Count words and sentences programmatically. Ensure the summary explicitly mentions both step-down period numbers (or `N/A`).

## Output Precision
Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly.
- **DO NOT**: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- **DO**: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- Rationale: The verifier's tolerance (often 1e-4) decides precision; provide full precision.

## Verification
Always validate before submitting. See `references/validation-checklist.md` for reusable assertion templates covering:
- Excel: Sheet name, headers, row count, period contiguity
- Text: Line count, word/sentence limits, mandatory value presence
- **Critical**: Verify transition boundary periods (e.g., if step-down happens at period 29, inspect periods 27-32 to confirm the logic triggers correctly)

## Anti-Patterns
- **Do not** assume vertical/table layout for Excel input. Check for horizontal/transposed data (periods as columns).
- **Do not** assume initial condition is purely backlog; verify if it includes scheduled demand and subtract first period's demand if so.
- **Do not** use string formatting on numeric outputs (no rounding).
- **Do not** hardcode summary text; generate dynamically from tracked variables.
- **Do not** skip verification; formatting constraints are strict and easily violated.

## Known invariants (by sub-task)

### capacity-backlog-simulation
- Initial condition statements often combine "Start of Week/Period Past Due" with "Scheduled Demand" — parse carefully to avoid double-counting in the first iteration.
- Summary text must be generated dynamically from tracked variables; hardcoded text goes stale.
- Word/sentence count constraints are strict and easily violated by minor phrasing changes.
- Horizontal Excel layouts (periods as columns) require column-wise iteration instead of row-wise.
- Period ranges vary by task (commonly 1-52 or 4-53); never assume a fixed row count.
