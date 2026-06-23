---
name: economic-time-series-correlation
description: Calculate correlations between detrended economic time series. Use when tasked with analyzing relationships between consumption categories, capital expenditure types, service demand, housing construction data, network services, cold chain logistics, or macroeconomic indicators that require inflation adjustment, trend removal (HP filtering), and correlation computation. Applies to hospitality, travel, retail, industrial equipment, software investment, media broadcasting, advertising revenue, residential renovation, building materials, utilities, telecom, logistics, warehousing, wholesale distribution, packaging, cold storage, last-mile delivery, and other sectoral spending analysis. Trigger when you see .xlsx files with year markers, price deflators, and correlation tasks. Handles wide-format matrices (years as columns), long-format panels, CSV update files with monthly data, catalog-mapped multi-file structures, alias-mapped data with priority-based deduplication, and selector-mapped data with multi-source monthly updates.
---

# Economic Time Series Correlation Analysis

Analyze correlations between economic time series after deflation and detrending.

## Quick Workflow

1. **Inspect data structure with Python** — Excel files cannot be read directly; use `pandas.read_excel()`
2. **Identify data layout** — wide matrix vs long panel vs hybrid vs catalog-mapped vs alias-mapped vs selector-mapped (see Data Layout Detection)
3. **Filter by status** — apply `release_status`, `status_flag`, `version`, `record_type`, or `status_bucket` filters
4. **Handle deduplication** — check for `priority` column and keep minimum value when duplicates exist
5. **Handle multi-source selection** — check for selector workbooks specifying source file and version per observation
6. **Extract series and years** — handle years-as-columns or years-as-rows (including FY-prefixed labels)
7. **Incorporate update data** — annualize monthly/quarterly data if present, respecting selector rules when provided
8. **Deflate, log-transform, HP filter (λ=100), compute correlation**
9. **Write only the numeric result** to answer file

## Data Layout Detection

| Pattern | Structure | Indicators | Handling |
|---------|-----------|------------|----------|
| Wide matrix | Years as columns | Columns like `'1991'`, `'1992'`, `series_name` row-wise | Melt or select column ranges |
| Long panel | Years as rows, series labels | `series_label`, `period_label`, `release_status` | Filter by status, pivot if needed |
| Hybrid | Matrix + CSV update | `.xlsx` matrix + `.csv` monthly update | Combine annual matrix with averaged monthly |
| Catalog-mapped | Multiple files via mapping | `series_catalog.csv`, `history_code`, `current_code` | Read catalog first, map codes to files |
| Alias-mapped | Alias file with priority dedup | `series_aliases.csv`, `target_alias`, `record_type`, `priority` | Match aliases case-insensitively, filter by `official`, keep min `priority` |
| Selector-mapped | Selector specifies source/version | `*_selector.xlsx` with `preferred_source`, `preferred_version`, `month` | Use selector to choose between multiple update files |

**Decision rule**: Check `df.columns`. If year-like strings ( `'1991'`, `'1992'` ) appear as column names → wide matrix. If `series_label` or `status_flag`/`release_status` columns present → long panel. If `series_catalog.csv` exists → catalog-mapped. If `series_aliases.csv` exists with `target_alias` and `priority` columns → alias-mapped. If selector file exists with `preferred_source`/`preferred_version` columns → selector-mapped.

## Status/Version Filter Handling

Filter to final/official/revised/benchmark data before processing:

```python
# Check for status_bucket (wide matrix pattern with benchmark/memo)
if 'status_bucket' in df.columns:
    df = df[df['status_bucket'] == 'benchmark']  # exclude 'memo'
# Check for version column first (catalog-mapped pattern)
elif 'version' in df.columns:
    df = df[df['version'] == 'revised']  # exclude 'prelim', 'draft-release', etc.
# Check for record_type (alias-mapped pattern)
elif 'record_type' in df.columns:
    df = df[df['record_type'] == 'official']
# Check for preferred_version (selector-mapped pattern)
elif 'preferred_version' in selector_df.columns:
    # Use selector to choose specific version from source
    pass
# Then check standard status columns
elif 'release_status' in df.columns:
    df = df[df['release_status'] == 'final']
elif 'status_flag' in df.columns:
    df = df[df['status_flag'] == 'official']
```

**Decision rule**: Check for `status_bucket` first in wide matrix files. Check for `version` (`revised`/`prelim`/`draft-release`/`city-release`/`central-release`) in current/quarterly files. Check for `record_type` (`official`/`memo`) in alias-mapped files. Check for `preferred_version` in selector-mapped files. Use `release_status`/`status_flag` for historical releases.

## Priority-Based Deduplication (Alias-Mapped Pattern)

When `priority` column exists alongside duplicates:

