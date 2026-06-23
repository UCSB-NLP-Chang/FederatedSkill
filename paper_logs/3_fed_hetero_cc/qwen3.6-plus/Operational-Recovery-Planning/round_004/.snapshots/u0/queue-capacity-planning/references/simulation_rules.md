# Simulation Rules & Output Schema

## Core Formulas

```
End_Queue = Start_Queue + Demand - Capacity
Start_Queue(next) = End_Queue(current)
Display_Start_Queue = max(0, Start_Queue)  # For reporting only
Display_End_Queue = max(0, End_Queue)      # CRITICAL: Both columns clamped
```

## Capacity Configuration

Capacity and overtime scale linearly with hours-per-day:

| Days | Weekly Capacity | Overtime/Premium |
|------|-----------------|------------------|
| 6 | hrs_per_day × 6 | ot_hrs_per_day × 6 |
| 5 | hrs_per_day × 5 | ot_hrs_per_day × 5 |
| 4 | hrs_per_day × 4 | 0 |

**Threshold**: `demand_threshold_5_days` typically equals `capacity_4_days`

## Transition Logic (Pseudocode)

```python
if current_days == 6 and end_queue <= 0:
    # Backlog cleared, decide next staffing level
    current_days = 5 if demand > threshold else 4
elif current_days == 4 and demand > threshold:
    # Demand spike, step up temporarily
    current_days = 5
# Note: If at 5 days and backlog reappears (end_queue > 0 after being <= 0),
# the logic naturally stays at or reverts to 6 days on next iteration
```

## Input Layout Adaptation

**CRITICAL**: Always inspect the input Excel structure first. Row indices are 1-based.

Common patterns seen in tasks:
- **Horizontal weeks** (most common): Weeks in columns, data in rows
  - `row_weeks`: Row containing week numbers (e.g., 2, 3, 4)
  - `row_demand`: Row containing demand values (e.g., 3, 4, 11)
- **Vertical weeks**: Weeks in rows, data in columns (transpose or adjust parser)

**Debugging tip**: If you get `KeyError` or data mismatch, print `df.iloc[n]` for candidate rows to verify content before setting CONFIG.

### Multi-row demand input:
Some domains split demand across multiple rows that must be combined:
- `demand_rows`: List of 1-based row indices (e.g., `[5, 6]`)
- `demand_combine`: Method to combine values
  - `"sum"`: Add all rows together (most common)
  - `"first"`: Use only first row value
  - `"second"`: Use only second row value

## Output Schema

### Excel Worksheet

Required structure:
- Sheet name: `Plan` (or as specified)
- 7 columns in exact order (names configurable via CONFIG):
  1. Week number
  2. Staffing days (6/5/4)
  3. Forecast demand
  4. Weekly capacity
  5. Start-of-week queue (display, clamped to 0)
  6. End-of-week queue/buffer (display, clamped to 0)
  7. Overtime/premium hours

**Important**: Internal `Start_Queue` and `End_Queue` may go negative after catch-up, but both displayed columns in Excel MUST use `max(0, value)`.

### Summary Text

Format (3 lines):
```
First_Week_5_Days: <N>
First_Week_4_Days: <N>
Summary: <text>
```

Summary constraints vary by task. Always verify exact requirements from task description.

## Domain-Specific Parameter Sets

### SOC Alert Queue (Default)

| Parameter | Value |
|-----------|-------|
| hrs_per_day | 28 |
| ot_hrs_per_day | 2.67 |
| capacity_6_days | 168 |
| overtime_6_days | 16 |
| capacity_5_days | 140 |
| overtime_5_days | 8 |
| capacity_4_days | 112 |
| overtime_4_days | 0 |
| demand_threshold | 112 |
| row_weeks | 2 |
| row_demand | 4 |

Headers:
- `On-Call Days`
- `Forecast Alert Load (Analyst Hr)`
- `Weekly Triage Capacity (Analyst Hr)`
- `Start-of-Week Alert Queue (Analyst Hr)`
- `End-of-Week Alert Queue/Buffer (Analyst Hr)`
- `Burnout Overtime Hours`

### Radiology Reading Backlog

| Parameter | Value |
|-----------|-------|
| hrs_per_day | 26 |
| ot_hrs_per_day | 2 |
| capacity_6_days | 156 |
| overtime_6_days | 12 |
| capacity_5_days | 130 |
| overtime_5_days | 6 |
| capacity_4_days | 104 |
| overtime_4_days | 0 |
| demand_threshold | 104 |
| row_weeks | 3 |
| row_demand | 4 |

Headers:
- `Radiologist Days`
- `Forecast Reading Load (Scan Hrs)`
- `Weekly Reading Capacity (Scan Hrs)`
- `Start-of-Week Reading Backlog (Scan Hrs)`
- `End-of-Week Reading Backlog/Buffer (Scan Hrs)`
- `Surge Premium Hours`

### Manufacturing / Welding Catch-Up

| Parameter | Value |
|-----------|-------|
| hrs_per_day | 30 |
| ot_hrs_per_day | 3.33 |
| capacity_6_days | 180 |
| overtime_6_days | 20 |
| capacity_5_days | 150 |
| overtime_5_days | 10 |
| capacity_4_days | 120 |
| overtime_4_days | 0 |
| demand_threshold | 120 |
| row_weeks | 4 |
| row_demand | 11 |

Headers:
- `Days Worked`
- `Scheduled Demand (Std Hrs)`
- `Weekly Capacity (Std Hrs)`
- `Start of Week Past Due (Std Hrs)`
- `End of Week Backlog/Buffer (Std Hrs)`
- `Overtime Hours`

### Returns Center Throughput (Project CleanSweep)

| Parameter | Value |
|-----------|-------|
| hrs_per_day | 32 |
| ot_hrs_per_day | 3 |
| capacity_6_days | 192 |
| overtime_6_days | 18 |
| capacity_5_days | 160 |
| overtime_5_days | 9 |
| capacity_4_days | 128 |
| overtime_4_days | 0 |
| demand_threshold | 128 |
| row_weeks | 3 |
| demand_rows | [5, 6] |
| demand_combine | "sum" |

**Demand Calculation**: Standard Return Intake Hours + Exception Review Hours (rows 5 + 6)

Headers:
- `Processing Days`
- `Forecast Return Intake (Work Hrs)`
- `Weekly Processing Capacity (Work Hrs)`
- `Start-of-Week Return Queue (Work Hrs)`
- `End-of-Week Return Queue/Buffer (Work Hrs)`
- `Flex Shift Hours`

## Extending to New Domains

1. Identify analogues: backlog → queue/reading load/alert load/past-due/return intake, capacity → throughput/triage capacity/processing capacity, overtime → burnout/surge premium/flex shift
2. Determine hrs_per_day and ot_hrs_per_day from task spec
3. Calculate capacities: `capacity_N = hrs_per_day × N`, `overtime_N = ot_hrs_per_day × N` (overtime_4 = 0)
4. Set threshold = capacity_4_days
5. **Inspect input Excel** to find correct `row_weeks` and `row_demand` indices
6. Update CONFIG with initial backlog, capacities, overtime values, threshold
7. If demand is split across multiple rows, use `demand_rows` list with `demand_combine: "sum"`
8. Update header list in CONFIG to match task requirements exactly
9. Update summary_template if task has specific wording requirements