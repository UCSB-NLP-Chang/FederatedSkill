---
name: economic-time-series-correlation
description: Correlate detrended economic time series (e.g., business cycles). Use when analyzing cyclical relationships between macroeconomic variables, deflating nominal values, applying HP filter, or handling messy year markers from statistical tables (BEA, Census, etc.).
---

# Economic Time Series Correlation

Analyze correlations between detrended economic variables through deflation, HP filtering, and cyclical component extraction.

## Workflow

1. **Inspect raw year markers**: Before parsing, print unique values from the year column to identify formatting artifacts (trailing dots, quarterly markers).
2. **Parse year markers**:
   - Strip trailing dots: `'1994.' → 1994` via `str.rstrip('.')` or `int(float(x))`
   - Handle mixed quarterly data: Identify patterns like `'2025:I'`, `'II'`, `'III'` and average available quarters to produce annual values
   - Forward-fill base years when quarters appear as continuation rows
3. **Align series**: Merge datasets on year; verify identical length and year range after cleaning.
4. **Deflate to real values**: Divide nominal series by price index (confirm base year = 1.0 in the price data).
5. **Detrend**: Apply HP filter (λ=100 for annual data) to natural log of real values: `cycle = ln(real) - trend`.
6. **Compute correlation**: Pearson correlation between cyclical components of the two series.

## Validation

- Verify year parsing: Compare unique values before/after conversion; ensure no `NaN` years post-merge.
- Check deflation: Real values should be roughly same magnitude as nominal for base year; trend should increase with inflation in other years.
- Verify HP filter: Cyclical component should oscillate around zero without trend drift.

## Anti-patterns

- **Do not** cast year columns directly to `int` without inspection; statistical tables commonly use `'1994.'` (trailing dot) which raises `ValueError`.
- **Do not** drop partial years (e.g., Q1-Q3 available for latest year); average available quarters to preserve the observation.
- **Do not** apply HP filter to nominal values; always deflate first then take natural log.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError: invalid literal for int()` on year column | Trailing dots or non-numeric markers in year strings | Strip dots: `df['Year'].str.replace('.', '', regex=False).astype(int)` |
| `ValueError: invalid literal` with 'I', 'II', 'III' | Quarterly markers (Roman numerals) mixed with years | Parse quarterly pattern separately; average quarters for annual value |
| Length mismatch after merge | Gap years in one series | Check for missing years using `set(years1).symmetric_difference(years2)` |

## Output precision

The correlation output must preserve trailing zeros. Use `f"{corr:.5f}"` for
formatted output, NOT `round(corr, 5)` which drops trailing zeros.

Concretely:
- DO: `print(f"{correlation:.5f}")` outputs `0.12340` (preserves zeros)
- DO NOT: `print(round(correlation, 5))` outputs `0.1234` (drops trailing zeros)

## Known invariants (by sub-task)

### annual-time-series-correlation
- Output format: string with exactly 5 decimal places, trailing zeros preserved
- Lambda: λ=100 for annual data (Ravn-Uhlig standard)
- Price index base year: verify base year = 1.0 before deflation

### quarterly-time-series-correlation
- Lambda: λ=1600 for quarterly data (Ravn-Uhlig: 100 × frequency^4)
- Quarter averaging: average all available quarters for partial years

### monthly-time-series-correlation
- Lambda: λ=14400 for monthly data (Ravn-Uhlig: 100 × 12^4 = 14400)
- Note: Some sources cite λ=6.25 (incorrect); use 14400

## References

- `references/excel-year-parsing.md` - Common year marker formats in statistical agency data
- `references/hp-lambda-values.md` - HP filter lambda values by data frequency
- `scripts/hp_filter.py` - Reusable Hodrick-Prescott filter implementation