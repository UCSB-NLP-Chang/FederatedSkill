# Safety Buffer Formulas and Z-Scores

## Service Level to Z-Score Mapping

| Service Level | Z-Score | Use Case |
|--------------|---------|----------|
| 90% | 1.28 | Lenient, low-cost buffer |
| 95% | 1.65 | Standard operational |
| 97.5% | 1.96 | High reliability |
| 99% | 2.33 | Critical systems |

## Safety Stock Formula

```
Safety Stock = Z × σ × √L

Where:
- Z = service factor (from table above)
- σ = standard deviation of daily demand
- L = lead time or planning period in days
- √L = square root of lead time (variance scales with time)
```

## Calculation in Python

```python
import numpy as np

Z = 1.65  # 95% service level
stddev_daily = 40  # liters per day
remaining_days = 27

safety_buffer = Z * stddev_daily * np.sqrt(remaining_days)
# = 1.65 * 40 * 5.196 = 342.95 liters
```

## Rationale for √Time

Demand variance over time periods scales with the square root of time (random walk/Brownian motion property). For independent daily demands:

- Variance over L days = L × daily_variance
- Standard deviation over L days = √L × daily_stddev

This prevents over-buffering for longer periods.

## Alternative: Buffer for Coverage Period

If buffering to cover current stock depletion:

```python
coverage_days = current_liters / daily_burn
safety_buffer = Z * stddev_daily * np.sqrt(coverage_days)
```

## Common Errors

| Error | Wrong | Right |
|-------|-------|-------|
| Linear time scaling | `Z * stddev * days` | `Z * stddev * sqrt(days)` |
| Wrong Z for 95% | 1.96 (97.5% two-tailed) | 1.65 (95% one-tailed) |
| Forgetting zero check | Divide by zero on empty | Handle zero stddev → buffer=0 |
