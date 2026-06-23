---
name: economic-time-series-analysis
description: Analyze economic time series by deflating nominal values, extracting cyclical components via HP filter, and computing correlations. Use when tasks involve real vs nominal indicators, detrending, business cycle analysis, or cross-series correlation of macroeconomic data. Also use when data contains mixed annual/quarterly/monthly frequencies requiring aggregation, or when data has duplicate entries with status flags (final/prelim) that need filtering.
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
2. **Handle Status Flags**: If data contains `release_status` or similar flags with values like 'final'/'prelim', **filter to 'final' only** to avoid duplicate year entries. See "Data Quality: Status Flags" below.
3. **Clean Index/Year Columns**: Strip trailing punctuation (e.g., `1994.` -> `1994`). Handle quarterly markers (`2025:I`, `2025 Q1`) by extracting the base year. Convert all indices to numeric integers.
4. **Aggregate Mixed Frequencies**: If quarterly/monthly data maps to the same year, aggregate to annual (mean or sum) before alignment. Never mix string and integer indices.
5. **Deflate Nominal Series**: Convert nominal values to real terms using a price index: `Real = Nominal / (Price_Index / Base_Multiplier)`. Verify the index base (e.g., 1.0 or 100).
6. **Align Series**: Ensure all series share the exact same integer year index. Drop or interpolate missing values. Verify `len(s1) == len(s2)`.
7. **Log Transform**: Apply `np.log()` to real values. HP filter must be applied to log-transformed series, not raw levels.
8. **Apply HP Filter**: Extract cyclical components.
   - **Correct Import**: `from statsmodels.tsa.filters.hp_filter import hpfilter`
   - **Usage**: `cycle, trend = hpfilter(log_series, lamb=100)` (use `100` for annual, `1600` for quarterly, `14400` for monthly).
   - **Return Order**: `hpfilter` returns `(cycle, trend)`. Do not index `[1]` or unpack incorrectly.
9. **Compute Correlation**: Use `scipy.stats.pearsonr` on the aligned cyclical components.
10. **Verify & Output**: Check p-values, ensure series lengths match, and write the final metric.

## Lambda Values by Frequency

| Data Frequency | λ (lambda) |
|---------------|------------|
| Annual        | 100        |
| Quarterly     | 1600       |
| Monthly       | 14400      |

## Data Quality Patterns

### Status Flags (final/prelim)

Many economic datasets contain duplicate entries for the same period with status flags. **Always inspect for status columns and filter appropriately.**

```python
# Check for status flags
print(df['release_status'].unique())  # Often: ['final', 'prelim']

# Filter to final only to avoid duplicates
df_clean = df[df['release_status'] == 'final'].copy()

# Verify no duplicate years remain
print(df_clean.groupby('period_label').size())  # Should all be 1
```

**Warning**: Failing to filter by status can cause:
- Duplicate year entries breaking pivot operations
- Incorrect aggregation (averaging final and prelim values)
- Mismatched series lengths after alignment

### Monthly to Annual Aggregation

For high-frequency update sheets with monthly data:

```python
# Extract year from month column (e.g., '2025-06' -> 2025)
update_df['year'] = update_df['month'].str[:4].astype(int)

# Annualize by averaging
annualized = update_df.groupby(['series_label', 'year'])['amount'].mean().reset_index()
```

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
# Check for zeros/NaNs in price index before dividing
price_idx = price_index.reindex(year_range, method='ffill')
price_idx = price_idx.replace(0, np.nan).dropna()  # Handle missing values

real_series = nominal_series / price_index
```

### Merging Multiple Data Sources
When combining historical panel data with recent updates:

```python
# Historical data (e.g., 1995-2024)
historical = panel_final[panel_final['year'] <= 2024]

# Recent update (e.g., 2025 monthly -> annual average)
recent_annual = recent_df.groupby('year')['amount'].mean().reset_index()

