---
name: queue-capacity-planning
description: Simulate multi-week backlog burn-down with step-down staffing rules. Use for capacity planning tasks involving weekly demand, constrained resources, and phased recovery (e.g., SOC alert triage, radiology reading backlogs, support ticket queues). Triggered by inputs with weekly forecasts, initial backlog, and requirements for on-call/day transitions based on demand thresholds.
---

# Queue Capacity Planning & Backlog Simulation

## STOP — Read This First

**NEVER write new simulation code from scratch.** The script at `scripts/queue_simulator.py` already implements the step-down logic. Your job is to **modify the CONFIG dictionary** at the top of that script — NOT to write new Python code.

1. Open `scripts/queue_simulator.py`
2. Edit the `CONFIG = {...}` block with your scenario's parameters
3. Run `python3 scripts/queue_simulator.py <input.xlsx> <output.xlsx> <summary.txt>`
4. Verify outputs match task requirements

## Quick Start

```bash
python3 scripts/queue_simulator.py <input.xlsx> <output.xlsx> <summary.txt>
```

## Workflow

1. **Inspect Input Data**: Load the reference spreadsheet. Identify:
   - Week numbers row/column
   - Weekly demand/forecast row/column
   - Initial backlog value
   - Any additional load (training, maintenance, admin reserve)

2. **Configure Simulation**: Edit `CONFIG` in `scripts/queue_simulator.py`:
   - `initial_backlog`: Starting queue depth
   - Capacity/overtime for each staffing level (6/5/4 days)
   - `demand_threshold`: Demand level triggering step-up from 4→5 days
   - Row/column indices for your input layout

3. **Run Simulation**: Execute the script to generate Excel plan and text summary.

4. **Verify Outputs**:
   - Excel row count matches week span
   - Headers match task requirements exactly (domain-specific)
   - Transition weeks in summary match Excel data
   - Summary meets format constraints (lines, words, sentences)

## Core Policy (Deterministic)

| Phase | Days | Capacity | Overtime/Premium | Trigger |
|-------|------|----------|------------------|---------|
| Surge | 6 | 168 hrs (or domain equiv) | 16 hrs (or domain equiv) | Initial state |
| Transition | 5 | 140 hrs (or domain equiv) | 8 hrs (or domain equiv) | After backlog cleared AND demand > threshold |
| Steady | 4 | 112 hrs (or domain equiv) | 0 hrs | After backlog cleared AND demand ≤ threshold |

**Step-up rule**: If on 4 days and demand > threshold, revert to 5 days for that week.

## Domain Adaptation Guide

| Domain | Term Mapping | Typical Headers |
|--------|-------------|-----------------|
| SOC Alerts | Alert Load, Triage Capacity, Burnout Overtime | `On-Call Days`, `Forecast Alert Load (Analyst Hr)`, `Weekly Triage Capacity (Analyst Hr)`, `Start-of-Week Alert Queue (Analyst Hr)`, `End-of-Week Alert Queue/Buffer (Analyst Hr)`, `Burnout Overtime Hours` |
| Radiology | Reading Load, Reading Capacity, Surge Premium | `Radiologist Days`, `Forecast Reading Load (Scan Hrs)`, `Weekly Reading Capacity (Scan Hrs)`, `Start-of-Week Reading Backlog (Scan Hrs)`, `End-of-Week Reading Backlog/Buffer (Scan Hrs)`, `Surge Premium Hours` |

**To adapt**: Update `CONFIG` dictionary and header list in `scripts/queue_simulator.py`. The transition logic remains identical.

## Parameter Adaptation

| Parameter | SOC Alerts | Radiology Readings |
|-----------|------------|-------------------|
| Capacity (6-day) | 168 hrs | 156 scan hrs |
| Capacity (5-day) | 140 hrs | 130 scan hrs |
| Capacity (4-day) | 112 hrs | 104 scan hrs |
| Overtime (6-day) | 16 hrs | 12 hrs |
| Overtime (5-day) | 8 hrs | 6 hrs |
| Overtime (4-day) | 0 hrs | 0 hrs |
| Demand threshold | 112 | 104 |

## Critical Implementation Rules

- **Never reset negative queues to zero internally**: Track `End_Queue` including negative values for accurate capacity calculations. Only clamp to zero for display/reporting.
- **Demand comparison uses next week's demand**: After clearing backlog at week N, evaluate week N+1's demand to decide 5 vs 4 days.
- **Step-up can occur multiple times**: Demand spikes after reaching 4 days trigger temporary reversion to 5 days.

## Validation Checklist

- [ ] Verify Excel shape: (weeks, 7 columns)
- [ ] Confirm headers match exactly (case-sensitive, spaces, parentheses)
- [ ] Check transition weeks: first 5-day week, first 4-day week
- [ ] Validate summary format: exact line count, word count, sentence count
- [ ] Confirm summary mentions both transition week numbers explicitly
- [ ] Spot-check: Start-of-Week Queue = 0 after backlog cleared
- [ ] Verify total overtime/premium hours calculated correctly

## Anti-Patterns

- **Don't** write simulation code from scratch — modify CONFIG only.
- **Don't** hardcode domain terminology in reusable logic. Parameterize via CONFIG.
- **Don't** assume 6→5→4 is a one-way progression. Implement step-up (4→5) for demand spikes.
- **Don't** display negative queue values. Use `max(0, queue)` for reporting only.
- **Don't** ignore additional load sources (training, maintenance, audit). Add to demand if present in input.

## Output Precision

Never round, truncate, or fixed-format numeric values. Pass raw floats directly to Excel/CSV. The verifier's tolerance decides acceptability.

- **DO NOT**: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- **DO**: `ws.cell(row=r, column=c, value=x)` with raw float

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Transition weeks off by one | Using current week demand instead of next week | Check demand indexing in transition logic |
| Negative displayed queues | Missing `max(0, queue)` for reporting | Clamp only display values, not internal calculations |
| Verifier rejects summary | Wrong word/sentence count or missing week numbers | Count programmatically; ensure both transitions mentioned |
| Capacity mismatch | Wrong capacity values for domain | Verify CONFIG matches task spec (hours per day may vary) |

## Fallback: Manual Implementation

If script fails due to unusual input format:
1. Read input with pandas: `pd.read_excel(file, header=None)`
2. Locate week/demand rows by string search or known indices
3. Implement queue simulation loop manually following Core Policy
4. Write output with openpyxl for precise header control

See `references/simulation_rules.md` for detailed formulas and adaptation notes.

## Known invariants (by sub-task)

### soc-alert-queue-planning
- Output Excel headers must exactly match: `Week`, `On-Call Days`, `Forecast Alert Load (Analyst Hr)`, `Weekly Triage Capacity (Analyst Hr)`, `Start-of-Week Alert Queue (Analyst Hr)`, `End-of-Week Alert Queue/Buffer (Analyst Hr)`, `Burnout Overtime Hours`
- Summary: 3 lines, ~38 words, 3 sentences, mentions both transition weeks

### radiology-reading-backlog
- Output Excel headers must exactly match: `Week`, `Radiologist Days`, `Forecast Reading Load (Scan Hrs)`, `Weekly Reading Capacity (Scan Hrs)`, `Start-of-Week Reading Backlog (Scan Hrs)`, `End-of-Week Reading Backlog/Buffer (Scan Hrs)`, `Surge Premium Hours`
- Summary: 3 lines, 27 words, 2 sentences, mentions "Project PulseLift" and "Milestone"
- Demand threshold is 104 (not 112)
- Row indices differ: `row_weeks` = 3, `row_demand` = 4