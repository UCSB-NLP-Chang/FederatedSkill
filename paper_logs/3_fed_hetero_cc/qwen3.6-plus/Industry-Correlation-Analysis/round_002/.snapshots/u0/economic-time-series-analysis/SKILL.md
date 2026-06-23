---
name: economic-time-series-analysis
description: Analyze economic time series by deflating nominal values, extracting cyclical components via HP filter, and computing correlations. Use when tasks involve real vs nominal indicators, detrending, business cycle analysis, or cross-series correlation of macroeconomic data.
---

# Economic Time Series Analysis

## Workflow
1. **Load & Inspect**: Read Excel/CSV files. Check column names, index formats, and data types.
2. **Clean Index/Year Columns**: Strip trailing punctuation (e.g., `1994.` -> `1994`). Handle quarterly markers (`2025:I`) by extracting the base year. Convert all indices to numeric integers.
3. **Aggregate Mixed Frequencies**: If quarterly data maps to the same year, aggregate to annual (mean or sum) before alignment. Never mix string and integer indices.
4. **Deflate Nominal Series**: Convert nominal values to real terms using a price index: `Real = Nominal / (Price_Index / Base_Multiplier)`. Verify the index base (e.g., 1.0 or 100).
5. **Align Series**: Ensure all series share the exact same integer year index. Drop or interpolate missing values. Verify `len(s1) == len(s2)`.
6. **Log Transform**: Apply `np.log()` to real values. HP filter must be applied to log-transformed series, not raw levels.
7. **Apply HP Filter**: Extract cyclical components.
   - **Correct Import**: `from statsmodels.tsa.filters.hp_filter import hpfilter`
   - **Usage**: `cycle, trend = hpfilter(log_series, lamb=100)` (use `100` for annual, `1600` for quarterly, `14400` for monthly).
8. **Compute Correlation**: Use `scipy.stats.pearsonr` on the aligned cyclical components.
9. **Verify & Output**: Check p-values, ensure series lengths match, and write the final metric.

## Common Pitfalls & Anti-Patterns
- **Silent Index Misalignment**: Mixing string indices (`'1992.'`, `'2025:I'`) with integer indices (`1992`) causes `pd.concat` to produce NaNs. Always normalize to integer years first.
- **HP Filter Import**: `from statsmodels.tsa.filters import hpfilter` fails. Always use `from statsmodels.tsa.filters.hp_filter import hpfilter`.
- **HP Filter on Levels**: Apply HP filter to log-transformed real values, not raw levels. `cycle = hpfilter(np.log(real_series))` is correct.
- **Lambda Mismatch**: Use λ=100 for annual data (not 1600, which is for quarterly). Wrong lambda produces invalid cyclical decomposition.
- **Mismatched Frequencies**: Annual vs quarterly data must be aligned. Aggregate quarterly to annual explicitly before filtering.
- **Deflation Base**: Verify the price index base year. If the index is `1.0` in the base year, divide directly. If it's `100`, divide by `index/100`.

## Validation Steps
- Print head/tail of cleaned series before filtering.
- Verify `len(cycle1) == len(cycle2)` and `cycle1.index.equals(cycle2.index)` before correlation.
- Check `p-value` from `pearsonr` to ensure statistical significance.
- If correlation is `NaN`, immediately inspect index types and alignment.

## References

- `scripts/hp_correlation.py` — Function-based helper for cleaning, deflation, HP filtering, and correlation
- `references/hp_filter_manual.py` — Pure NumPy HP filter implementation when statsmodels unavailable