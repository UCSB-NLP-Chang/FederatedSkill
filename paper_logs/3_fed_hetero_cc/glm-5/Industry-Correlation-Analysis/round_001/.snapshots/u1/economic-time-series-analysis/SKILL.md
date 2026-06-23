---
name: economic-time-series-analysis
description: Analyze economic time series by deflating nominal values, extracting cyclical components via HP filter, and computing correlations. Use when tasks involve real vs nominal indicators, detrending, business cycle analysis, or cross-series correlation of macroeconomic data.
---

# Time Series Detrending with HP Filter

## Quick Start

```python
from statsmodels.tsa.filters.hp_filter import hpfilter
import numpy as np
from scipy.stats import pearsonr

# Apply HP filter to log-transformed series
cycle, trend = hpfilter(np.log(series), lamb=100)

# Correlate cyclical components
corr, pvalue = pearsonr(cycle1, cycle2)
```

## Critical Import Note

**HP filter is in statsmodels, NOT scipy.**

```python
# CORRECT
from statsmodels.tsa.filters.hp_filter import hpfilter

# WRONG - will fail
from scipy.signal import hpfilter  # ImportError
```

## Standard Workflow

1. **Handle mixed-frequency data**: If quarterly data appears in annual series (e.g., "2025:I", "II", "III"), average them to get annual value.
2. **Convert nominal to real**: Divide by price index: `real = nominal / price_index`
3. **Log transform**: Apply `np.log()` to real values before HP filter
4. **Apply HP filter**: Use `lamb=100` for annual data, `lamb=1600` for quarterly
5. **Extract cyclical component**: The `cycle` output is the detrended series
6. **Compute correlation**: Use `pearsonr()` on cyclical components

## Lambda Values by Frequency

| Data Frequency | λ (lambda) |
|---------------|------------|
| Annual        | 100        |
| Quarterly     | 1600       |
| Monthly       | 14400      |

## Common Patterns

### Averaging Quarterly Data
```python
# When quarterly data appears as rows like "2025:I", "II", "III"
q_values = df[df['year_col'].str.contains(':', na=False)]['value_col'].values
annual_2025 = np.mean(q_values)
```

### Real Value Conversion
```python
# Price index with base year (e.g., 2025=1.0)
real_series = nominal_series / price_index
```

## Validation Checklist

- [ ] Series lengths match before correlation
- [ ] No NaN values in cyclical components
- [ ] Lambda matches data frequency
- [ ] Log transformation applied before HP filter
- [ ] Correlation computed on cycle component, not trend

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### economic-hp-correlation
- Clean year columns that may contain trailing dots (e.g., `1994.` → `1994`)
- Price index base year typically equals 1.0; verify before dividing
- Verify cyclical component mean ≈ 0 after HP filter