```python
# After filtering to official records, deduplicate by keeping lowest priority
for series in series_list:
    series_df = official_df[official_df['target_alias'].str.lower().isin(aliases[series])]
    # If duplicates exist, keep row with smallest priority
    if series_df.duplicated(subset=['year_label']).any():
        series_df = series_df.loc[series_df.groupby('year_label')['priority'].idxmin()]
```

## Selector-Mapped Multi-Source Pattern

When a selector workbook specifies which source file and version to use for each month:

```python
# Read selector that specifies source and version per month
selector = pd.read_excel('/root/coldchain_update_selector.xlsx', sheet_name='UseThese')
# Columns: series_code, month, preferred_source, preferred_version
# preferred_source: 'A' or 'B' (maps to updates_a.csv vs updates_b.csv)
# preferred_version: 'city-release', 'central-release', 'draft-release', etc.

# Read both update files
updates_a = pd.read_csv('/root/coldchain_updates_a.csv')
updates_b = pd.read_csv('/root/coldchain_updates_b.csv')

# For each row in selector, pick matching observation from correct source
results = []
for _, row in selector.iterrows():
    source_df = updates_a if row['preferred_source'] == 'A' else updates_b
    match = source_df[
        (source_df['series_code'] == row['series_code']) &
        (source_df['month'] == row['month']) &
        (source_df['version'] == row['preferred_version'])
    ]
    if len(match) > 0 and not pd.isna(match['amount'].iloc[0]):
        results.append(match['amount'].iloc[0])

# Annualize by averaging valid monthly values
annual_value = np.mean(results)
```

**Critical checks**:
- Verify `preferred_source` column values match file naming (A→updates_a, B→updates_b)
- Verify `preferred_version` values exist in the source files (e.g., 'city-release', 'central-release', 'draft-release')
- Handle blank/missing amounts by excluding them from the average
- Annualize only over valid (non-null) months

See `references/selector_mapped_example.md` for complete walkthrough.

## Column Name Detection

| Data Type | Common Value Column | Year Column |
|-----------|---------------------|-------------|
| Capital expenditure | `Private total` | `Year marker` |
| Media/broadcasting | `Domestic total` | `Period label` |
| Service industries | `Total`, `Value` | `Year`, `Period` |
| Panel data (housing) | `amount` | `period_label` |
| Wide matrix | Year columns directly | Column names like `'1991'`, `'1992'` |
| Wide matrix (cold chain) | Year columns, `status_bucket` | `series_code` identifies series |
| Catalog-mapped history | Column from `history_code` | `calendar_year` |
| Catalog-mapped current | `value` | `subperiod` |
| Alias-mapped | `amount` | `year_label` (may have FY prefix) |
| Selector-mapped | `amount` | `month` (YYYY-MM) |

**Decision rule**: List columns with `df.columns.tolist()` first. For selector-mapped data, parse year from `month` column using `str[:4]` or `str.split('-')[0]`.

## Catalog-Mapped Data Handling

When `series_catalog.csv` (or `*_register.csv`) maps codes across files:

```python
# Read catalog/register first
catalog = pd.read_csv('/root/series_register.csv')

# Extract mapping for each series
info = catalog[catalog['requested_series'] == 'Target Series'].iloc[0]

# Read historical using history_code (may need status_bucket filter)
hist = pd.read_excel('/root/archive.xlsx', sheet_name='HistoryMatrix')
hist_benchmark = hist[hist['status_bucket'] == 'benchmark']
series_hist = hist_benchmark[hist_benchmark['series_code'] == info['history_code']]

# Read current updates, filter by version
updates = pd.read_csv('/root/updates.csv')
updates_filtered = updates[updates['version'] == 'revised']
series_curr = updates_filtered[updates_filtered['series_code'] == info['current_code']]

# Apply series-specific deflator
prices = pd.read_excel('/root/price_book.xlsx', sheet_name='Indices')
deflator_col = info['deflator_column']
```

See `references/catalog_mapped_example.md` for complete walkthrough.

## Wide Matrix Format with Status Filter

When years are columns and `status_bucket` identifies valid rows:

```python
# Filter to benchmark status (exclude memo rows)
benchmark_df = df[df['status_bucket'] == 'benchmark']

# Identify year columns programmatically
year_cols = [c for c in df.columns if c.isdigit() and len(c) == 4]
year_cols = [c for c in year_cols if 1990 <= int(c) <= 2030]  # sanity filter

# Extract series by row filtering on series_code
series_a = benchmark_df[benchmark_df['series_code'] == 'CODE_A']
values_a = series_a[year_cols].values[0]
```

## Detailed Steps

### 1. Load Data

