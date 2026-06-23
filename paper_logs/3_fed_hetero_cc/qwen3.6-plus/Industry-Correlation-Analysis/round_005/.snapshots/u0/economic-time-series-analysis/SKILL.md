---
name: economic-time-series-analysis
description: Analyze economic time series by deflating nominal values, extracting cyclical components via HP filter, and computing correlations. Use when tasks involve real vs nominal indicators, detrending, business cycle analysis, or cross-series correlation of macroeconomic data.
---

# Economic Time Series Analysis

## ⚠️ CRITICAL: Output Precision
**Never round, truncate, or format numeric outputs.** Verifiers check raw floats with tight tolerances (often 1e-4). Writing `0.99918` instead of `0.9991834270369953` will fail. Always write the exact Python float directly. Do NOT use `round()`, `f"{x:.Nf}"`, `.toFixed()`, or `format()`.

## Workflow
1. **Load & Inspect**: Read Excel/CSV. Check column names, index formats. **Check for status columns** (`release_status`, `status_flag`, `revision`) - if present, filter to authoritative values (`'final'`, `'official'`, `'revised')` to avoid duplicate year entries.
2. **Detect Format**: If years are columns (matrix format `series_name | 1991 | 1992 | ...`), melt to long-form: `df.melt(id_vars=['series_name'], value_vars=year_cols, var_name='year')`. Else proceed with long-form.
3. **Clean Index/Year Columns**: Strip trailing punctuation (`1994.` -> `1994`). Handle quarterly markers (`2025:I`, `2025 Q1`) by extracting base year. Convert all indices to integer.
4. **Aggregate Mixed Frequencies**: Quarterly → average ALL quarters (`:` OR `Q[1-4]` patterns); Monthly → extract year from `2025-06`, group by year and average.
5. **Combine Multiple Sources**: If historical panel + update sheets, merge on year after aggregating each.
6. **Deflate Nominal Series**: `Real = Nominal / Price_Index`. Verify index base (1.0 or 100). **Check for zeros before dividing.**
7. **Align Series**: Ensure same integer year index. Verify `len(s1) == len(s2)`.
8. **Log Transform**: `np.log(real_values)`. HP filter on logs, not raw levels.
9. **Apply HP Filter**: `from statsmodels.tsa.filters.hp_filter import hpfilter`. `cycle, trend = hpfilter(log_series, lamb=100)` (annual=100, quarterly=1600, monthly=14400). **Return order: (cycle, trend)**.
10. **Compute Correlation**: `scipy.stats.pearsonr` on aligned cycles.
11. **Verify & Output**: Cycle mean check `abs(np.mean(cycle)) < 1e-6`; reconstruction `trend + cycle ≈ log_series`. **Write raw float, no rounding.**

## Common Pitfalls & Anti-Patterns
- **Rounding Output**: `round(x, N)` causes verifier failure. Pass raw floats.
- **Status Flag Not Filtered**: `release_status` ('final'/'prelim') or `status_flag` ('official'/'memo') unfiltered → duplicate years corrupt alignment.
- **Matrix Format Missed**: Years as columns not detected → assume wrong structure.
- **Silent Index Misalignment**: String indices (`'1992.'`) mixed with integers (`1992`) → NaN correlations.
- **HP Filter Import**: Use `from statsmodels.tsa.filters.hp_filter import hpfilter` (NOT `from statsmodels.tsa.filters import hpfilter`).
- **HP Filter Return Order**: Returns `(cycle, trend)`. Unpacking wrong yields trend, not cycle.
- **HP Filter on Levels**: Apply to `np.log(real_series)`, not raw levels.
- **Lambda Mismatch**: Annual λ=100 (NOT 1600 for quarterly).
- **Partial Quarterly Capture**: Average ALL quarters (Q1-Q4), not just Q1.
- **Trend-vs-Cycle Correlation Trap**: Correlation >0.99 means you likely correlated trends.
- **Price Index Zeros**: Check for zeros/NaNs before deflation.

## Status Column Naming Variations
| Column Name | Typical Values | Filter To |
|-------------|----------------|-----------|
| `release_status` | 'final', 'prelim' | 'final' |
| `status_flag` | 'official', 'memo' | 'official' |
| `revision` | 'revised', 'preliminary' | 'revised' |

## Validation Steps
- Print head/tail of cleaned series before filtering.
- **Cycle Mean**: `abs(np.mean(cycle)) < 1e-6`. Large mean = trend extracted.
- **Reconstruction**: `np.allclose(trend + cycle, log_series)`.
- Verify `len(cycle1) == len(cycle2)` and indices match.
- Check for duplicate years: `df.groupby('year').size()` all = 1.
- **Output Check**: Read back output file, verify raw float (not rounded string).

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### economic-hp-correlation
- Check for status columns; filter to authoritative values (final, official, revised)
- Detect matrix format (years as columns) vs long-form; reshape if needed
- Clean year columns with trailing dots (e.g., `1994.` → `1994`)
- Price index base year typically = 1.0; verify; check for zeros
- Cycle mean ≈ 0 after HP filter
- When quarterly for partial year: average ALL quarters, not just Q1

## References

- `scripts/hp_correlation.py` — Function-based helper for cleaning, deflation, HP filtering, and correlation
- `references/hp_filter_manual.py` — Pure NumPy HP filter implementation when statsmodels unavailable