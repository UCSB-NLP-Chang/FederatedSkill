---
name: queue-capacity-planning
description: Simulate multi-week backlog burn-down with step-down staffing rules (6→5→4 days). Use for capacity planning tasks involving weekly demand, constrained resources, and phased recovery (e.g., SOC alert triage, radiology reading backlogs, manufacturing catch-up plans, support ticket queues). Triggered by inputs with weekly forecasts, initial backlog/past-due, and requirements for on-call/day transitions based on demand thresholds.
---

# Queue Capacity Planning & Backlog Simulation

## STOP — Read This First

**NEVER write new simulation code from scratch.** The script at `scripts/queue_simulator.py` already implements the step-down/step-up logic. Your job is to **modify the CONFIG dictionary** at the top of that script — NOT to write new Python code.

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
   - Week numbers row/column (1-based index)
   - Weekly demand/forecast row/column (1-based index)
   - Initial backlog/past-due value
   - Any additional load (training, maintenance, admin reserve)

2. **Configure Simulation**: Edit `CONFIG` in `scripts/queue_simulator.py`:
   - `initial_backlog`: Starting queue depth
   - Capacity/overtime for each staffing level (6/5/4 days)
   - `demand_threshold`: Demand level triggering step-up from 4→5 days
   - `row_weeks` / `row_demand`: 1-based row indices for your input layout
   - `headers`: Exact 7 column names required by the task
   - `summary_template`: Text template with `{w5}` and `{w4}` placeholders

3. **Run Simulation**: Execute the script to generate Excel plan and text summary.

4. **Verify Outputs**:
   - Excel row count matches week span
   - Headers match task requirements exactly (case-sensitive)
   - Transition weeks in summary match Excel data
   - Summary meets format constraints (lines, words, sentences)

## Core Policy (Deterministic)

| Phase | Days | Capacity | Overtime/Premium | Trigger |
|-------|------|----------|------------------|---------|
| Surge | 6 | Configured | Configured | Initial state |
| Transition | 5 | Configured | Configured | After backlog cleared AND demand > threshold |
| Steady | 4 | Configured | 0 | After backlog cleared AND demand ≤ threshold |

**Step-up rule**: If on 4 days and demand > threshold, revert to 5 days for that week. If on 5 days and backlog reappears, revert to 6 days.

## Parameter Calculation

Capacity and overtime scale linearly with hours-per-day:

```
capacity_N_days = hrs_per_day × N
overtime_N_days = ot_hrs_per_day × N
```

Example: 30 hrs/day, 3.33 OT hrs/day →
- 6-day: capacity=180, OT=20
- 5-day: capacity=150, OT=10
- 4-day: capacity=120, OT=0
- Threshold = capacity_4_days = 120

See `references/simulation_rules.md` for domain-specific parameter sets.

## Domain Adaptation Guide

| Domain | Term Mapping | Typical Headers |
|--------|-------------|-----------------|
| SOC Alerts | Alert Load, Triage Capacity, Burnout Overtime | `On-Call Days`, `Forecast Alert Load (Analyst Hr)`, `Weekly Triage Capacity (Analyst Hr)`, `Start-of-Week Alert Queue (Analyst Hr)`, `End-of-Week Alert Queue/Buffer (Analyst Hr)`, `Burnout Overtime Hours` |
| Radiology | Reading Load, Reading Capacity, Surge Premium | `Radiologist Days`, `Forecast Reading Load (Scan Hrs)`, `Weekly Reading Capacity (Scan Hrs)`, `Start-of-Week Reading Backlog (Scan Hrs)`, `End-of-Week Reading Backlog/Buffer (Scan Hrs)`, `Surge Premium Hours` |
| Manufacturing | Scheduled Demand, Past Due, Overtime | `Days Worked`, `Scheduled Demand (Std Hrs)`, `Weekly Capacity (Std Hrs)`, `Start of Week Past Due (Std Hrs)`, `End of Week Backlog/Buffer (Std Hrs)`, `Overtime Hours` |

**To adapt**: Update `CONFIG` dictionary in `scripts/queue_simulator.py`. The transition logic remains identical.

## Critical Implementation Rules

- **Never reset negative queues to zero internally**: Track `End_Queue` including negative values for accurate capacity calculations. Only clamp to zero for display/reporting.
- **Clamp ALL displayed queue columns**: Both `Start-of-Week` AND `End-of-Week` display values must use `max(0, value)`. Never show negative numbers in output.
- **Demand comparison uses current week's demand**: After clearing backlog at week N, evaluate week N's demand to decide 5 vs 4 days for that week.
- **Step-up can occur multiple times**: Demand spikes after reaching 4 days trigger temporary reversion to 5 days. Backlog reappearance at 5 days triggers reversion to 6 days.
- **Headers must match exactly**: Copy header strings verbatim from task requirements into CONFIG. Never reuse skill defaults if the task specifies different names.

## Validation Checklist

- [ ] Verify Excel shape: (weeks, 7 columns)
- [ ] Confirm headers match exactly (case-sensitive, spaces, parentheses)
- [ ] Check transition weeks: first 5-day week, first 4-day week
- [ ] Validate summary format: exact line count, word count, sentence count
- [ ] Confirm summary mentions both transition week numbers explicitly
- [ ] Spot-check: Start-of-Week and End-of-Week Queue values are ≥ 0 in output
- [ ] Verify total overtime/premium hours calculated correctly

## Anti-Patterns

- **Don't** write simulation code from scratch — modify CONFIG only.
- **Don't** hardcode domain terminology in reusable logic. Parameterize via CONFIG.
- **Don't** assume 6→5→4 is a one-way progression. Implement step-up (4→5, 5→6) for demand spikes.
- **Don't** display negative queue values. Use `max(0, queue)` for ALL reporting columns.
- **Don't** ignore additional load sources (training, maintenance, audit). Add to demand if present in input.
- **Don't** round numeric outputs before writing — pass raw floats.

## Output Precision

Never round, truncate, or fixed-format numeric values. Pass raw floats directly to Excel/CSV. The verifier's tolerance decides acceptability.

- **DO NOT**: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- **DO**: `ws.cell(row=r, column=c, value=x)` with raw float

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Transition weeks off by one | Using wrong week's demand for decision | Check demand indexing in transition logic |
| Negative displayed queues | Missing `max(0, queue)` for reporting | Clamp **both** Start and End queue display values |
| Verifier rejects summary | Wrong word/sentence count or missing week numbers | Count programmatically; ensure both transitions mentioned |
| Capacity mismatch | Wrong capacity values for domain | Verify CONFIG matches task spec (hrs/day may vary) |
| Wrong input rows | Week/demand at unexpected row indices | Inspect Excel structure first; update `row_weeks`/`row_demand` |
| Headers rejected | Typo or wrong domain terms | Copy headers verbatim from task requirements into CONFIG |

## Fallback: Manual Implementation

If script fails due to unusual input format:
1. Read input with pandas: `pd.read_excel(file, header=None)`
2. Locate week/demand rows by string search or known indices
3. Implement queue simulation loop manually following Core Policy
4. Write output with openpyxl for precise header control

See `references/simulation_rules.md` for detailed formulas and adaptation notes.