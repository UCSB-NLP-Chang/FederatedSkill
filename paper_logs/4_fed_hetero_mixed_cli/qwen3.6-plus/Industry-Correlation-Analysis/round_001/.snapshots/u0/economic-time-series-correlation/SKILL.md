---
name: economic-time-series-correlation
description: Correlate detrended economic time series (e.g., business cycles). Use when analyzing cyclical relationships between macroeconomic variables, deflating nominal values, applying HP filter, or handling messy year markers from statistical tables.
---

# Economic Time Series Correlation

Analyze correlations between detrended economic variables through deflation, HP filtering, and cyclical component extraction.

## Workflow

1. **Read Data**: Use `python3` and `pandas` to read Excel/CSV files. Do not rely on `read_file` for binary spreadsheets.
2. **Inspect raw year markers**: Before parsing, print unique values from the year column to identify formatting artifacts (trailing dots, quarterly markers).
3. **Parse Time Markers**: Handle mixed annual/quarterly markers (e.g., `"2025:I"`, `"II"`, `"III"`). Average all quarterly values for the partial year into a single annual value.
4. **Align series**: Merge datasets on year; verify identical length and year range after cleaning.
5. **Deflate**: Compute real series: `real = nominal / price_index` (confirm base year = 1.0 in price data).
6. **Log Transform**: `log_real = np.log(real)`.
7. **HP Filter**: Apply Hodrick-Prescott filter to extract cyclical component: `cycle = log_real - trend`.
8. **Correlate**: Compute Pearson correlation between the two cyclical components.
9. **Format Output**: Always use `f"{corr:.5f}"` to preserve trailing zeros when outputting 5 decimal places.

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
- **Year Parsing**: Do not cast year columns directly to `int` without inspection; statistical tables commonly use `'1994.'` (trailing dot) or quarterly markers which raise `ValueError`.
- **Quarterly Parsing**: Do not assume partial-year rows are already annualized. Look for markers like `:I`, `II`, `III`, `IV` and average them.
- **Trailing Zeros**: `round(x, 5)` drops trailing zeros in Python. Use formatted strings `f"{x:.5f}"` for exact decimal output.
- **HP Filter on Nominal**: Always deflate and take log before applying HP filter. Never apply to raw nominal values.

## Validation

- Verify year parsing: Compare unique values before/after conversion; ensure no `NaN` years post-merge.
- Check deflation: Real values should be roughly same magnitude as nominal for base year.
- Verify HP filter: Cyclical component should oscillate around zero without trend drift.

## Script Usage

Run `scripts/hp_correlation.py` as a starting template. It handles quarterly parsing, deflation, HP filtering, and formatted output. Adjust file paths and column names as needed.

## References

- `references/excel-year-parsing.md` - Common year marker formats in statistical agency data (BEA, Census, Federal Reserve)