# Combine
full_series = pd.concat([historical, recent_annual]).sort_values('year')
```

## Anti-Patterns

- **Silent Index Misalignment**: Mixing string indices (`'1992.'`, `'2025:I'`) with integer indices (`1992`) causes `pd.concat` to produce NaNs. Always normalize to integer years first.
- **Ignoring Status Flags**: Failing to filter `release_status` to 'final' creates duplicate year entries and corrupts analysis.
- **HP Filter Import**: `from statsmodels.tsa.filters import hpfilter` fails. Always use `from statsmodels.tsa.filters.hp_filter import hpfilter`.
- **HP Filter on Levels**: Apply HP filter to log-transformed real values, not raw levels. `cycle = hpfilter(np.log(real_series))` is correct.
- **HP Filter Return Order**: `hpfilter` returns `(cycle, trend)`. Unpacking as `trend, cycle = ...` or taking index `[1]` yields the trend, not the cycle.
- **Lambda Mismatch**: Use λ=100 for annual data (not 1600, which is for quarterly). Wrong lambda produces invalid cyclical decomposition.
- **Mismatched Frequencies**: Annual vs quarterly data must be aligned. Aggregate quarterly to annual explicitly before filtering.
- **Deflation Base**: Verify the price index base year. If the index is `1.0` in the base year, divide directly. If it's `100`, divide by `index/100`.
- **Partial Quarterly Capture**: When averaging quarterly data for annual synthesis, ensure ALL quarters (Q1-Q4, or Q1-Q3 for partial years) are captured. Do not stop at Q1. Verify by printing the count of quarterly values found.
- **Trend-vs-Cycle Correlation Trap**: If the computed correlation is suspiciously high (>0.99) for detrended cycles, you likely correlated the trends instead. Always verify cycle properties before trusting the correlation.
- **Price Index Zeros**: Price indices may have zeros for missing years. Check and handle before deflation.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Correlation NaN | Index misalignment (string vs int) | Normalize all year indices to integers |
| Duplicate year errors in pivot | Status flags not filtered | Filter to `release_status == 'final'` before pivoting |
| ImportError for hpfilter | Wrong import path | Use `statsmodels.tsa.filters.hp_filter import hpfilter` |
| statsmodels unavailable | Missing dependency | Use manual HP from `references/hp_filter_manual.py` |
| Correlation > 1 or < -1 | Data error or wrong series | Check real value calculation |
| Cyclical mean far from 0 | Wrong lambda or frequency | Verify λ matches data frequency |
| Mismatched series lengths | Different date ranges or duplicate entries | Align series, check for status flags, verify `groupby().size()` |
| Answer rejected for format | Trailing newline or precision | Use `xxd` to verify exact bytes |
| 2025 value seems low | Only Q1 captured, not all quarters | Check quarterly row detection captures Q1-Q4 |
| Cycle looks like trend | Unpacked in wrong order | Verify `cycle, trend = hpfilter(...)` and check return order |
| Division by zero in deflation | Price index has zeros | Check price index for missing values before dividing |
| Inconsistent results | Mixed final/prelim data | Filter for `release_status == 'final'` |

## Validation Steps

After HP filtering, run these explicit checks to verify correct extraction:

```python
# 1. Print head/tail of cleaned series before filtering
print(log_series.head())
print(log_series.tail())

# 2. Cycle Mean Check: Mean should be approximately zero
assert abs(np.mean(cycle)) < 1e-6, f"Cycle mean {np.mean(cycle)} not near zero - may have extracted trend instead"

# 3. Reconstruction Check: trend + cycle should equal original log series
assert np.allclose(trend + cycle, log_series), "Reconstruction failed - filter output may be wrong"

# 4. Length and index alignment
assert len(cycle1) == len(cycle2), f"Length mismatch: {len(cycle1)} vs {len(cycle2)}"
assert cycle1.index.equals(cycle2.index), "Indices not aligned"

# 5. Check p-value for statistical significance
print(f"Correlation: {corr:.6f}, p-value: {pvalue:.6f}")

# 6. If correlation is NaN, immediately inspect index types
if np.isnan(corr):
    print("Index types:", type(cycle1.index[0]), type(cycle2.index[0]))
```

## Validation Checklist

- [ ] Checked for status flags (`release_status`, `revision`, etc.) and filtered appropriately
- [ ] No duplicate year entries after status filtering (verify with `groupby().size()`)
- [ ] Series lengths match before correlation
- [ ] No NaN values in cyclical components
- [ ] Lambda matches data frequency
- [ ] Log transformation applied before HP filter
- [ ] Correlation computed on cycle component, not trend
- [ ] All year indices are integers (not strings)
- [ ] When synthesizing annual from quarterly: all quarters averaged, not just Q1
- [ ] Cycle mean near zero (abs(np.mean(cycle)) < 1e-6)
- [ ] Reconstruction passes (trend + cycle ≈ log_series)
- [ ] Price index checked for zeros before deflation

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### economic-hp-correlation
- Check for `release_status` or similar status columns; filter to 'final' to avoid duplicates
- Clean year columns that may contain trailing dots (e.g., `1994.` → `1994`)
- Price index base year typically equals 1.0; verify before dividing; check for zeros
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