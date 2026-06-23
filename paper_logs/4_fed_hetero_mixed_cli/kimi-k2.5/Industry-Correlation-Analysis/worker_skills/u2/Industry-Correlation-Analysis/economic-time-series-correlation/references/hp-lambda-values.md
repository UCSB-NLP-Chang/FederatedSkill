# HP Filter Lambda Values by Data Frequency

The Hodrick-Prescott filter smoothing parameter λ depends on data frequency.

## Ravn-Uhlig Adjustment

Standard formula: λ = 100 × frequency^4

| Frequency | Lambda | Calculation |
|-----------|--------|-------------|
| Annual | 100 | 100 × 1^4 |
| Quarterly | 1600 | 100 × 4^4 |
| Monthly | 14400 | 100 × 12^4 |

## Common Errors

- **Incorrect monthly lambda**: Some sources cite λ=6.25 for monthly data.
  This is wrong. The correct value is λ=14400 (Ravn-Uhlig adjustment).

- **Why λ=6.25 is wrong**: It comes from an alternative calibration method
  that produces inconsistent detrending across frequencies.

## Usage in statsmodels

```python
from statsmodels.tsa.filters.hp_filter import hpfilter

# Annual data
trend, cycle = hpfilter(log_values, lamb=100)

# Quarterly data
trend, cycle = hpfilter(log_values, lamb=1600)

# Monthly data
trend, cycle = hpfilter(log_values, lamb=14400)
```

## Usage in custom implementation

See `scripts/hp_filter.py` for a pure-numpy implementation that accepts
the same lambda parameter.