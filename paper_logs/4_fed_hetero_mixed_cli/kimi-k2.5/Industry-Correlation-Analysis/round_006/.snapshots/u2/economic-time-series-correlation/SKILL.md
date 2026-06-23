---
name: economic-time-series-correlation
description: Correlate detrended economic time series (e.g., business cycles). Use when analyzing cyclical relationships between macroeconomic variables, deflating nominal values, applying HP filter, handling messy year markers from statistical tables (BEA, Census, etc.), working with panel data in long format, combining historical annual matrices with monthly/quarterly update files, or when series catalog files map human-readable names to database codes.
---

# Economic Time Series Correlation

Analyze correlations between detrended economic variables through deflation, HP filtering, and cyclical component extraction.

## Workflow

1. **Check for Series Catalog**: If `series_catalog.csv` or similar mapping file exists, use it to resolve:
   - `history_code` → column names in historical files
   - `current_code` → codes in update/release files  
   - `deflator_column` → price index column names
   - Sheet names for Excel files

2. **Read Data**: Use `python3` and `pandas` to read Excel/CSV files.

3. **Detect Format**: Inspect structure to distinguish:
   - **Wide/Matrix format**: Years are column headers (e.g., `'1991', '1992'`)
   - **Long/Panel format**: Years are values in a column (e.g., `period_label`)

4. **Handle Wide Format**: If years are column headers:
   ```python
   # Filter for specific series and status
   df_series = df[df['series_name'] == 'Series Name']
   df_official = df_series[df_series['status_flag'] == 'official']
   # Extract year columns (exclude metadata columns)
   year_cols = [c for c in df.columns if c.isdigit()]
   values = df_official[year_cols].values[0]  # Assuming one row per series
   years = [int(c) for c in year_cols]
   ```

5. **Handle Panel/Long Format**: If data has `series_label` or similar:
   ```python
   df_series = df[df['series_label'] == 'Series Name']
   df_final = df_series[df_series['release_status'] == 'final']
   # Alternative column names: status_flag, release_status, estimate_status, version
   ```

6. **Inspect raw year markers** (Long format only): Print unique values. Pandas often infers mixed numeric/string as `object`. Always `.astype(str)` before parsing.

7. **Parse Time Markers**: Handle mixed annual/quarterly markers. Average quarterly values for partial years.
   - **Reuse**: Run `scripts/parse_year_markers.py` for messy markers
   - **Skip if**: Years are already clean column headers (wide format)

8. **Combine Historical and Update Data**: Common pattern: historical annual matrix + current-year monthly/quarterly CSV:
   ```python
   # Annual data from wide matrix (step 4 above)
   # Current data from update file - filter for highest quality status
   df_current = pd.read_csv('update_2025.csv')
   current_revised = df_current[
       (df_current['series_code'] == 'CODE_25') &
       (df_current['version'] == 'revised')  # Prefer revised over prelim
   ]
   annual_2025 = current_revised['value'].mean()  # Average quarters/months
   # Append to historical series
   ```

9. **Monthly-to-Annual Conversion**: For monthly/quarterly data needing annualization:
   ```python
   # Filter to highest quality status available
   revised = df[df['version'] == 'revised']
   if len(revised) > 0:
       data = revised
   else:
       data = df[df['version'] == 'prelim']
   annual_value = data['amount'].mean()
   ```

10. **Align series**: Merge datasets on year; verify identical length and year range.

11. **Deflate**: `real = nominal / price_index` (confirm base year = 1.0).

12. **Log Transform**: `log_real = np.log(real)`.

13. **HP Filter**: Apply Hodrick-Prescott filter.
    - `statsmodels.tsa.filters.hp_filter.hpfilter` returns `(cycle, trend)`. Use index `[0]`.
    - **Reuse**: Run `scripts/hp_correlation.py` as template

14. **Correlate**: Compute Pearson correlation between cyclical components.

15. **Format Output**: Use `f"{corr:.5f}"` for 5 decimal places with trailing zeros.

## HP Filter Lambda Values

- Annual data: λ = 100
- Quarterly data: λ = 1600
- Monthly data: λ = 14400

## Data Filtering Patterns

Statistical agency releases vary in column naming:
- `release_status`: 'final', 'prelim', 'revised' (BEA style)
- `status_flag`: 'official', 'memo', 'estimate' (Census/utility data style)
- `estimate_status`: 'advance', 'preliminary', 'final'
- `version`: 'revised', 'prelim' (update file style)

