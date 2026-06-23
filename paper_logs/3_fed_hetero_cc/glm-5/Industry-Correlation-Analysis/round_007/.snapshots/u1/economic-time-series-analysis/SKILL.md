---
name: economic-time-series-analysis
description: Analyze economic time series by deflating nominal values, extracting cyclical components via HP filter, and computing correlations. Use when tasks involve real vs nominal indicators, detrending, business cycle analysis, or cross-series correlation of macroeconomic data. Also use when data contains mixed annual/quarterly/monthly frequencies requiring aggregation, wide/matrix-formatted data (years as columns), catalog files mapping series codes, alias files mapping variant names to canonical series, status flags (`release_status`, `status_flag`, `revision`, `version`) requiring filtering, or priority columns for deduplication.
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

## ⚠️ CRITICAL: Output Precision
**Never round, truncate, or format numeric outputs.** Verifiers check raw floats with tight tolerances (often 1e-4). Writing `0.99918` instead of `0.9991834270369953` will fail. Always write the exact Python float directly to the output file. Do NOT use `round()`, `f"{x:.Nf}"`, or `.toFixed()`.

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

1. **Read Alias/Catalog Files (if present)**: Check for `series_aliases.csv` (maps variant names to canonical series) or `series_catalog.csv` (maps series to codes/deflators). Read these first to identify correct column names and series mappings.
2. **Load & Inspect**: Read Excel/CSV files. Check column names, index formats, and data types.
3. **Filter by Status Flags**: Inspect for status columns (`release_status`, `status_flag`, `revision`, `version`, `record_type`) and filter appropriately (usually to `'final'`, `'official'`, or `'revised'`). See "Data Quality: Status Flags" below.
4. **Deduplicate by Priority**: If a `priority` column exists alongside status flags, keep the smallest priority value for duplicate entries (same series, same period).
5. **Handle Matrix vs Long-Form Data**: Excel files may have years as columns (matrix format) or as row values (long-form). Detect and reshape accordingly.
6. **Clean Index/Year Columns**: Strip trailing punctuation, fiscal year prefixes (e.g., `FY-1998` → `1998`), and quarterly suffixes. Convert all indices to numeric integers. Never mix string and integer indices.
7. **Aggregate Mixed Frequencies**: If quarterly/monthly data maps to the same year, aggregate to annual (mean or sum) before alignment.
8. **Deflate Nominal Series**: Convert nominal values to real terms: `Real = Nominal / (Price_Index / Base_Multiplier)`. Verify base year and check for zeros/NaNs.
9. **Align Series**: Ensure all series share the exact same integer year index. Drop or interpolate missing values. Verify `len(s1) == len(s2)`.
10. **Log Transform**: Apply `np.log()` to real values. HP filter must be applied to log-transformed series, not raw levels.
11. **Apply HP Filter**: Extract cyclical components.
    - **Correct Import**: `from statsmodels.tsa.filters.hp_filter import hpfilter`
    - **Usage**: `cycle, trend = hpfilter(log_series, lamb=100)` (use `100` for annual, `1600` for quarterly, `14400` for monthly).
    - **Return Order**: `hpfilter` returns `(cycle, trend)`. Do not index `[1]` or unpack incorrectly.
12. **Compute Correlation**: Use `scipy.stats.pearsonr` on aligned cyclical components.
13. **Verify & Output**: Check cycle properties, p-values, and write final metric with full precision.

## Lambda Values by Frequency

| Data Frequency | λ (lambda) |
|---------------|------------|
| Annual        | 100        |
| Quarterly     | 1600       |
| Monthly       | 14400      |

## Data Quality & Common Patterns

### Status Flags (generalized)

Many economic datasets contain duplicate entries for the same period with status flags. **Always inspect for status columns and filter appropriately.**

Common patterns:

| Column Name | Typical Values | Filter To |
|-------------|----------------|-----------|
| `release_status` | 'final', 'prelim' | 'final' |
| `status_flag` | 'official', 'memo' | 'official' |
| `revision` | 'revised', 'preliminary' | 'revised' |
| `version` | 'revised', 'prelim' | 'revised' |
| `record_type` | 'official', 'prelim' | 'official' |

```python
# Check for status flags - inspect unique values first
for col in df.columns:
    if any(x in col.lower() for x in ['status', 'release', 'revision', 'version', 'record']):
        print(f"{col}: {df[col].unique()}")

# Filter to authoritative data only
df_clean = df[df['record_type'] == 'official'].copy()
```

