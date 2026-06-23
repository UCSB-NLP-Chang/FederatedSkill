# Simulation Rules & Output Schema

## Core Formulas

```
End_Queue = Start_Queue + Demand - Capacity
Start_Queue(next) = End_Queue(current)
Display_Start_Queue = max(0, Start_Queue)  # For reporting only
```

## Capacity Configuration

Default values (SOC domain). Scale proportionally for other domains:

| Days | Weekly Capacity | Overtime/Premium |
|------|-----------------|------------------|
| 6 | 168 hrs | 16 hrs |
| 5 | 140 hrs | 8 hrs |
| 4 | 112 hrs | 0 hrs |

**Threshold**: `demand_threshold_5_days = 112` (default)

## Transition Logic (Pseudocode)

```python
if current_days == 6 and end_queue <= 0:
    # Backlog cleared, decide next staffing level
    current_days = 5 if next_demand > threshold else 4
elif current_days == 4 and demand > threshold:
    # Demand spike, step up temporarily
    current_days = 5
```

## Input Layout Adaptation

Standard row-based input (horizontal weeks):
- `row_weeks`: 1-based row index containing week numbers
- `row_demand`: 1-based row index containing weekly demand values

For column-based input (vertical weeks), transpose or adjust parser.

## Output Schema

### Excel Worksheet

Required structure:
- Sheet name: `Plan` (or as specified)
- 7 columns in exact order:
  1. Week number
  2. Staffing days (6/5/4)
  3. Forecast demand
  4. Weekly capacity
  5. Start-of-week queue (display, clamped to 0)
  6. End-of-week queue/buffer (actual, may be negative)
  7. Overtime/premium hours

### Summary Text

Format (3 lines):
```
First_Week_5_Days: <N>
First_Week_4_Days: <N>
Summary: <text>
```

Summary constraints vary by task:
- **SOC standard**: ~38 words, 3 sentences, mention both transition weeks
- **Radiology variant**: ~27 words, 2 sentences, mention project name and milestone

Always verify exact requirements from task description.

## Domain-Specific Adaptations

### Radiology Reading Backlog

Parameter changes from default:
- `initial_backlog`: varies (e.g., 372.3)
- Capacity: 156/130/104 (26 hrs/day × 6/5/4 days)
- Premium hours: 12/6/0 (2 hrs/day × 6/5 days)
- Threshold: 104 (4-day capacity)

Headers:
- `Radiologist Days`
- `Forecast Reading Load (Scan Hrs)`
- `Weekly Reading Capacity (Scan Hrs)`
- `Start-of-Week Reading Backlog (Scan Hrs)`
- `End-of-Week Reading Backlog/Buffer (Scan Hrs)`
- `Surge Premium Hours`

Input layout:
- `row_weeks`: 3 (not 2)
- `row_demand`: 4

### SOC Alert Queue

See `SKILL.md` for default parameters and headers.

## Extending to New Domains

1. Identify analogues: backlog → queue/reading load/alert load, capacity → throughput/triage capacity, overtime → burnout/surge premium
2. Map staffing levels to day counts and calculate proportional capacities
3. Determine threshold (typically the 4-day capacity)
4. Update CONFIG with initial backlog, capacities, overtime values, threshold
5. Update header list in output writer
6. Adjust summary template for domain terminology

## Adaptation Notes

- If input Excel uses different row indices, update `CONFIG["row_weeks"]` and `CONFIG["row_demand"]` in `scripts/queue_simulator.py`.
- If capacity/overtime values change, modify the `CONFIG` dictionary.
- The transition logic automatically adapts if `demand_threshold` is updated to match your 4-day capacity.
- Always verify output headers match task requirements exactly—column names vary by scenario.