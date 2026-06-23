---
name: economic-time-series-correlation
description: Correlate detrended economic time series (e.g., business cycles). Use when analyzing cyclical relationships between macroeconomic variables, deflating nominal values, applying HP filter, or handling messy year markers from statistical tables (BEA, Census, etc.).
---

# Economic Time Series Correlation

Analyze correlations between detrended economic variables through deflation, HP filtering, and cyclical component extraction.

## When to Use

- Computing correlation between detrended economic series
- Extracting cyclical components from time series data
- Converting nominal values to real using price indices
- Handling partial-year data (quarterly to annual conversion)

## Workflow

1. **Read Data**: Use `python3` and `pandas` to read Excel/CSV files. Do not rely on `read_file` for binary spreadsheets.
2. **Inspect raw year markers**: Before parsing, print unique values from the year column to identify formatting artifacts (trailing dots, quarterly markers). Pandas often infers mixed numeric/string columns as `object` (strings).
3. **Parse Time Markers**: Handle mixed annual/quarterly markers (e.g., `"2025:I"`, `"II"`, `"III"`). Average all quarterly values for the partial year into a single annual value. Run `scripts/parse_year_markers.py` for reusable parsing functions.
4. **Align series**: Merge datasets on year; verify identical length and year range after cleaning.
5. **Deflate**: Compute real series: `real = nominal / price_index` (confirm base year = 1.0 in price data).
6. **Log Transform**: `log_real = np.log(real)`.
7. **HP Filter**: Apply Hodrick-Prescott filter to extract cyclical component. **statsmodels returns `(cycle, trend)`** — use index `[0]` for the cyclical component.
8. **Correlate**: Compute Pearson correlation between the two cyclical components.
9. **Format Output**: Always use `f"{corr:.5f}"` to preserve trailing zeros when outputting 5 decimal places.

## HP Filter Lambda Values

- Annual data: λ = 100
- Quarterly data: λ = 1600
- Monthly data: λ = 14400 (Ravn-Uhlig adjustment: λ = 100 × frequency^4)

## Validation

- Verify year parsing: Compare unique values before/after conversion; ensure no `NaN` years post-merge.
- Check deflation: Real values should be roughly same magnitude as nominal for base year.
- **Verify HP filter**: Cyclical component should oscillate around zero. Check `np.abs(cycle.mean()) < 1e-6`. If the mean is large or the series is monotonic, you extracted the trend instead of the cycle.

## Anti-Patterns & Pitfalls

- **Python Command**: Use `python3`, not `python`.
- **Wrong import**: `scipy.signal.hp_filter` does NOT exist; use `statsmodels.tsa.filters.hp_filter.hpfilter`.
- **HP Filter Return Order**: `hpfilter()` returns `(cycle, trend)`, NOT `(trend, cycle)`. Using `[1]` extracts the trend, which will produce a smooth, non-zero-mean series and incorrect correlations. Always use `[0]` or unpack as `cycle, trend = hpfilter(...)`.
- **Year Parsing**: Do not cast year columns directly to `int` without inspection; statistical tables commonly use `'1994.'` (trailing dot) or quarterly markers which raise `ValueError`.
- **Quarterly Parsing**: Do not assume partial-year rows are already annualized. Look for markers like `:I`, `II`, `III`, `IV` and average them.
- **Trailing Zeros**: `round(x, 5)` drops trailing zeros in Python. Use formatted strings `f"{x:.5f}"` for exact decimal output.
- **HP Filter on Nominal**: Always deflate and take log before applying HP filter. Never apply to raw nominal values.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

For the correlation output specifically, use `f"{corr:.5f}"` to preserve trailing zeros as required by the verifier.

## Required Libraries

```python
import pandas as pd
import numpy as np
from scipy.stats import pearsonr
from statsmodels.tsa.filters.hp_filter import hpfilter  # NOT scipy.signal
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

## Scripts

| Script | Use when |
|--------|----------|
| `scripts/hp_correlation.py` | Full workflow template: quarterly parsing, deflation, HP filtering, validation. Adjust paths and column names. |
| `scripts/parse_year_markers.py` | Year column contains trailing dots, quarterly markers (`2025:I`, `II`, `III`), or mixed formats. Import functions or run with `--test` to verify. |

## Known invariants (by sub-task)

### annual-time-series-correlation
- Output format: string with exactly 5 decimal places, trailing zeros preserved
- Lambda: λ=100 for annual data (Ravn-Uhlig standard)
- Price index base year: verify base year = 1.0 before deflation

### quarterly-time-series-correlation
- Lambda: λ=1600 for quarterly data (Ravn-Uhlig: 100 × 4^4)
- Quarter averaging: average all available quarters for partial years

### monthly-time-series-correlation
- Lambda: λ=14400 for monthly data (Ravn-Uhlig: 100 × 12^4 = 14400)
- Note: Some sources cite λ=6.25 (incorrect); use 14400

## References

- `references/excel-year-parsing.md` — Common year marker formats in statistical agency data (BEA, Census, Federal Reserve)