---
name: economic-time-series-analysis
description: Analyze economic time series by deflating nominal values, extracting cyclical components via HP filter, and computing correlations. Use when tasks involve real vs nominal indicators, detrending, business cycle analysis, or cross-series correlation of macroeconomic data.
---

# Economic Time Series Analysis

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

If statsmodels unavailable, use manual implementation from `references/hp_filter_manual.py`.

## Standard Workflow

1. **Handle mixed-frequency data**: If quarterly data appears in annual series (e.g., "2025:I", "II", "III"), average them to get annual value.
2. **Clean year columns**: Strip trailing punctuation (`1992.` → `1992`). Normalize all indices to integer years.
3. **Convert nominal to real**: Divide by price index: `real = nominal / price_index`
4. **Log transform**: Apply `np.log()` to real values before HP filter
5. **Apply HP filter**: Use `lamb=100` for annual data, `lamb=1600` for quarterly
6. **Extract cyclical component**: The `cycle` output is the detrended series
7. **Compute correlation**: Use `pearsonr()` on cyclical components

## Lambda Values by Frequency

| Data Frequency | λ (lambda) |
|---------------|------------|
| Annual        | 100        |
| Quarterly     | 1600       |
| Monthly       | 14400      |

## Common Patterns

### Cleaning Year Columns
Year columns may contain trailing dots (e.g., `1992.`). Strip them before conversion:

```python
df['year'] = df['year_col'].astype(str).str.rstrip('.').astype(int)
```

### Averaging Quarterly Data (Roman Numeral Format)
When quarterly data appears as "2025:I", "II", "III", "IV" rows:

```python
# Identify quarterly rows by colon pattern
q_mask = df['year_col'].astype(str).str.contains(':', na=False)

# Extract year from first quarter row (e.g., "2025:I" -> 2025)
q_year = int(df.loc[q_mask, 'year_col'].iloc[0].split(':')[0])

# Average quarterly values
q_values = df.loc[q_mask, 'value_col'].values
annual_value = np.mean(q_values)

# Add to annual series
annual_df = df[~q_mask].copy()
annual_df['year'] = annual_df['year_col'].str.rstrip('.').astype(int)
annual_df = pd.concat([annual_df, pd.DataFrame({'year': [q_year], 'value': [annual_value]})])
```

### Real Value Conversion
```python
# Price index with base year (e.g., 2025=1.0)
real_series = nominal_series / price_index
```

## Anti-Patterns

- **Silent Index Misalignment**: Mixing string indices (`'1992.'`, `'2025:I'`) with integer indices (`1992`) causes NaN correlations. Always normalize to integer years first.
- **HP Filter Import**: `from statsmodels.tsa.filters import hpfilter` fails. Always use `from statsmodels.tsa.filters.hp_filter import hpfilter`.
- **HP Filter on Levels**: Apply HP filter to log-transformed real values, not raw levels.
- **Lambda Mismatch**: Use λ=100 for annual data (not 1600, which is for quarterly).
- **Mismatched Frequencies**: Aggregate quarterly to annual explicitly before filtering.
- **Deflation Base**: Verify the price index base year. If index is `1.0` in base year, divide directly.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Correlation NaN | Index misalignment (string vs int) | Normalize all year indices to integers |
| ImportError for hpfilter | Wrong import path | Use `statsmodels.tsa.filters.hp_filter import hpfilter` |
| statsmodels unavailable | Missing dependency | Use manual HP from `references/hp_filter_manual.py` |
| Correlation > 1 or < -1 | Data error or wrong series | Check real value calculation |
| Cyclical mean far from 0 | Wrong lambda or frequency | Verify λ matches data frequency |
| Mismatched series lengths | Different date ranges | Align series before HP filter |
| Answer rejected for format | Trailing newline or precision | Use `xxd` to verify exact bytes |

## Validation Checklist

- [ ] Series lengths match before correlation
- [ ] No NaN values in cyclical components
- [ ] Lambda matches data frequency
- [ ] Log transformation applied before HP filter
- [ ] Correlation computed on cycle component, not trend
- [ ] All year indices are integers (not strings)

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
- When quarterly data available for partial year, average quarters to synthesize annual value

## Helper Script

Use `scripts/hp_correlation.py` for a reusable implementation of cleaning, deflation, HP filtering, and correlation. Functions include:
- `clean_year_index()` — handles trailing dots and quarterly suffixes
- `deflate_series()` — converts nominal to real
- `run_hp_correlation()` — aligns, log-transforms, filters, and computes correlation

## References

- `references/hp_filter_manual.py` — Pure NumPy HP filter implementation when statsmodels unavailable