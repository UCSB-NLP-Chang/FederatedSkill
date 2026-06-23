---
name: economic-time-series-analysis
description: Analyze economic time series by deflating nominal values, extracting cyclical components via HP filter, and computing correlations. Use when tasks involve real vs nominal indicators, detrending, business cycle analysis, or cross-series correlation of macroeconomic data. Also use when data contains mixed annual/quarterly frequencies requiring aggregation.
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

1. **Load & Inspect**: Read Excel/CSV files. Check column names, index formats, and data types.
2. **Clean Index/Year Columns**: Strip trailing punctuation (e.g., `1994.` -> `1994`). Handle quarterly markers (`2025:I`, `2025 Q1`) by extracting the base year. Convert all indices to numeric integers.
3. **Aggregate Mixed Frequencies**: If quarterly data maps to the same year, aggregate to annual (mean or sum) before alignment. Never mix string and integer indices.
4. **Deflate Nominal Series**: Convert nominal values to real terms using a price index: `Real = Nominal / (Price_Index / Base_Multiplier)`. Verify the index base (e.g., 1.0 or 100).
5. **Align Series**: Ensure all series share the exact same integer year index. Drop or interpolate missing values. Verify `len(s1) == len(s2)`.
6. **Log Transform**: Apply `np.log()` to real values. HP filter must be applied to log-transformed series, not raw levels.
7. **Apply HP Filter**: Extract cyclical components.
   - **Correct Import**: `from statsmodels.tsa.filters.hp_filter import hpfilter`
   - **Usage**: `cycle, trend = hpfilter(log_series, lamb=100)` (use `100` for annual, `1600` for quarterly, `14400` for monthly).
   - **Return Order**: `hpfilter` returns `(cycle, trend)`. Do not index `[1]` or unpack incorrectly.
8. **Compute Correlation**: Use `scipy.stats.pearsonr` on the aligned cyclical components.
9. **Verify & Output**: Check p-values, ensure series lengths match, and write the final metric.

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

### Averaging Quarterly Data

**Format 1: Roman numerals with colon** (e.g., "2025:I", "II", "III", "IV")
```python
q_mask = df['year_col'].astype(str).str.contains(':', na=False)
q_year = int(df.loc[q_mask, 'year_col'].iloc[0].split(':')[0])
q_values = df.loc[q_mask, 'value_col'].values
annual_value = np.mean(q_values)
```

**Format 2: Q-prefix format** (e.g., "2025 Q1", "Q2", "Q3", "Q4")
```python
# Detect quarterly rows - look for Q1-Q4 patterns
q_mask = df['year_col'].astype(str).str.contains(r'Q[1-4]', na=False, regex=True)

# Extract year from first quarter row (e.g., "2025 Q1" -> 2025)
q_year = int(df.loc[q_mask, 'year_col'].iloc[0].split()[0])

# Average all available quarterly values
q_values = df.loc[q_mask, 'value_col'].astype(float).values
annual_value = np.mean(q_values)
```

*Combine into annual series*:
```python
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

- **Silent Index Misalignment**: Mixing string indices (`'1992.'`, `'2025:I'`) with integer indices (`1992`) causes `pd.concat` to produce NaNs. Always normalize to integer years first.
- **HP Filter Import**: `from statsmodels.tsa.filters import hpfilter` fails. Always use `from statsmodels.tsa.filters.hp_filter import hpfilter`.
- **HP Filter on Levels**: Apply HP filter to log-transformed real values, not raw levels. `cycle = hpfilter(np.log(real_series))` is correct.
- **HP Filter Return Order**: `hpfilter` returns `(cycle, trend)`. Unpacking as `trend, cycle = ...` or taking index `[1]` yields the trend, not the cycle.
- **Lambda Mismatch**: Use λ=100 for annual data (not 1600, which is for quarterly). Wrong lambda produces invalid cyclical decomposition.
- **Mismatched Frequencies**: Annual vs quarterly data must be aligned. Aggregate quarterly to annual explicitly before filtering.
- **Deflation Base**: Verify the price index base year. If the index is `1.0` in the base year, divide directly. If it's `100`, divide by `index/100`.
- **Partial Quarterly Capture**: When averaging quarterly data for annual synthesis, ensure ALL quarters (Q1-Q4, or Q1-Q3 for partial years) are captured. Do not stop at Q1. Verify by printing the count of quarterly values found.

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
| 2025 value seems low | Only Q1 captured, not all quarters | Check quarterly row detection captures Q1-Q4 |
| Cycle looks like trend | Unpacked in wrong order | Verify `cycle, trend = hpfilter(...)` and check return order |

## Validation Checklist

- [ ] Series lengths match before correlation
- [ ] No NaN values in cyclical components
- [ ] Lambda matches data frequency
- [ ] Log transformation applied before HP filter
- [ ] Correlation computed on cycle component, not trend
- [ ] All year indices are integers (not strings)
- [ ] When synthesizing annual from quarterly: all quarters averaged, not just Q1
- [ ] **Cycle Sum Check**: `abs(np.sum(cycle)) < 1e-6`. A large sum indicates you extracted the trend instead of the cycle.

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
- **Critical**: When detecting quarterly rows, verify you capture ALL quarters (Q1-Q4 or available Q1-Q3), not just the first one. Print quarterly values for verification.

## Helper Script

Use `scripts/hp_correlation.py` for a reusable implementation of cleaning, deflation, HP filtering, and correlation. Functions include:
- `clean_year_index()` — handles trailing dots and quarterly suffixes
- `deflate_series()` — converts nominal to real
- `run_hp_correlation()` — aligns, log-transforms, filters, and computes correlation

## References

- `references/hp_filter_manual.py` — Pure NumPy HP filter implementation when statsmodels unavailable
- `references/quarterly_aggregation_patterns.md` — Detailed patterns for handling mixed-frequency data
