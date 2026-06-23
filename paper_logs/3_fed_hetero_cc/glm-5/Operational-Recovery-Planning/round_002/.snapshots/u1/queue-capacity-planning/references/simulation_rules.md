# Simulation Rules & Output Schema

## Core Formulas
- `End_Queue = Start_Queue + Demand - Capacity`
- `Start_Queue(next) = End_Queue(current)`
- Report `Start-of-Week` as `max(0, Start_Queue)` to avoid negative display values after catch-up.
- Maintain negative `End_Queue` internally to track overcapacity accurately.

## Capacity & Overtime Mapping

### SOC Alert Scenario (Default in script)
| On-Call Days | Weekly Capacity (hrs) | Burnout Overtime (hrs) |
|--------------|-----------------------|------------------------|
| 6            | 168                   | 16                     |
| 5            | 140                   | 8                      |
| 4            | 112                   | 0                      |

### Radiology Reading Scenario
| Radiologist Days | Weekly Capacity (scan hrs) | Surge Premium (hrs) |
|------------------|---------------------------|---------------------|
| 6                | 156                       | 12                  |
| 5                | 130                       | 6                   |
| 4                | 104                       | 0                   |

## Transition Thresholds
- **Initial State**: Maximum staffing (typically 6 days).
- **Catch-up End**: Triggered when `End_Queue ≤ 0`.
- **Post-Catch-up Decision**: Compare next week's `Demand` against scenario threshold.
  - For SOC: threshold is 112 (matches 4-day capacity).
  - For Radiology: threshold is 104 (matches 4-day capacity).
  - `Demand > threshold` → step to intermediate staffing (5 days).
  - `Demand ≤ threshold` → step to baseline staffing (4 days).
- **Reversion**: If at baseline and `Demand > threshold`, step back up to intermediate.

## Output Schema

### Excel (worksheet name varies by scenario)
Headers must match task requirements exactly. Common patterns:

**SOC Alert Plan**:
`Week`, `On-Call Days`, `Forecast Alert Load (Analyst Hrs)`, `Weekly Triage Capacity (Analyst Hrs)`, `Start-of-Week Alert Queue (Analyst Hrs)`, `End-of-Week Alert Queue/Buffer (Analyst Hrs)`, `Burnout Overtime Hours`

**Radiology Reading Plan**:
`Week`, `Radiologist Days`, `Forecast Reading Load (Scan Hrs)`, `Weekly Reading Capacity (Scan Hrs)`, `Start-of-Week Reading Backlog (Scan Hrs)`, `End-of-Week Reading Backlog/Buffer (Scan Hrs)`, `Surge Premium Hours`

### Summary Text (3 lines)
1. `First_Week_5_Days: <week_number>`
2. `First_Week_4_Days: <week_number>`
3. `Summary: <text>` (Must mention both transition weeks, check task for word/sentence limits.)

## Adaptation Notes
- If input Excel uses different row indices, update `CONFIG["row_weeks"]` and `CONFIG["row_demand"]` in `scripts/queue_simulator.py`.
- If capacity/overtime values change, modify the `CONFIG` dictionary.
- The transition logic automatically adapts if `demand_threshold` is updated to match your 4-day capacity.
- Always verify output headers match task requirements exactly—column names vary by scenario.