### Priority-Based Deduplication

When multiple records exist for the same series-period combination after status filtering, use the `priority` column to select the best record:

```python
# After filtering to official records, deduplicate by keeping smallest priority
df_clean = df_clean.sort_values('priority').groupby(['series_name', 'year']).first().reset_index()

# Verify no duplicate series-period entries remain
print(df_clean.groupby(['series_name', 'year']).size().max())  # Should be 1
```

**Warning**: Failing to deduplicate by priority can cause duplicate year entries, incorrect aggregation, and mismatched series lengths.

### Alias Mapping Files

When a `series_aliases.csv` or similar mapping file exists, use it to canonicalize variant series names:

```python
# Read alias mapping
aliases = pd.read_csv('series_aliases.csv')
# Columns typically: requested_series, accepted_alias

# Build mapping from alias to canonical name
alias_to_canonical = {}
for _, row in aliases.iterrows():
    alias_to_canonical[row['accepted_alias']] = row['requested_series']

# Apply mapping to data
df['canonical_series'] = df['target_alias'].map(alias_to_canonical)

# Verify all aliases mapped
unmapped = df[df['canonical_series'].isna()]['target_alias'].unique()
print(f"Unmapped aliases: {unmapped}")
```

### Catalog-Driven Data Extraction

When a `series_catalog.csv` or similar mapping file exists:

```python
# Read catalog to get code mappings
catalog = pd.read_csv('series_catalog.csv')
# Columns typically: requested_series, history_sheet, history_code, 
#                    current_sheet, current_code, deflator_column

# Extract codes for specific series
row = catalog[catalog['requested_series'] == 'Freight brokerage revenue'].iloc[0]
hist_code = row['history_code']      # e.g., 'BROKER_REV'
current_code = row['current_code']   # e.g., 'BR_REV_25'
deflator_col = row['deflator_column']  # e.g., 'Transport_Services_Price_2025_Base'
```

### Matrix-Formatted Excel Files (Years as Columns)

Some Excel files store time series as matrices with years as column headers:

```python
# Matrix format: series_name | 1991 | 1992 | 1993 | ...
# Detect: many numeric column names
year_cols = [c for c in df.columns if str(c).isdigit()]
if len(year_cols) > 5:  # Likely matrix format
    # Melt to long-form
    df_long = df.melt(
        id_vars=['series_name', 'status_flag'], 
        value_vars=year_cols,
        var_name='year', 
        value_name='value'
    )
    df_long['year'] = df_long['year'].astype(int)
```

### Monthly to Annual Aggregation

For high-frequency update sheets with monthly data:

```python
# Extract year from month column (e.g., '2025-06' -> 2025)
update_df['year'] = update_df['month'].str[:4].astype(int)

# Annualize by averaging
annualized = update_df.groupby(['series_label', 'year'])['amount'].mean().reset_index()
```

### Cleaning Year Columns

Year columns may contain various formats. Clean them systematically:

```python
# Handle FY-YYYY format (e.g., 'FY-1998' -> 1998)
df['year'] = df['year_col'].str.replace('FY-', '', regex=False).astype(int)

# Handle trailing dots (e.g., '1992.' -> 1992)
df['year'] = df['year_col'].astype(str).str.rstrip('.').astype(int)

# Handle combined formats
df['year'] = df['year_col'].astype(str).str.replace('FY-', '').str.rstrip('.').astype(int)
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

**Format 3: Hyphen-separated** (e.g., "2025-Q1", "2025-Q2", "2025-Q3")
```python
# Detect quarterly rows with YYYY-QN format
q_mask = df['subperiod'].astype(str).str.contains(r'\d{4}-Q[1-4]', na=False, regex=True)

