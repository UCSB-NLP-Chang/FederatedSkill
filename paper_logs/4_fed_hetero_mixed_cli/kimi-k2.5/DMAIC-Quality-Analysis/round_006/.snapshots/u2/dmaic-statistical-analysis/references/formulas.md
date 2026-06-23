# Statistical Formulas & Constants

## I-MR Chart (Individuals & Moving Range)
- **Moving Range (MR)**: `|x_i - x_{i-1}|`
- **MR_bar**: Mean of all MR values.
- **Center Line (CL)**: Mean of individual values.
- **UCL / LCL (Individuals)**: `CL ± 2.667 * MR_bar` (E2 = 2.667 for n=1)
- **MR_UCL**: `3.267 * MR_bar` (D4 = 3.267 for n=2)
- **MR_LCL**: `0` (D3 = 0 for n=1)
- **sigma estimate**: `MR_bar / 1.128` (d2 = 1.128 for n=2)

## Process Capability (Cpk)
- **Sample Std Dev**: `sqrt(sum((x - mean)^2) / (n - 1))` (use `ddof=1`)
- **Cpk_lower**: `(mean - LSL) / (3 * std_dev)`
- Negative Cpk indicates mean is below LSL.

## One-Way ANOVA
- Groups: Weekday (Mon-Fri)
- Use: `scipy.stats.f_oneway(*groups)`
- Report: F-statistic, p-value, highest/lowest mean day

## Linear Regression
- X: `day_index` (1 to N for sorted business days)
- Y: Metric value
- Use: `scipy.stats.linregress(x, y)`
- Report: slope, intercept, r_value, r_squared, p_value

## One-Sample t-Test
- Use: `scipy.stats.ttest_1samp(values, target)`
- 95% CI: `scipy.stats.t.interval(0.95, n-1, loc=mean, scale=sem)`
- Decision: `reject_h0` if p < 0.05, else `fail_to_reject_h0`

## Precision Rules
- p-values < 1e-10: Store as `1e-15` or scientific notation — never `0.0`
- Means, limits, coefficients: round to 4 decimal places unless schema specifies otherwise
- Verify JSON types: all numeric fields must be `float` or `int` as specified

## Key Constants
| Constant | Value | Usage |
|----------|-------|-------|
| d2 (n=2) | 1.128 | sigma_est = MR_bar / d2 |
| E2 (n=1) | 2.667 | I-chart limits = CL ± E2 × MR_bar |
| D3 (n=1) | 0 | MR-chart LCL |
| D4 (n=2) | 3.267 | MR-chart UCL = D4 × MR_bar |
