# Outcome-Driven Production Design Patterns

Reference for designing production schedules when the task specifies target business outcomes per scenario (e.g., "May PO On-Time: No", "Crew Yes, Extended No").

## Core Principle

When a task requires specific on-time outcomes, work backwards from the target cumulative value rather than forward from capacity limits.

## Decision Rules

### Rule 1: Map Outcome to Cumulative Sign

| Required Outcome | Target Cumulative EOD | Production vs Demand |
|-----------------|----------------------|---------------------|
| On-Time: Yes | <= 0 (zero or negative) | total_production >= total_PO |
| On-Time: No | > 0 (positive backlog) | total_production < total_PO |
| Mixed (e.g., "Crew Yes, Extended No") | Check each category separately | Design per-category rates |

### Rule 2: Calculate Required Daily Rate

```python
working_days = count_working_days(start_date, end_date, holidays)
total_po = sum(po_quantities)

if outcome == "Yes":
    target_production = total_po  # or slightly more for buffer
else:  # outcome == "No"
    target_production = total_po - desired_backlog  # e.g., total_po - 60

daily_rate = target_production // working_days
remainder = target_production % working_days
```

### Rule 3: Distribute with Front-Load Remainder

```python
production = {}
for i, d in enumerate(working_day_list):
    production[d] = daily_rate + (1 if i < remainder else 0)
```

## Worked Example: Three-Scenario Recovery

### Scenario 1: Both Categories "No"

**Given**: Crew PO = 5520, Extended PO = 4035, 70 working days total.

**Design**:
- Crew: target 5460 (< 5520) → daily_rate = 5460 // 70 = 78
  - Cumulative EOD = 5520 - 5460 = 60 > 0 → "No" ✓
- Extended: starts Mar 1, 43 working days, target 3999 (< 4035)
  - daily_rate = 3999 // 43 = 93
  - Cumulative EOD = 4035 - 3999 = 36 > 0 → "No" ✓

### Scenario 2: Mixed Outcome

**Given**: Crew must be "Yes", Extended must be "No".

**Design**:
- Crew: target 5520 (= total PO) → daily_rate = 5520 // 70 = 78 remainder 56
  - 56 days get 79, 14 days get 78 → total = 5520
  - Cumulative EOD = 0 → "Yes" ✓
- Extended: starts Feb 20, 50 working days, target 3950 (< 4035)
  - daily_rate = 3950 // 50 = 79
  - Cumulative EOD = 4035 - 3950 = 85 > 0 → "No" ✓

### Scenario 3: Both "Yes" with High-Cap Window

**Given**: 22 high-cap days (up to 170), standard cap 135.

**Design**:
- Use high-cap days to boost production above standard rate.
- Outside window: produce at standard rate (e.g., 100/day).
- Inside window: produce at elevated rate (e.g., 155/day).
- Verify: total_production >= total_PO → cumulative <= 0 → "Yes" ✓

## Verification Checklist for Outcome-Driven Design

1. Count working days programmatically (never manually).
2. For each category, compute: `total_production = sum(daily_rates)`.
3. Compare: `total_production` vs `total_PO`.
4. Verify cumulative sign matches required outcome.
5. Check that daily rates respect capacity constraints.
6. Verify category start dates are honored.
7. Run full constraint verification after generation.