# Filter to specific year and average
q_year = 2025
q_values = df.loc[q_mask & (df['subperiod'].str[:4].astype(int) == q_year), 'value'].values
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
- **Ignoring Status Flags**: Failing to filter status columns creates duplicate year entries and corrupts analysis. Check for `release_status`, `status_flag`, `revision`, `version`, `record_type`, etc.
- **Ignoring Priority Columns**: After status filtering, duplicates may remain. Always check for and apply priority-based deduplication.
- **Matrix Format Assumption**: Assuming all Excel files are long-form. Check for matrix format (years as columns) and reshape with `melt()`.
- **HP Filter Import**: `from statsmodels.tsa.filters import hpfilter` fails. Always use `from statsmodels.tsa.filters.hp_filter import hpfilter`.
- **HP Filter on Levels**: Apply HP filter to log-transformed real values, not raw levels. `cycle = hpfilter(np.log(real_series))` is correct.
- **HP Filter Return Order**: `hpfilter` returns `(cycle, trend)`. Unpacking as `trend, cycle = ...` or taking index `[1]` yields the trend, not the cycle.
- **Lambda Mismatch**: Use λ=100 for annual data (not 1600, which is for quarterly). Wrong lambda produces invalid cyclical decomposition.
- **Mismatched Frequencies**: Annual vs quarterly data must be aligned. Aggregate quarterly to annual explicitly before filtering.
- **Deflation Base**: Verify the price index base year. If the index is `1.0` in the base year, divide directly. If it's `100`, divide by `index/100`.
- **Partial Quarterly Capture**: When averaging quarterly data for annual synthesis, ensure ALL quarters (Q1-Q4, or available Q1-Q3) are captured. Do not stop at Q1. Verify by printing the count of quarterly values found.
- **Price Index Zeros**: Price indices may have zeros for missing years. Check and handle before deflation.
- **Trend-vs-Cycle Correlation Trap**: If the computed correlation is suspiciously high (>0.99) for detrended cycles, you likely correlated the trends instead. Always verify cycle properties before trusting the correlation.
- **Rounding Output**: Rounding to N decimals for "readability" causes verifier failure. Always pass raw floats.
- **Unmapped Aliases**: Failing to apply alias mapping can leave series unmatched. Always verify all aliases are mapped after applying the mapping file.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Correlation NaN | Index misalignment (string vs int) | Normalize all year indices to integers |
| Duplicate year errors in pivot | Status flags not filtered | Filter status column before pivoting |
| Duplicate year errors after status filter | Priority column not applied | Deduplicate by keeping smallest priority value |
| Unmapped series names | No alias mapping applied | Check for `series_aliases.csv` and apply mapping |
| ImportError for hpfilter | Wrong import path | Use `statsmodels.tsa.filters.hp_filter import hpfilter` |
| statsmodels unavailable | Missing dependency | Use manual HP from `references/hp_filter_manual.py` |
| Correlation > 1 or < -1 | Data error or wrong series | Check real value calculation |
| Cyclical mean far from 0 | Wrong lambda or frequency | Verify λ matches data frequency |
| Mismatched series lengths | Different date ranges or duplicate entries | Align series, check for status flags and priority, verify `groupby().size()` |
| Answer rejected for format | Trailing newline or precision | Use `xxd` to verify exact bytes |
| 2025 value seems low | Only Q1 captured, not all quarters | Check quarterly row detection captures Q1-Q4 |
| Cycle looks like trend | Unpacked in wrong order | Verify `cycle, trend = hpfilter(...)` and check return order |
| Division by zero in deflation | Price index has zeros | Check price index for missing values before dividing |
| Suspiciously high correlation (>0.99) | Correlated trends instead of cycles | Verify cycle extraction; check trend+cycle reconstruction |
| Empty series after filter | Wrong status column name | Check for `status_flag`, `release_status`, `revision`, `version`, `record_type` variants |
| Cannot find series code | No catalog read | Check for `series_catalog.csv` or similar mapping file |

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

- [ ] Checked for alias file (`series_aliases.csv`) and applied canonical name mapping
- [ ] Verified all aliases mapped (no unmapped series names)
- [ ] Checked for catalog file (`series_catalog.csv`) and extracted correct codes
- [ ] Checked for status flags (`release_status`, `status_flag`, `revision`, `version`, `record_type`, etc.) and filtered appropriately
- [ ] Status column name verified (`status_flag` vs `release_status` vs `revision` vs `version` vs `record_type`)
- [ ] Checked for priority column and deduplicated by keeping smallest priority
- [ ] No duplicate year entries after status+priority filtering (verify with `groupby().size()`)
- [ ] Matrix-formatted data detected and reshaped if needed
- [ ] Wide format data melted to long format if years were columns
- [ ] Year columns cleaned (FY-YYYY format, trailing dots, etc.)
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
- Check for `series_aliases.csv` to map variant names to canonical series names
- Check for `series_catalog.csv` to map series codes
- Check for status columns (`release_status`, `status_flag`, `revision`, `version`, `record_type`); filter to authoritative values ('final', 'official', 'revised')
- Check for priority column and deduplicate by keeping smallest priority value
- Detect matrix-formatted Excel (years as columns) vs long-form data
- Clean year columns that may contain FY- prefix, trailing dots, or quarterly suffixes
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