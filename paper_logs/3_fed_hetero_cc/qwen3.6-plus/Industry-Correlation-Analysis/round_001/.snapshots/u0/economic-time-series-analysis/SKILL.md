---
name: economic-time-series-analysis
description: Analyze economic time series by deflating nominal values, extracting cyclical components via HP filter, and computing correlations. Use when tasks involve real vs nominal indicators, detrending, business cycle analysis, or cross-series correlation of macroeconomic data.
---

# Economic Time Series Analysis

## Workflow
1. **Load & Inspect**: Read Excel/CSV files. Check column names, index formats, and data types.
2. **Clean Index/Year Columns**: Strip trailing punctuation (e.g., `1994.` -> `1994`). Handle quarterly markers (`2025:I`) by mapping to numeric or keeping as strings if alignment allows. Convert to numeric where possible.
3. **Deflate Nominal Series**: Convert nominal values to real terms using a price index: `Real = Nominal / (Price_Index / Base_Multiplier)`. Verify the index base (e.g., 1.0 or 100).
4. **Align Series**: Ensure all series share the exact same index/years before filtering. Drop or interpolate missing values.
5. **Log Transform**: Apply `np.log()` to real values. HP filter should be applied to log-transformed series, not raw levels.
6. **Apply HP Filter**: Extract cyclical components.
   - **Correct Import**: `from statsmodels.tsa.filters.hp_filter import hpfilter`
   - **Usage**: `cycle, trend = hpfilter(log_series, lamb=100)` (use `100` for annual, `1600` for quarterly, `14400` for monthly).
7. **Compute Correlation**: Use `scipy.stats.pearsonr` on the aligned cyclical components.
8. **Verify & Output**: Check p-values, ensure series lengths match, and write the final metric.

## Common Pitfalls & Anti-Patterns
- **Year Parsing Errors**: Excel exports often append dots to years (`1994.`). Always strip non-numeric characters before `astype(int)`.
- **HP Filter Import**: `from statsmodels.tsa.filters import hpfilter` fails. Always use `from statsmodels.tsa.filters.hp_filter import hpfilter`.
- **HP Filter on Levels**: Apply HP filter to log-transformed real values, not raw levels. `cycle = hpfilter(np.log(real_series))` is correct.
- **Lambda Mismatch**: Use λ=100 for annual data (not 1600, which is for quarterly). Wrong lambda produces invalid cyclical decomposition.
- **Mismatched Frequencies**: Annual vs quarterly data must be aligned. If mixing, aggregate or interpolate explicitly.
- **Deflation Base**: Verify the price index base year. If the index is `1.0` in the base year, divide directly. If it's `100`, divide by `index/100`.

## Validation Steps
- Print head/tail of cleaned series before filtering.
- Verify `len(cycle1) == len(cycle2)` before correlation.
- Check `p-value` from `pearsonr` to ensure statistical significance.

## Helper Script
Use `scripts/hp_correlation.py` for a robust, reusable implementation of the cleaning, deflation, HP filtering, and correlation steps. Run it when you need to quickly process multiple series or avoid boilerplate errors.