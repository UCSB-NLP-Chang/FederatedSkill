---
name: queue-capacity-planning
description: Use when simulating multi-week backlog burn-down with step-down staffing rules. Triggered by tasks involving weekly demand forecasts, capacity planning with transitions between staffing levels (e.g., 6→5→4 days), and Excel output with constrained text summaries. Applies to SOC alert queues, radiology reading backlogs, and similar capacity-constrained work queues.
---

# Queue Capacity Planning & Backlog Simulation

## Workflow
1. **Inspect Input Data**: Load the reference spreadsheet. Identify rows/columns for Week numbers and Demand/Load values. Note the initial backlog value.
2. **Identify Scenario Parameters**: Determine capacity values, overtime hours, and demand thresholds for your specific scenario (see Parameter Adaptation below).
3. **Run Simulation**: Either adapt `scripts/queue_simulator.py` with your parameters or implement inline. Generate both Excel plan and text summary.
4. **Verify Outputs**:
   - Excel row count matches the week span.
   - Headers match required column names for your scenario.
   - Transition weeks in summary match Excel data.
   - Summary meets constraints (word count, sentence count, required mentions).

## Decision Rules & Transition Logic
- **Initial State**: Start at maximum staffing (typically 6 days).
- **Catch-up Phase**: Maintain max staffing until `End-of-Week Queue ≤ 0`.
- **Step-Down Trigger**: Once backlog clears, evaluate next week's demand against threshold to decide staffing level.
- **Step-Up Trigger**: If demand exceeds threshold while at lower staffing, revert to higher staffing.
- **Queue Tracking**: `End_Queue = Start_Queue + Demand - Capacity`. Report `Start-of-Week` as `max(0, Start_Queue)` but track negative buffer internally.

## Parameter Adaptation

Different scenarios require different parameters. The `scripts/queue_simulator.py` uses SOC alert defaults. Adapt for your scenario:

| Parameter | SOC Alerts | Radiology Readings | Your Scenario |
|-----------|------------|-------------------|---------------|
| Capacity (6-day) | 168 hrs | 156 scan hrs | ... |
| Capacity (5-day) | 140 hrs | 130 scan hrs | ... |
| Capacity (4-day) | 112 hrs | 104 scan hrs | ... |
| Overtime (6-day) | 16 hrs | 12 hrs | ... |
| Overtime (5-day) | 8 hrs | 6 hrs | ... |
| Overtime (4-day) | 0 hrs | 0 hrs | ... |
| Demand threshold | 112 | 104 | ... |
| Initial backlog | 407 | varies | ... |

**To adapt the script**: Modify the `CONFIG` dictionary in `scripts/queue_simulator.py` or implement the logic inline with your parameters.

**Input layout varies**: Check row indices for weeks and demand data. Update `row_weeks` and `row_demand` in CONFIG or adjust your parser accordingly.

## Anti-Patterns
- **Do not** reset the internal queue to 0 when it goes negative. Track the negative buffer to prevent capacity miscalculations.
- **Do not** assume staffing only steps down once. Demand spikes can trigger temporary step-ups.
- **Do not** hardcode summary text without verifying word/sentence counts programmatically.
- **Do not** use the default script parameters without verifying they match your scenario.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### radiology-reading-backlog
- Excel headers must match exactly: `Week`, `Radiologist Days`, `Forecast Reading Load (Scan Hrs)`, `Weekly Reading Capacity (Scan Hrs)`, `Start-of-Week Reading Backlog (Scan Hrs)`, `End-of-Week Reading Backlog/Buffer (Scan Hrs)`, `Surge Premium Hours`.
- Summary must be exactly 3 lines: `First_Week_5_Days: <N>`, `First_Week_4_Days: <N>`, `Summary: <text>` (27 words, 2 sentences, mentions "Project PulseLift" and "Milestone").
- Capacity values: 156/130/104 scan hrs for 6/5/4 days; premium: 12/6/0 hrs.
- Demand threshold: 104 (matches 4-day capacity).

### soc-alert-queue-planning
- Excel headers must match exactly: `Week`, `On-Call Days`, `Forecast Alert Load (Analyst Hrs)`, `Weekly Triage Capacity (Analyst Hrs)`, `Start-of-Week Alert Queue (Analyst Hrs)`, `End-of-Week Alert Queue/Buffer (Analyst Hrs)`, `Burnout Overtime Hours`.
- Summary must be exactly 3 lines: `First_Week_5_Days: <N>`, `First_Week_4_Days: <N>`, `Summary: <text>` (~38 words, 3 sentences, mentions both transition weeks).
- Capacity values: 168/140/112 hrs for 6/5/4 days; overtime: 16/8/0 hrs.
- Demand threshold: 112 (matches 4-day capacity).

## Troubleshooting
- If the script fails due to unexpected input layout, read `references/simulation_rules.md` and adjust row/column indices.
- If transition weeks seem wrong, verify demand threshold matches your scenario's capacity values.
- If verifier rejects output, check that column headers match the exact names specified in your task.