```python
import pandas as pd
df = pd.read_excel("/root/data.xlsx")
print(df.columns.tolist())
print(df.head(10))
print(df.tail(10))

# Check for catalog, aliases, selector, and CSV updates
import glob
csv_files = glob.glob('/root/*.csv')
xlsx_files = glob.glob('/root/*.xlsx')
for f in csv_files:
    print(f"CSV: {f}")
    print(pd.read_csv(f).head())
for f in xlsx_files:
    print(f"XLSX: {f}")
    try:
        xl = pd.ExcelFile(f)
        print(f"  Sheets: {xl.sheet_names}")
    except:
        pass
```

### 2. Detect Layout and Filter

```python
# Detect wide matrix (years as columns)
year_cols = [c for c in df.columns if c.isdigit() and len(c) == 4]
if year_cols and 1990 <= int(year_cols[0]) <= 2030:
    layout = 'wide_matrix'
else:
    layout = 'long_panel'

# Check for alias file
if any('alias' in f.lower() for f in csv_files):
    layout = 'alias_mapped'

# Check for selector file
if any('selector' in f.lower() for f in xlsx_files):
    layout = 'selector_mapped'

# Filter by version/status/record_type/status_bucket if present
if 'status_bucket' in df.columns:
    df = df[df['status_bucket'] == 'benchmark']
elif 'version' in df.columns:
    df = df[df['version'] == 'revised']
elif 'record_type' in df.columns:
    df = df[df['record_type'] == 'official']
elif 'release_status' in df.columns:
    df = df[df['release_status'].isin(['final', 'official'])]
elif 'status_flag' in df.columns:
    df = df[df['status_flag'] == 'official']
```

### 3. Extract Series

**Selector-mapped (multi-source monthly):**
```python
# Parse selector to choose source file and version per month
def get_selector_annual(selector_df, updates_a, updates_b, series_code):
    sel = selector_df[selector_df['series_code'] == series_code]
    values = []
    for _, row in sel.iterrows():
        source_df = updates_a if row['preferred_source'] == 'A' else updates_b
        match = source_df[
            (source_df['series_code'] == row['series_code']) &
            (source_df['month'] == row['month']) &
            (source_df['version'] == row['preferred_version'])
        ]
        if len(match) > 0 and not pd.isna(match['amount'].iloc[0]):
            values.append(match['amount'].iloc[0])
    return np.mean(values) if values else np.nan
```

**Catalog-mapped:**
```python
# Extract historical using series_code from register
benchmark_df = archive_df[archive_df['status_bucket'] == 'benchmark']
series_hist = benchmark_df[benchmark_df['series_code'] == info['history_code']]
# Extract year columns
year_cols = [c for c in archive_df.columns if c.isdigit() and len(c) == 4]
years = [int(y) for y in year_cols]
values = series_hist[year_cols].values[0]
```

**Wide matrix:**
```python
def extract_wide_series(df, series_name, year_cols, status_col='status_flag'):
    if status_col in df.columns:
        df = df[df[status_col] == 'official']
    row = df[df['series_name'] == series_name]
    values = row[year_cols].values[0]
    years = [int(y) for y in year_cols]
    return pd.DataFrame({'year': years, 'amount': values})
```

**Long panel:**
```python
def extract_panel_series(df, series_label):
    sub = df[df['series_label'] == series_label][['period_label', 'amount']]
    sub.columns = ['year', 'amount']
    return sub
```

### 4. Handle Update Data (Monthly/Quarterly → Annual)

```python
# Standard averaging for single source
update_df = pd.read_csv('/root/update_2025.csv')
update_df['year'] = update_df['period'].str[:4].astype(int)
annual_2025 = update_df.groupby('series_name')['amount'].mean().reset_index()

# Selector-matched multi-source (see above)
# Average only valid (non-null) observations, exclude missing months
```

### 5. Align and Deflate

```python
# Merge series on year
merged = pd.merge(series_a, series_b, on='year', suffixes=('_a', '_b'))
merged = pd.merge(merged, deflator, on='year')

# Deflate: divide nominal by price index
merged['real_a'] = merged['amount_a'] / merged['price_index']
merged['real_b'] = merged['amount_b'] / merged['price_index']
```

### 6. Detrend with HP Filter

```python
from statsmodels.tsa.filters.hp_filter import hpfilter
import numpy as np

# Log transform first (standard for economic series)
log_a = np.log(merged['real_a'])
log_b = np.log(merged['real_b'])

# HP filter: λ=100 for annual data (NOT 1600—that's for quarterly)
cycle_a, trend_a = hpfilter(log_a, lamb=100)
cycle_b, trend_b = hpfilter(log_b, lamb=100)
```

### 7. Compute and Output Correlation

