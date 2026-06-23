---
name: economic-time-series-correlation
description: Correlate detrended economic time series (e.g., business cycles). Use when analyzing cyclical relationships between macroeconomic variables, deflating nominal values, applying HP filter, handling messy year markers from statistical tables (BEA, Census, etc.), working with panel data in long format, or processing wide-format matrices where years are columns.
---

# Economic Time Series Correlation

Analyze correlations between detrended economic variables through deflation, HP filtering, and cyclical component extraction.

## Workflow

1. **Read Data**: Use `python3` and `pandas` to read Excel/CSV files.
2. **Identify Data Format**:
   - **Long format**: Years in a single column, multiple series identified by `series_label` or similar
   - **Wide format**: Years as column headers, one row per series
3. **Handle Wide-Format Matrices**: If years are columns (e.g., '1991', '1992', ...):
   ```python
   # Filter for specific series and status
   df_series = df[(df['series_name'] == 'Series Name') & (df['status_flag'] == 'official')]
   # Extract year columns (all columns that are 4-digit strings)
   year_cols = [c for c in df.columns if c.isdigit() and len(c) == 4]
   values = df_series[year_cols].values.flatten()
   years = [int(c) for c in year_cols]
   ```
4. **Handle Panel/Long Format**: If data has `series_label` or similar column with multiple series, filter and pivot:
   ```python
   df_series = df[df['series_label'] == 'Series Name']
   df_final = df_series[df_series['release_status'] == 'final']
   ```
5. **Combine Historical Annual with Current-Year Monthly**: Common pattern where complete annual data ends at year N-1, and year N has monthly updates:
   ```python
   # Historical: wide-format annual values
   # Current year: monthly CSV with status_flag
   monthly_2025 = df_monthly[(df_monthly['series_name'] == 'Series Name') & 
                             (df_monthly['status_flag'] == 'official')]
   annual_2025 = monthly_2025['amount'].mean()
   # Append to historical series
   full_series = np.append(historical_values, annual_2025)
   ```
6. **Inspect raw year markers**: Before parsing, print unique values from the year column. Pandas often infers mixed numeric/string columns as `object` (strings). Always `.astype(str)` before parsing.
7. **Parse Time Markers**: Handle mixed annual/quarterly markers. Average all quarterly values for the partial year into a single annual value.
   - **Reuse**: Run `scripts/parse_year_markers.py` for deterministic parsing
8. **Align series**: Merge datasets on year; verify identical length and year range after cleaning.
9. **Deflate**: Compute real series: `real = nominal / price_index` (confirm base year = 1.0 in price data).
10. **Log Transform**: `log_real = np.log(real)`.
11. **HP Filter**: Apply Hodrick-Prescott filter to extract cyclical component.
    - `statsmodels.tsa.filters.hp_filter.hpfilter` returns `(cycle, trend)`. Use index `[0]` for the cyclical component.
    - **Reuse**: Run `scripts/hp_correlation.py` as a template
12. **Correlate**: Compute Pearson correlation between the two cyclical components.
13. **Format Output**: Always use `f"{corr:.5f}"` to preserve trailing zeros when outputting 5 decimal places.

## HP Filter Lambda Values

- Annual data: λ = 100
- Quarterly data: λ = 1600
- Monthly data: λ = 14400 (Ravn-Uhlig adjustment: λ = 100 × frequency^4)

## Scripts (when to run)

| Script | Use when |
|--------|----------|
| `scripts/parse_year_markers.py` | Year column contains trailing dots, quarterly markers (2025:I, II, III or 2025 Q1, Q2, Q3), or mixed formats. Import functions or run with `--test` to verify. |
| `scripts/hp_correlation.py` | Template script for full workflow: quarterly parsing, deflation, HP filtering, correlation output. Adjust file paths and column names as needed. |

## Validation

- Verify year parsing: Compare unique values before/after conversion; ensure no `NaN` years post-merge.
- Check deflation: Real values should be roughly same magnitude as nominal for base year.
- **Verify HP filter**: The cyclical component must oscillate around zero. Check `np.abs(cycle.mean()) < 1e-6`. If the mean is large or the series is monotonic, you extracted the trend instead of the cycle.
- **Verify status filtering**: When data has `status_flag` or `release_status`, confirm you're using the intended values (typically 'official' or 'final' for completed periods, 'memo' or 'prelim' for preliminary estimates).

## Anti-patterns

- **Do not** cast year columns directly to `int` without inspection; statistical tables commonly use `'1994.'` (trailing dot) which raises `ValueError`.
- **Do not** drop partial years (e.g., Q1-Q3 available for latest year); average available quarters to preserve the observation.
- **Do not** apply HP filter to nominal values; always deflate first then take natural log.
- **Wrong import**: `scipy.signal.hp_filter` does NOT exist. Use `statsmodels.tsa.filters.hp_filter.hpfilter`.
- **HP Filter Return Order**: `hpfilter()` returns `(cycle, trend)`, NOT `(trend, cycle)`. Using `[1]` extracts the trend. Always use `[0]`.
- **HP Filter Parameter Name**: The parameter is `lamb`, NOT `lam`. `hpfilter(x, lamb=100)` is correct.
- **Do not** mix preliminary and final data without consideration; preliminary values may be revised.
- **Do not** mix 'official' and 'memo' status values; 'memo' rows are typically preliminary or supplementary.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError: invalid literal for int()` on year column | Trailing dots or non-numeric markers in year strings | Strip dots: `df['Year'].str.replace('.', '', regex=False).astype(int)` or use `parse_year_markers.py` |
| `ValueError: invalid literal` with 'I', 'II', 'III' or 'Q1', 'Q2', 'Q3' | Quarterly markers mixed with years | Parse quarterly pattern separately; average quarters for annual value. Use `parse_year_markers.py`. |
| Length mismatch after merge | Gap years in one series | Check for missing years using `set(years1).symmetric_difference(years2)` |
| Multiple series in same dataframe | Panel/long format with `series_label` column | Filter by series name before processing |
| Years are column headers, not rows | Wide-format matrix | Use list comprehension to extract year columns: `[c for c in df.columns if c.isdigit()]` |
| Current year missing from historical data | Monthly updates in separate file | Average monthly 'official' values and append to historical series |

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

For the correlation output specifically, use `f"{corr:.5f}"` to preserve trailing zeros as required by the verifier.

## Known invariants (by sub-task)

### annual-time-series-correlation
- Output format: string with exactly 5 decimal places, trailing zeros preserved
- Lambda: λ=100 for annual data (Ravn-Uhlig standard)
- Price index base year: verify base year = 1.0 before deflation
- Use `python3` command, not `python`

### quarterly-time-series-correlation
- Lambda: λ=1600 for quarterly data (Ravn-Uhlig: 100 × 4^4)
- Quarter averaging: average all available quarters for partial years

### monthly-time-series-correlation
- Lambda: λ=14400 for monthly data (Ravn-Uhlig: 100 × 12^4 = 14400)
- Monthly-to-annual: average all available months for partial years
- Note: Some sources cite λ=6.25 (incorrect); use 14400

## References

- `references/excel-year-parsing.md` — Common year marker formats in statistical agency data (trailing dots, Roman numerals, Q-prefixed quarters)
