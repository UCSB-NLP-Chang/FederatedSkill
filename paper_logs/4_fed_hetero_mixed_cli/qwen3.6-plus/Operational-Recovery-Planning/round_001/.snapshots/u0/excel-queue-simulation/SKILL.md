---
name: excel-queue-simulation
description: Handles tasks requiring reading tabular Excel data, running a stateful weekly simulation based on a deterministic policy, and generating strictly formatted output workbooks and summary files. Use when given queue/capacity planning problems with step-down rules, threshold-based day selection, and exact output constraints.
---

# Excel Queue Simulation & Policy Planning

## Workflow
1. **Extract Source Data**: Read the input Excel file. Identify the row containing the time-series demand/load and map it to week indices (1..N).
2. **Define Simulation State**: Initialize `calc_start` (signed carryover) and `report_queue` (`max(0, calc_start)`). Track `prev_end` for the next iteration.
3. **Run Weekly Loop**: For each week:
   - Apply policy rules to choose capacity/days based on `report_queue` and demand thresholds.
   - Compute `weekly_cap`, `end_queue`, and secondary metrics (e.g., overtime).
   - Update state: `prev_end = end_queue`.
   - Store row data.
4. **Generate Outputs**:
   - **Workbook**: Create a new sheet named exactly as specified. Write headers in row 1, data in rows 2..N+1. Ensure ascending week order.
   - **Summary**: Write exactly 3 lines. Line 1 & 2: key findings. Line 3: concise summary (≤60 words, ≤3 sentences).
5. **Verify Constraints**: Run `scripts/verify_outputs.py <summary_path> <workbook_path>` to programmatically check line counts, word/sentence limits, Excel headers, and row counts before finalizing.

## Critical Decision Rules
- **Signed vs Reporting State**: Always maintain a signed `calc_start` for arithmetic (allows negative buffer accumulation). Use `max(0, calc_start)` *only* for policy branching and reporting columns.
- **Threshold Branching**: If policy says "choose smallest days such that X ≤ 0", iterate `[min_days, max_days]` and pick the first match. Default to max if none match.
- **Floating Point**: Round outputs to 2 decimals for display, but keep full precision in intermediate calculations to avoid drift.
- **Summary Formatting**: Do not rely on terminal wrapping. Use `wc -l` and Python string methods to verify exact line count, word count, and sentence count.

## Anti-Patterns
- ❌ Do not reset the queue to 0 when it goes negative; the signed carryover must persist.
- ❌ Do not hardcode week counts; derive from source data dimensions.
- ❌ Do not guess summary constraints; verify programmatically.