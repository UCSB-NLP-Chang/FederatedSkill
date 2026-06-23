---
name: workload-capacity-planning
description: Simulates deterministic weekly capacity, backlog, and overtime policies from Excel input data. Generates structured Excel plans and strictly formatted summary text files. Use when tasks require week-by-week workload simulation, backlog burn-down calculations, and output validation against strict formatting constraints.
---

# Workload & Capacity Planning Simulation

## Workflow
1. **Extract Input Data**: Read the source Excel file. Identify the sheet, header row, and data columns (e.g., Week, Demand). Parse all rows into a dictionary or list.
2. **Resolve Initial State**: Carefully separate "Start of Week Past Due" from "Scheduled Demand" if the prompt provides a combined initial condition. Avoid double-counting demand in the first week's calculation.
3. **Define Policy Rules**: Map out the deterministic decision tree:
   - Backlog clearing logic (e.g., choose minimum days to drive `End of Week <= 0`).
   - Steady-state logic (e.g., if demand ≤ threshold, use X days).
   - Overtime calculation (e.g., `10 * max(0, days_worked - 4)`).
4. **Run Simulation**: Iterate week-by-week. Track `prior_end`, `sow_past_due`, `calc_start`, `capacity`, `overtime`, and `end_of_week`. Record first occurrences of state transitions (e.g., first 4-day or 5-day week).
5. **Generate Excel Output**: Create a new workbook. Name the sheet exactly as specified (e.g., `Plan`). Write headers and data rows. Ensure week sequences are contiguous with no gaps.
6. **Generate Summary Text**: Format strictly. Handle `None` transitions as `N/A`. Enforce line count, word limit, sentence limit, and mandatory value mentions.
7. **Verify Programmatically**: Before submitting, run assertions on both files.

## Critical Decision Rules
- **Initial Condition Parsing**: If given `Start of Week Past Due + Scheduled Demand = X`, compute `Calc Start = X - Demand[Week 4]` to prevent double-counting when applying `End = Calc Start + Demand - Capacity`.
- **State Tracking**: Use `max(0, prior_end)` for reporting `Start of Week Past Due`, but keep the signed `prior_end` for actual backlog/buffer calculations.
- **N/A Handling**: If a policy state (e.g., 5-day week) is never triggered, explicitly output `N/A` in both the tracking variables and the summary text. Do not invent placeholder weeks.
- **Summary Constraints**: Count words and sentences programmatically. Ensure the summary explicitly mentions both step-down week numbers (or `N/A`).

## Verification Checklist
Always run a quick validation script before finalizing:
- Excel: Sheet name matches exactly. Headers match spec. Row count equals `end_week - start_week + 1`. Week column is contiguous.
- Text: Exactly 3 lines (or specified count). Summary line ≤60 words, ≤3 sentences. Contains required step-down values.
- See `references/validation-checklist.md` for reusable assertion templates.

## Anti-Patterns
- ❌ Do not assume the initial condition is purely backlog; verify if it includes scheduled demand.
- ❌ Do not hardcode summary text; generate it dynamically from tracked variables to avoid stale values.
- ❌ Do not skip verification; formatting constraints (word/sentence counts) are strict and easily violated by minor phrasing changes.