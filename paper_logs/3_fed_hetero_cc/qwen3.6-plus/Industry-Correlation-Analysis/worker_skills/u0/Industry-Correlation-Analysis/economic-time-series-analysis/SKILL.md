---
name: economic-time-series-analysis
description: Analyze economic time series by deflating nominal values, extracting cyclical components via HP filter, and computing correlations. Use when tasks involve real vs nominal indicators, detrending, business cycle analysis, cross-series correlation of macroeconomic data, or alias-mapped series with priority/record-type deduplication.
---

# Economic Time Series Analysis

## ⚠️ CRITICAL: Output Precision
**Never round, truncate, or format numeric outputs.** Verifiers check raw floats with tight tolerances (often 1e-4). Writing `0.99918` instead of `0.9991834270369953` will fail. Always write the exact Python float directly. Do NOT use `round()`, `f"{x:.Nf}"`, `.toFixed()`, or `format()`.

## Workflow
1. **Alias Mapping**: If a `series_aliases.csv` (or similar) is provided, load it to map raw `target_alias` or series names to canonical `requested_series` names before any aggregation.
2. **Load & Inspect**: Read catalog if present. Read Excel/CSV. Check column names, index formats. **Check for status/priority columns** (`release_status`, `status_flag`, `record_type`, `priority`, `revision`, `version`). Filter to authoritative values (`'final'`, `'official'`, `'revised'`). If duplicates remain for the same (series, year), deduplicate by keeping the row with the best `priority` (e.g., `min(priority)`) or latest timestamp.
3. **Detect Format**: If years are columns (matrix format `series_name | 1991 | 1992 | ...`), melt to long-form: `df.melt(id_vars=['series_name'], value_vars=year_cols, var_name='year')`. Else proceed with long-form.
4. **Clean Index/Year Columns**: Strip trailing punctuation (`1994.` -> `1994`). Handle quarterly markers (`2025:I`, `2025 Q1`, `2025-Q1`, `2025Q1`) by extracting base year. Convert all indices to integer.
5. **Aggregate Mixed Frequencies**: Quarterly → average ALL quarters (`:` OR `Q[1-4]` patterns); Monthly → extract year from `2025-06`, group by year and average.
6. **Selector/Version Routing**: If current-year updates span multiple files or versions, look for a `selector`, `routing`, or `UseThese` table mapping `(series, period) -> (source_file, version)`. Join updates to this map before filtering.
7. **Combine Multiple Sources**: Merge historical panel + aggregated updates on year. **Drop blanks/missing values** in update files before averaging to avoid NaN propagation.
8. **Deflate Nominal Series**: `Real = Nominal / Price_Index`. Verify index base (1.0 or 100). **Check for zeros before dividing.**
9. **Align Series**: Ensure same integer year index. Verify `len(s1) == len(s2)`.
10. **Log Transform**: `np.log(real_values)`. HP filter on logs, not raw levels.
11. **Apply HP Filter**: `from statsmodels.tsa.filters.hp_filter import hpfilter`. `cycle, trend = hpfilter(log_series, lamb=100)` (annual=100, quarterly=1600, monthly=14400). **Return order: (cycle, trend)**.
12. **Compute Correlation**: `scipy.stats.pearsonr` on aligned cycles.
13. **Verify & Output**: Cycle mean check `abs(np.mean(cycle)) < 1e-6`; reconstruction `trend + cycle ≈ log_series`. **Write raw float, no rounding.**

## Common Pitfalls & Anti-Patterns
- **Rounding Output**: `round(x, N)` causes verifier failure. Pass raw floats.
- **Status/Priority Not Filtered**: `record_type` ('official'/'prelim'), `release_status`, or `priority` unfiltered → duplicate years corrupt alignment. Always filter to authoritative status first, then deduplicate by priority.
- **Selector Sheet Missed**: Ignoring a provided `(series, period) -> (source, version)` routing table leads to picking wrong drafts or duplicates. Always check for routing/selector sheets when multiple update files exist.
- **Missing Values in Updates**: Blank cells in update CSVs/Excel are common. Drop them before monthly-to-annual averaging to avoid skewing or NaN propagation.
- **Matrix Format Missed**: Years as columns not detected → assume wrong structure.
- **Silent Index Misalignment**: String indices (`'1992.'`) mixed with integers (`1992`) → NaN correlations.
- **HP Filter Import**: Use `from statsmodels.tsa.filters.hp_filter import hpfilter` (NOT `from statsmodels.tsa.filters import hpfilter`).
- **HP Filter Return Order**: Returns `(cycle, trend)`. Unpacking wrong yields trend, not cycle.
- **HP Filter on Levels**: Apply to `np.log(real_series)`, not raw levels.
- **Lambda Mismatch**: Annual λ=100 (NOT 1600 for quarterly).
- **Partial Quarterly Capture**: Average ALL quarters (Q1-Q4), not just Q1.
- **Trend-vs-Cycle Correlation Trap**: Correlation >0.99 means you likely correlated trends.
- **Price Index Zeros**: Check for zeros/NaNs before deflation.

## Status & Priority Column Naming Variations
| Column Name | Typical Values | Filter To / Action |
|-------------|----------------|-------------------|
| `record_type` | 'official', 'prelim' | Filter to 'official' |
| `release_status` | 'final', 'prelim' | Filter to 'final' |
| `status_flag` | 'official', 'memo' | Filter to 'official' |
| `revision` | 'revised', 'preliminary' | Filter to 'revised' |
| `version` | 'revised', 'prelim' | Filter to 'revised' |
| `priority` | integer (1, 2, 3...) | Keep `min(priority)` per (series, year) after status filter |

## Validation Steps
- Print head/tail of cleaned series before filtering.
- **Cycle Mean**: `abs(np.mean(cycle)) < 1e-6`. Large mean = trend extracted.
- **Reconstruction**: `np.allclose(trend + cycle, log_series)`.
- Verify `len(cycle1) == len(cycle2)` and indices match.
- Check for duplicate years: `df.groupby('year').size()` all = 1.
- **Output Check**: Read back output file, verify raw float (not rounded string).

## Known invariants (by sub-task)

### economic-hp-correlation
- Check for status/priority columns; filter to authoritative values, then deduplicate by priority
- Detect matrix format (years as columns) vs long-form; reshape if needed
- Clean year columns with trailing dots (e.g., `1994.` → `1994`)
- Price index base year typically = 1.0; verify; check for zeros
- Cycle mean ≈ 0 after HP filter
- When quarterly for partial year: average ALL quarters, not just Q1

## References

- `scripts/hp_correlation.py` — Function-based helper for cleaning, deflation, HP filtering, and correlation
- `references/hp_filter_manual.py` — Pure NumPy HP filter implementation when statsmodels unavailable