Best practice: Inspect `df.columns` and `df['status_col'].unique()` to identify the status column and values.

### Status Precedence
When multiple versions exist for the same observation period, prefer in this order:
1. 'revised' (most reliable)
2. 'final' / 'official'
3. 'prelim' / 'preliminary'
4. 'advance' / 'estimate'

**Implementation**: Filter for highest priority available:
```python
for status in ['revised', 'final', 'prelim']:
    subset = df[df['version'] == status]
    if len(subset) > 0:
        return subset
```

Additional filters:
- `period_kind == 'annual'` to exclude quarterly/monthly in annual tables
- Filter by `series_name`, `series_label`, or `series_code` to isolate individual series

## Scripts (when to run)

| Script | Use when |
|--------|----------|
| `scripts/parse_year_markers.py` | Year column contains trailing dots, quarterly markers, or mixed formats. Not needed for wide-format matrices with clean year headers. |
| `scripts/hp_correlation.py` | Template for full workflow: parsing, deflation, HP filtering, correlation. |
| `scripts/hp_filter.py` | Pure-numpy HP filter when statsmodels is unavailable. |

## Validation

- Verify year range continuity: `set(years1).symmetric_difference(years2)`
- Check deflation: Real values should match nominal magnitude in base year.
- **Verify HP filter**: `np.abs(cycle.mean()) < 1e-6`. If large, you extracted trend (wrong index) instead of cycle.
- **Quick HP verification**: Run `help(hpfilter)` or `hpfilter.__doc__` to confirm return order is `(cycle, trend)` before trusting your extraction.
- Verify status filtering: Print value counts to confirm 'official'/'final' selection.
- For combined historical+update: Verify latest year is included and averaged correctly.
- **Verify catalog mapping**: Confirm resolved column names exist in `df.columns` before filtering.

## Anti-patterns

- **Do not** assume `release_status` is the column name; check for `status_flag`, `version`, or similar.
- **Do not** guess column codes; check for `series_catalog.csv` or similar mapping files first.
- **Do not** apply year-parsing scripts to wide-format matrices (years are already column names).
- **Do not** cast year columns to `int` without inspection; statistical tables use `'1994.'` or mixed formats.
- **Do not** drop partial years; average available months/quarters to preserve observations.
- **Do not** apply HP filter to nominal values; always deflate first, then log transform.
- **Wrong HP import**: `scipy.signal.hp_filter` does NOT exist. Use `statsmodels.tsa.filters.hp_filter.hpfilter`.
- **HP Return Order**: `hpfilter()` returns `(cycle, trend)`, NOT `(trend, cycle)`. Using `[1]` gives trend (smooth, non-zero-mean), which ruins correlations. Always use `[0]`.
- **HP Parameter**: Use `lamb=100`, NOT `lam`.
- **Do not** mix status versions in the same series (e.g., 2024 'final' with 2025 'prelim'); prefer consistent status levels or document the mix.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `KeyError: 'release_status'` | Column named differently | Check for `status_flag`, `estimate_status`, `version`, or similar |
| `KeyError: 'BROKER_REV'` | Column code wrong | Check `series_catalog.csv` or file headers for correct code |
| `ValueError: invalid literal` on year | Trailing dots or non-numeric markers | Strip: `str.replace('.', '', regex=False)` or use `parse_year_markers.py` |
| Years are column headers, not values | Wide/matrix format | Select columns directly; don't parse |
| Length mismatch after merge | Gap years or missing latest partial year | Check symmetric difference of year sets |
| Missing recent year | Monthly update file not incorporated | Average monthly values and append to annual series |
| Cycle mean is large (>0.01) | Extracted trend instead of cycle | Use `hpfilter()` return value `[0]`, not `[1]` |
| Same period appears multiple times | Multiple status versions (revised+prelim) | Filter for 'revised' or apply status precedence |

## Output precision

Never round numeric values when writing to files (Excel, JSON, CSV). Pass raw floats. The verifier's tolerance decides precision.

For correlation output specifically: `f"{corr:.5f}"` preserves trailing zeros as required.

## References

- `references/excel-year-parsing.md` — Year marker formats, wide vs long format, monthly conversion
- `references/hp-lambda-values.md` — HP filter lambda values by frequency
- `references/series-catalog-pattern.md` — Mapping file patterns for series codes and deflators