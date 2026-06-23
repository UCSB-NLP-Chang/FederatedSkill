---
name: economic-time-series-analysis
description: Analyze economic time series by deflating nominal values, extracting cyclical components via HP filter, and computing correlations. Use when tasks involve real vs nominal indicators, detrending, business cycle analysis, or cross-series correlation of macroeconomic data.
---

# Economic Time Series Analysis

## Workflow
1. **Load & Inspect**: Read Excel/CSV files. Check column names, index formats, and data types. **Check for status columns** (`release_status`, `revision`) - if present, filter to `'final'` values to avoid duplicate year entries.
2. **Clean Index/Year Columns**: Strip trailing punctuation (e.g., `1994.` -> `1994`). Handle quarterly markers (`2025:I`, `2025 Q1`) by extracting the base year. Convert all indices to numeric integers.
3. **Aggregate Mixed Frequencies**: 
   - Quarterly: Average ALL available quarters (regex `:` OR `Q[1-4]` patterns), not just Q1
   - Monthly: Extract year from `month` column (e.g., `2025-06` -> 2025), group by year and average
4. **Combine Multiple Sources**: If historical panel + update sheets, merge on year after aggregating each.
5. **Deflate Nominal Series**: Convert nominal values to real terms: `Real = Nominal / Price_Index`. Verify the index base (e.g., 1.0 or 100). **Check for zeros in price index before dividing.**
6. **Align Series**: Ensure all series share the exact same integer year index. Drop or interpolate missing values. Verify `len(s1) == len(s2)`.
7. **Log Transform**: Apply `np.log()` to real values. HP filter must be applied to log-transformed series, not raw levels.
8. **Apply HP Filter**: Extract cyclical components.
   - **Correct Import**: `from statsmodels.tsa.filters.hp_filter import hpfilter`
   - **Usage**: `cycle, trend = hpfilter(log_series, lamb=100)` (use `100` for annual, `1600` for quarterly, `14400` for monthly).
   - **Return Order**: `hpfilter` returns `(cycle, trend)`. Do not index `[1]` or unpack incorrectly.
9. **Compute Correlation**: Use `scipy.stats.pearsonr` on the aligned cyclical components.
10. **Verify & Output**: 
    - **Cycle Mean Check**: `abs(np.mean(cycle)) < 1e-6` - large mean indicates trend extracted instead
    - **Reconstruction Check**: `np.allclose(trend + cycle, log_series)` - catches unpacking errors
    - Check p-values, ensure series lengths match, and write the final metric.

## Common Pitfalls & Anti-Patterns
- **Status Flag Not Filtered**: If `release_status` exists, unfiltered 'final'/'prelim' pairs create duplicate years corrupting alignment.
- **Silent Index Misalignment**: Mixing string indices (`'1992.'`, `'2025:I'`) with integer indices (`1992`) causes `pd.concat` to produce NaNs. Always normalize to integer years first.
- **HP Filter Import**: `from statsmodels.tsa.filters import hpfilter` fails. Always use `from statsmodels.tsa.filters.hp_filter import hpfilter`.
- **HP Filter on Levels**: Apply HP filter to log-transformed real values, not raw levels. `cycle = hpfilter(np.log(real_series))` is correct.
- **HP Filter Return Order**: `hpfilter` returns `(cycle, trend)`. Unpacking as `trend, cycle = ...` or taking index `[1]` yields the trend, not the cycle.
- **Lambda Mismatch**: Use λ=100 for annual data (not 1600, which is for quarterly). Wrong lambda produces invalid cyclical decomposition.
- **Mismatched Frequencies**: Annual vs quarterly data must be aligned. Aggregate quarterly to annual explicitly before filtering.
- **Deflation Base**: Verify the price index base year. If the index is `1.0` in the base year, divide directly. If it's `100`, divide by `index/100`.
- **Price Index Zeros**: Check for zeros/NaNs in price index before deflation to avoid division errors.
- **Partial Quarterly Capture**: When averaging quarterly data for annual synthesis, ensure ALL quarters (Q1-Q4, or available Q1-Q3) are captured. Do not stop at Q1. Verify by printing the count of quarterly values found.
- **Trend-vs-Cycle Correlation Trap**: If correlation >0.99 for "detrended" cycles, you likely correlated trends. Verify cycle properties before trusting.

## Validation Steps
- Print head/tail of cleaned series before filtering.
- **Cycle Mean Check**: Verify `abs(np.mean(cycle)) < 1e-6`. A large mean indicates you extracted the trend instead of the cycle.
- **Reconstruction Check**: Verify `np.allclose(trend + cycle, log_series)`. If false, filter unpacking or implementation is wrong.
- Verify `len(cycle1) == len(cycle2)` and `cycle1.index.equals(cycle2.index)` before correlation.
- Check `p-value` from `pearsonr` to ensure statistical significance.
- If correlation is `NaN`, immediately inspect index types and alignment.
- Check for duplicate years after filtering: `df.groupby('year').size()` should all be 1.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## References

- `scripts/hp_correlation.py` — Function-based helper for cleaning, deflation, HP filtering, and correlation
- `references/hp_filter_manual.py` — Pure NumPy HP filter implementation when statsmodels unavailable