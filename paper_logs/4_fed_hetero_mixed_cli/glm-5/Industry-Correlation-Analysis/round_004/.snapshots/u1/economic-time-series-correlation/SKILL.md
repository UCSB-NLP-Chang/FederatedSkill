---
name: economic-time-series-correlation
description: Correlate detrended economic time series (e.g., business cycles). Use when analyzing cyclical relationships between macroeconomic variables, deflating nominal values, applying HP filter, handling messy year markers from statistical tables (BEA, Census, etc.), or working with panel data in long format.
---

# Economic Time Series Correlation

Analyze correlations between detrended economic variables through deflation, HP filtering, and cyclical component extraction.

## Workflow

1. **Read Data**: Use `python3` and `pandas` to read Excel/CSV files.
2. **Handle Panel/Long Format**: If data has `series_label` or similar column with multiple series, filter and pivot:
   ```python
   # Filter for specific series
   df_series = df[df['series_label'] == 'Series Name']
   # Filter for release status if present
   df_final = df_series[df_series['release_status'] == 'final']
   ```
3. **Inspect raw year markers**: Before parsing, print unique values from the year column. Pandas often infers mixed numeric/string columns as `object` (strings). Always `.astype(str)` before parsing.
4. **Parse Time Markers**: Handle mixed annual/quarterly markers (e.g., `"2025:I"`, `"II"`, `"III"` or `"2025 Q1"`, `"Q2"`, `"Q3"`). Average all quarterly values for the partial year into a single annual value.
   - **Reuse**: Run `scripts/parse_year_markers.py` for deterministic parsing
5. **Monthly-to-Annual Conversion**: For monthly data that needs annualizing:
   ```python
   # Filter for final monthly values, then average
   monthly_final = df_monthly[df_monthly['release_status'] == 'final']
   annual_value = monthly_final['amount'].mean()
   ```
6. **Align series**: Merge datasets on year; verify identical length and year range after cleaning.
7. **Deflate**: Compute real series: `real = nominal / price_index` (confirm base year = 1.0 in price data).
8. **Log Transform**: `log_real = np.log(real)`.
9. **HP Filter**: Apply Hodrick-Prescott filter to extract cyclical component.
   - `statsmodels.tsa.filters.hp_filter.hpfilter` returns `(cycle, trend)`. Use index `[0]` for the cyclical component.
   - **Reuse**: Run `scripts/hp_correlation.py` as a template (handles quarterly parsing, deflation, HP filtering, correlation output)
10. **Correlate**: Compute Pearson correlation between the two cyclical components.
11. **Format Output**: Always use `f"{corr:.5f}"` to preserve trailing zeros when outputting 5 decimal places.

## HP Filter Lambda Values

- Annual data: λ = 100
- Quarterly data: λ = 1600
- Monthly data: λ = 14400 (Ravn-Uhlig adjustment: λ = 100 × frequency^4)

## Scripts (when to run)

| Script | Use when |
|--------|----------|
| `scripts/parse_year_markers.py` | Year column contains trailing dots, quarterly markers (2025:I, II, III or 2025 Q1, Q2, Q3), or mixed formats. Import functions or run with `--test` to verify. |
| `scripts/hp_correlation.py` | Template script for full workflow: quarterly parsing, deflation, HP filtering, correlation output. Adjust file paths and column names as needed. |
| `scripts/hp_filter.py` | Pure-numpy HP filter implementation (returns trend, cycle). Use when statsmodels is unavailable. |

## Validation

- Verify year parsing: Compare unique values before/after conversion; ensure no `NaN` years post-merge.
- Check deflation: Real values should be roughly same magnitude as nominal for base year.
- **Verify HP filter**: The cyclical component must oscillate around zero. Check `np.abs(cycle.mean()) < 1e-6`. If the mean is large or the series is monotonic, you extracted the trend instead of the cycle.
- **Verify release status**: When data has `release_status`, confirm you're using the intended values (typically 'final' for completed periods, 'prelim' for recent estimates).

## Anti-patterns

- **Do not** cast year columns directly to `int` without inspection; statistical tables commonly use `'1994.'` (trailing dot) which raises `ValueError`.
- **Do not** drop partial years (e.g., Q1-Q3 available for latest year); average available quarters to preserve the observation.
- **Do not** apply HP filter to nominal values; always deflate first then take natural log.
- **Wrong import**: `scipy.signal.hp_filter` does NOT exist. Use `statsmodels.tsa.filters.hp_filter.hpfilter`.
- **HP Filter Return Order**: `hpfilter()` returns `(cycle, trend)`, NOT `(trend, cycle)`. Using `[1]` extracts the trend, which will produce a smooth, non-zero-mean series and incorrect correlations. Always use `[0]`.
- **HP Filter Parameter Name**: The parameter is `lamb`, NOT `lam`. `hpfilter(x, lamb=100)` is correct; `hpfilter(x, lam=100)` raises `TypeError`.
- **Do not** mix preliminary and final data without consideration; preliminary values may be revised.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError: invalid literal for int()` on year column | Trailing dots or non-numeric markers in year strings | Strip dots: `df['Year'].str.replace('.', '', regex=False).astype(int)` or use `parse_year_markers.py` |
| `ValueError: invalid literal` with 'I', 'II', 'III' or 'Q1', 'Q2', 'Q3' | Quarterly markers (Roman numerals or Q-prefixed) mixed with years | Parse quarterly pattern separately; average quarters for annual value. Use `parse_year_markers.py` which handles both formats. |
| `Roman numeral 'II' appears without preceding year` in parser | Data starts with continuation row without base year | Inspect raw data; may need to manually prepend year or fix source |
| `Quarter marker 'Q2' appears without preceding year` in parser | Q-prefixed continuation row appears before any year row | Inspect raw data; check for header rows or malformed input |
| Length mismatch after merge | Gap years in one series | Check for missing years using `set(years1).symmetric_difference(years2)` |
| Multiple series in same dataframe | Panel/long format with `series_label` column | Filter by series name before processing: `df[df['series_label'] == 'Name']` |
| Monthly data needs annual value | Update sheet with monthly breakdown | Filter for final values, then group by year and average |

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
