---
name: economic-time-series-analysis
description: Analyze correlations between economic time series using Hodrick-Prescott filtering. Use when computing business cycle correlations, detrending economic data, or comparing cyclical components of macroeconomic series.
---

# Economic Time Series Correlation Analysis

## When to Use
- Computing correlation between detrended economic series
- Extracting cyclical components from time series data
- Converting nominal values to real using price indices
- Handling partial-year data (quarterly to annual conversion)

## Workflow

1. **Load and inspect data**: Read Excel/CSV files, check column names and data ranges
2. **Handle partial years**: If latest year has only quarterly data, compute annual value as average of available quarters
3. **Convert to real values**: Divide nominal series by price index (base year = 1.0)
4. **Log transform**: Apply natural logarithm to real values
5. **Detrend with HP filter**: Use Hodrick-Prescott filter to extract cyclical component
6. **Compute correlation**: Pearson correlation between cyclical components

## HP Filter Lambda Values
- Annual data: λ = 100
- Quarterly data: λ = 1600
- Monthly data: λ = 14400

## Key Implementation Notes

- Align all series to the same time period before analysis
- Price index base year should match across all series
- Cyclical component = log(series) - trend
- The HP filter returns (trend, cycle) tuple in `statsmodels.tsa.filters.hpfilter`

## Common Pitfalls
- Forgetting to convert nominal to real before log transformation
- Using wrong λ value for data frequency
- Not handling missing or partial-year data consistently
- Computing correlation on raw or trend components instead of cyclical

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

For final correlation output, use formatted string to preserve trailing zeros
when the task specifies exact decimal places: `f"{corr:.5f}"` for 5 decimals.

## Required Libraries
```python
import pandas as pd
import numpy as np
from scipy.stats import pearsonr
from statsmodels.tsa.filters.hp_filter import hpfilter
```

## Quick Reference Pattern
```python
# Convert nominal to real
real_values = nominal_values / price_index

# Log transform
log_values = np.log(real_values)

# HP filter detrending (returns cycle, trend)
cycle, trend = hpfilter(log_values, lamb=100)

# Correlation
correlation = np.corrcoef(cycle1, cycle2)[0, 1]
```

## References

- `references/excel-year-parsing.md` — Common year marker formats in statistical agency data (BEA, Census, Federal Reserve)
- `scripts/hp_correlation.py` — Starting template for HP filter correlation workflow

## Known invariants (by sub-task)

### economic-time-series-correlation
- Year markers may have trailing dots (`'1994.'`) — strip with `str.rstrip('.')` or `int(float(x))`
- Quarterly markers (`'2025:I'`, `'II'`, `'III'`, `'IV'`) must be averaged to produce annual value
- Use `python3` command, not `python`
- Output correlation string must preserve trailing zeros when specified (e.g., `0.12340` for 5 decimals)