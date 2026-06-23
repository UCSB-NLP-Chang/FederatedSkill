---
name: queue-capacity-planning
description: Use when simulating multi-week backlog burn-down, capacity planning with step-down staffing rules, or generating Excel queue plans with constrained text summaries. Triggered by inputs containing weekly demand, training, or audit hours alongside requirements for on-call day transitions (e.g., 6→5→4 days based on backlog and demand thresholds).
---

# Queue Capacity Planning & Backlog Simulation

## Workflow
1. **Inspect Input Data**: Load the reference spreadsheet. Identify rows/columns for Week numbers, Demand/Alert Load, Training Hours, and Audit Hours. Note the initial backlog value.
2. **Run Simulation**: Execute `scripts/queue_simulator.py` with the input path, output Excel path, and output summary path. The script implements the standard step-down logic and generates both deliverables.
3. **Verify Outputs**:
   - Check Excel row count matches the week span.
   - Verify headers exactly match: `Week`, `On-Call Days`, `Forecast Alert Load (Analyst Hrs)`, `Weekly Triage Capacity (Analyst Hrs)`, `Start-of-Week Alert Queue (Analyst Hrs)`, `End-of-Week Alert Queue/Buffer (Analyst Hrs)`, `Burnout Overtime Hours`.
   - Confirm transition weeks in the summary match the Excel data.
   - Validate summary constraints: exactly 3 lines, ~38 words, 3 sentences, mentions both step-down weeks.

## Decision Rules & Transition Logic
- **Start**: 6 on-call days (168 hrs capacity, 16 hrs overtime).
- **Catch-up Phase**: Maintain 6 days until `End-of-Week Queue ≤ 0`.
- **Step-Down Trigger**: Once backlog is cleared, evaluate next week's demand:
  - If `Demand > 112` → switch to 5 days (140 hrs capacity, 8 hrs overtime).
  - If `Demand ≤ 112` → switch to 4 days (112 hrs capacity, 0 hrs overtime).
- **Step-Up Trigger**: If currently on 4 days and `Demand > 112`, revert to 5 days.
- **Queue Tracking**: `End_Queue = Start_Queue + Demand - Capacity`. Clamp `Start-of-Week` to `0` for reporting after catch-up, but maintain the negative buffer internally for accurate capacity tracking.

## Anti-Patterns
- **Do not** reset the internal queue to 0 when it goes negative. Track the negative buffer to prevent capacity miscalculations in subsequent weeks.
- **Do not** assume staffing only steps down once. Demand spikes can trigger temporary step-ups (4 → 5 days).
- **Do not** hardcode summary text without verifying word/sentence counts programmatically.

## Troubleshooting
- If the script fails due to unexpected input layout, read `references/simulation_rules.md` to adjust row/column indices in the parser.
- If verifier rejects the summary, check sentence boundaries and ensure both transition weeks are explicitly named.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### soc-alert-queue-planning
- Output Excel headers must exactly match the schema in `references/simulation_rules.md`.
- Summary must be exactly 3 lines, ~38 words, 3 sentences, mentioning both step-down weeks.