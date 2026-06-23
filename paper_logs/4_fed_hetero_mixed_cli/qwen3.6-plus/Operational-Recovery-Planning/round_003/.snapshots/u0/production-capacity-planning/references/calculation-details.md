# Capacity Calculation Details

## Standard Capacity Assumptions

| Days/Week | Standard Hours | Overtime Hours | Total Capacity |
|-----------|---------------|----------------|----------------|
| 6         | 180           | 20             | 200            |
| 5         | 150           | 10             | 160            |
| 4         | 120           | 0              | 120            |

*Assumes 30 standard hours per day, 10 hours = 1 OT day equivalent*

## Backlog Calculation

```
End_Backlog = Start_Past_Due + Demand - Capacity
```

If `End_Backlog < 0`, backlog is cleared (cap at 0 for next week's start).
If `End_Backlog > 0`, carry forward to next week.

## Step-Down Logic

**Initial State**: Always start with 6-day weeks to maximize throughput.

**6 → 5 Transition**: Occurs when `backlog <= 0` for the first time.

**5 → 4 Transition**: Occurs when:
- Current backlog is 0 (or negative)
- Demand < 120 (4-day capacity without OT)
- Sustained for at least 1 week at 5 days

**Regression (5 → 6)**: If demand spikes while on 5-day schedule such that `Start_Past_Due + Demand > 150`, return to 6 days for that week.

## Excel Data Patterns

Common row labels in capacity sheets:
- `MIG weld Demand Total` - Total demand row
- `MIG PLT 2` - Past due / backlog row
- `Grand Total MIG Weld` - Sum including backlog

Week columns typically start at index 1 (index 0 is the label column).
Last column is often "Total" (string) and must be excluded from numeric calculations.

## Edge Cases

1. **Volatile Demand**: Week 10 may clear backlog (→ 5 days), but Week 11 high demand may force return to 6 days.
2. **Seasonal Lows**: Demand may drop below 120 early but backlog prevents 4-day weeks until cleared.
3. **Partial Weeks**: Calculations assume full weeks; partial weeks at start/end of year require manual adjustment.