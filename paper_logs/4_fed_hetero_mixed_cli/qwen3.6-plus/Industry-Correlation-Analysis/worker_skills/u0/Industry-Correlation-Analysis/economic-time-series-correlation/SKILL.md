---
name: economic-time-series-correlation
description: Correlate detrended economic time series (e.g., business cycles). Use when analyzing cyclical relationships between macroeconomic variables, deflating nominal values, applying HP filter, handling messy year markers from statistical tables (BEA, Census, etc.), working with panel data in long format, processing wide-format matrices where years are columns, handling quarterly update sheets with version/status filtering, resolving series aliases, deduplicating rows by priority, or routing monthly updates via a selector workbook that maps each month to a specific source file and version.
---

# Economic Time Series Correlation

Analyze correlations between detrended economic variables through deflation, HP filtering, and cyclical component extraction.

## Workflow

1. **Read Catalog/Mapping**: Many tasks provide a CSV mapping series names to column codes and deflator columns. Read it first to identify which columns to extract.
2. **Read Alias Map**: If a `series_aliases.csv` (or similar) is provided, load it to resolve multiple naming variants to canonical series names.
3. **Read Data**: Use `python3` and `pandas` or `openpyxl` to read Excel/CSV files. Do not rely on `read_file` for binary spreadsheets.
4. **Inspect raw year markers**: Before parsing, print unique values from the year column. Pandas often infers mixed numeric/string columns as `object` (strings). Always `.astype(str)` before parsing.
5. **Parse Time Markers**: Handle mixed annual/quarterly markers (e.g., `"2025:I"`, `"II"`, `"III"` or `"2025 Q1"`, `"Q2"`, `"Q3"` or `"FY-1990"`). Average all quarterly values for the partial year into a single annual value.
6. **Deduplicate by Priority**: If multiple rows exist per (series, year) with a `priority` column, keep the row with the smallest priority value per group.
7. **Align series**: Merge datasets on year; verify identical length and year range after cleaning.
8. **Deflate**: Compute real series: `real = nominal / price_index` (confirm base year = 1.0 in price data). **Each series may use a different deflator column** — look up the correct deflator from the catalog/register for each series.
9. **Log Transform**: `log_real = np.log(real)`.
10. **HP Filter**: Apply Hodrick-Prescott filter. `statsmodels` returns `(cycle, trend)`. Use index `[0]` for the cyclical component.
11. **Correlate**: Compute Pearson correlation between the two cyclical components.
12. **Format Output**: Always use `f"{corr:.5f}"` to preserve trailing zeros when outputting 5 decimal places.

## HP Filter Lambda Values

- Annual data: λ = 100
- Quarterly data: λ = 1600
- Monthly data: λ = 14400 (Ravn-Uhlig adjustment: λ = 100 × frequency^4)

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

For the correlation output specifically, use `f"{corr:.5f}"` to preserve trailing zeros as required by the verifier.

## Anti-Patterns & Pitfalls

- **Python Command**: Use `python3`, not `python`.
- **Year Parsing**: Do not cast year columns directly to `int` without inspection; statistical tables commonly use `'1994.'` (trailing dot), `'FY-1990'` (fiscal year prefix), or quarterly markers which raise `ValueError`. Pandas reads mixed columns as strings.
- **Quarterly Parsing**: Do not assume partial-year rows are already annualized. Look for markers like `:I`, `II`, `III`, `IV` (Roman) or `Q1`, `Q2`, `Q3`, `Q4` (Arabic) and average them.
- **Monthly Data**: When monthly data must be annualized, average all 12 months (or available months) for that year. Do not sum or take the last month.
- **Blank Values in Monthly Data**: Some monthly update cells may be blank/NaN. Filter these out before averaging: `df['amount'].dropna()` or `df[df['amount'].notna()]`. Do not treat blank as zero.
- **Trailing Zeros**: `round(x, 5)` drops trailing zeros in Python. Use formatted strings `f"{x:.5f}"` for exact decimal output.
- **HP Filter on Nominal**: Always deflate and take log before applying HP filter. Never apply to raw nominal values.
- **HP Filter Return Order**: `hpfilter()` returns `(cycle, trend)`, NOT `(trend, cycle)`. Using `[1]` extracts the trend, which will produce a smooth, non-zero-mean series and incorrect correlations. Always use `[0]`.
- **HP Filter Parameter Name**: The parameter is `lamb`, NOT `lam`. `hpfilter(x, lamb=100)` is correct; `hpfilter(x, lam=100)` raises `TypeError`.
- **Wrong Import**: `scipy.signal.hp_filter` does NOT exist. Use `statsmodels.tsa.filters.hp_filter.hpfilter` instead.
- **Per-Series Deflators**: Do not assume all series share the same price index. Each series may have its own deflator column specified in the catalog/register.

## Data Filtering Patterns

Statistical agency Excel files often include multiple release statuses and period kinds:
- Filter by `release_status == 'final'`, `record_type == 'official'`, or `version == 'revised'` to use finalized data (avoid `prelim` or `memo` unless specified).
- Filter by `period_kind == 'annual'` to exclude quarterly/monthly breakdowns in annual tables.
- When combining annual historical data with partial-year updates, average the partial-year values to produce a single annual figure.

## Selector Workbook Pattern