```python
from scipy.stats import pearsonr

corr, pval = pearsonr(cycle_a, cycle_b)

# Write ONLY the numeric value
with open('/root/answer.txt', 'w') as f:
    f.write(f"{corr:.5f}")
```

## Validation Steps

- [ ] Verify layout detection: wide matrix vs long panel vs catalog-mapped vs alias-mapped vs selector-mapped
- [ ] Confirm status filter applied (`benchmark`/`revised`/`final`/`official`/`record_type`/`preferred_version`)
- [ ] Check for `priority` column and deduplicate if present
- [ ] Verify selector columns: `preferred_source`, `preferred_version`, `month` present and used
- [ ] Confirm year ranges match across all series after processing
- [ ] Confirm log transformation before HP filter
- [ ] Check λ=100 for annual data (λ=1600 only for quarterly)
- [ ] Verify cyclical components sum approximately to zero
- [ ] Ensure answer file contains ONLY the numeric coefficient
- [ ] Check for hidden characters: `cat -A /root/answer.txt` should show `0.92431$`

## Anti-Patterns

| Don't... | Why | Instead... |
|----------|-----|------------|
| Use `Read` tool on .xlsx files | Tool cannot parse binary | Use `pandas.read_excel` in Python |
| Assume years are always rows | Wide matrix has years as columns | Detect layout from column names |
| Ignore `priority` column when duplicates exist | Keeps wrong record when multiple versions | Deduplicate by `idxmin()` on priority |
| Ignore `record_type` column in alias files | Mixes official and memo data | Filter to `'official'` when present |
| Ignore `preferred_version` in selector files | Uses wrong source/version for update data | Match both `preferred_source` and `preferred_version` from selector |
| Ignore `status_bucket` in wide matrix files | Includes memo/draft rows | Filter to `'benchmark'` or `'official'` |
| Ignore `version` column in current files | Mixes preliminary and revised data | Filter to `'revised'` when present |
| Ignore `status_flag`/`release_status` column | Mixes memo and official data | Filter to `'official'` or `'final'` |
| Hardcode column names for series | Names vary by dataset | Match on `series_name`, `series_code`, `series_label`, use catalog mapping, or alias matching |
| Ignore selector files when present | Uses wrong data source for updates | Read selector first and use `preferred_source`/`preferred_version` |
| Ignore CSV update files | Missing final year data | Check for `.csv` files with monthly data |
| Treat monthly/quarterly rows as separate observations | Creates frequency mismatch | Average to annual equivalent |
| Apply HP filter to nominal values | Mixes trend and price effects | Deflate first, then filter |
| Use λ=1600 for annual data | Wrong smoothing parameter | Use λ=100 for annual, λ=1600 for quarterly |
| Skip log transformation | HP assumes log-normality | Log-transform before filtering |
| Write with `print()` or shell redirection | May add formatting | Use Python `write()` for full control |

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Year columns not recognized | Years as strings, not detected | Use `c.isdigit()` and length check |
| FY-prefixed years not parsed | Custom format like `FY-1998` | Use `str.replace('FY-', '')` |
| Duplicate years after filtering | Multiple priority levels | Group by year and select `idxmin()` on priority |
| `KeyError` on series name | Subtle naming differences | Print unique values, match case-insensitively |
| Too many rows after filtering | Wrong status column used | Check for `status_bucket`, `version`, `record_type`, `status_flag`, and `release_status` variants |
| Missing 2025 data | In separate CSV file or not matched by selector | Look for `.csv` files, check selector matches, parse monthly/quarterly |
| Empty result from selector matching | Wrong column name assumption | Verify actual column names: `preferred_source` vs `source_file` |
| Length mismatch after merge | Different year ranges | Align to intersection or check for gaps |
| HP filter warnings | Missing values | `dropna()` before filtering |
| Hidden characters in output | Using `echo` or `print()` | Python `write()` method |
| Multiple deflator columns | Series-specific price indices | Use catalog mapping or match by series type |

## References

- `references/hp_filter_parameters.md` — Lambda selection by frequency
- `references/capital_expenditure_example.md` — Equipment/software long-format
- `references/media_broadcasting_example.md` — Broadcasting/advertising long-format
- `references/housing_panel_example.md` — Renovation/materials panel data
- `references/wide_matrix_example.md` — Network services wide-format walkthrough
- `references/catalog_mapped_example.md` — Logistics/warehousing catalog-mapped multi-file
- `references/alias_mapped_example.md` — Wholesale/packaging alias-mapped with priority deduplication
- `references/selector_mapped_example.md` — Cold chain logistics selector-mapped multi-source monthly
- `scripts/correlation_analysis.py` — Reusable template with auto-detection