Some tasks provide a selector workbook (e.g., `coldchain_update_selector.xlsx`) that routes each month to a specific source file and version:

### Structure
```
series_code, month, preferred_source, preferred_version
CC_STOR_25, 2025-01, A, city-release
CC_STOR_25, 2025-02, B, central-release
LM_PARCEL_25, 2025-01, B, central-release
...
```

### Usage Pattern
```python
selector = pd.read_excel('update_selector.xlsx', sheet_name='UseThese')
source_map = {'A': updates_a_df, 'B': updates_b_df}

def get_monthly_values(series_code, selector_df, source_map):
    amounts = []
    for _, row in selector_df.iterrows():
        if row['series_code'] != series_code:
            continue
        src_df = source_map[row['preferred_source']]
        match = src_df[
            (src_df['series_code'] == series_code) &
            (src_df['month'] == row['month']) &
            (src_df['version'] == row['preferred_version'])
        ]
        if len(match) > 0:
            val = match['amount'].values[0]
            if pd.notna(val):  # Skip blank/NaN values
                amounts.append(float(val))
    return np.mean(amounts) if amounts else None
```

## Alias Mapping Pattern

Some tasks provide a `series_aliases.csv` that maps multiple naming variants to canonical series names:

```csv
requested_series,accepted_alias
Merchant wholesale turnover,Merchant wholesale turnover
Merchant wholesale turnover,merchant-wholesale-turnover
Merchant wholesale turnover,merchant wholesale net turnover
Packaging converters shipments,Packaging converters shipments
Packaging converters shipments,packaging-plants shipments
```

### Usage Pattern
```python
aliases = pd.read_csv('series_aliases.csv')
alias_map = dict(zip(aliases['accepted_alias'], aliases['requested_series']))
df['canonical_series'] = df['target_alias'].map(alias_map)
```

## Priority-Based Deduplication

When multiple rows exist for the same (series, year) combination, a `priority` column indicates which value to use (smallest number = highest priority):

```python
# Keep the row with smallest priority per (series, year)
df_deduped = df.loc[df.groupby(['canonical_series', 'year'])['priority'].idxmin()]
```

## Catalog/Mapping File Pattern

Many tasks provide a CSV that maps human-readable series names to column codes and deflator columns:

```csv
requested_series,history_sheet,history_code,current_sheet,current_code,deflator_column
Freight brokerage revenue,AnnualSeries,BROKER_REV,QuarterlyUpdate,BR_REV_25,Transport_Services_Price_2025_Base
```

### Usage Pattern
```python
catalog = pd.read_csv('series_catalog.csv')
# Look up codes for each series
for _, row in catalog.iterrows():
    hist_code = row['history_code']
    curr_code = row['current_code']
    deflator_col = row['deflator_column']
    # Use these to extract the right columns from your data files
```

## Wide Matrix Format

Some statistical releases use a "wide" format where years are column headers and series are rows:

### Structure
```
series_name, status_flag, unit, 1991, 1992, ..., 2024
Series A, official, usd_bn, 52.71, 55.32, ..., 217.05
Series B, official, usd_bn, 39.11, 41.09, ..., 176.03
```

### Extraction Pattern
```python
# Filter for official/final rows
df_official = df[df['status_flag'] == 'official']

# Extract a single series
series_row = df_official[df_official['series_name'] == 'Target Series']

# Build year-value dict from column headers
years = [str(y) for y in range(1991, 2025)]
values = [float(series_row[y].values[0]) for y in years]
series_dict = dict(zip([int(y) for y in years], values))
```

### Combining with Monthly Updates
When a separate CSV provides partial-year monthly updates:
```python
# Filter official monthly data, average for the partial year
monthly_official = csv_df[csv_df['status_flag'] == 'official']
partial_year_avg = monthly_official[monthly_official['series_name'] == 'Target Series']['amount'].mean()

# Append to annual series
full_series = annual_values + [partial_year_avg]
```

## Validation

- Verify year parsing: Compare unique values before/after conversion; ensure no `NaN` years post-merge.
- Check deflation: Real values should be roughly same magnitude as nominal for base year.
- **Verify HP filter**: The cyclical component must oscillate around zero. Check `np.abs(cycle.mean()) < 1e-6`. If the mean is large or the series is monotonic, you extracted the trend instead of the cycle.
- **Quick HP verification**: Run `help(hpfilter)` or `hpfilter.__doc__` to confirm return order is `(cycle, trend)` before trusting your extraction.

## Correlation Methods

Two equivalent approaches for Pearson correlation:
```python
# Method 1: numpy
import numpy as np
corr = np.corrcoef(cycle1, cycle2)[0, 1]

# Method 2: scipy (returns r and p-value)
from scipy import stats
r, p_value = stats.pearsonr(cycle1, cycle2)
```

## Script Usage

- `scripts/hp_correlation.py` — Template for quarterly parsing, deflation, HP filtering, and formatted output. Adjust file paths and column names as needed.
- `scripts/parse_year_markers.py` — Reusable year marker parser. Import `parse_year_column` and `annualize_quarterly` functions, or run with `--test` to verify behavior.

## References

- `references/excel-year-parsing.md` - Common year marker formats in statistical agency data (BEA, Census, Federal Reserve)
- `references/series-catalog-pattern.md` - Mapping file patterns for series codes and deflators