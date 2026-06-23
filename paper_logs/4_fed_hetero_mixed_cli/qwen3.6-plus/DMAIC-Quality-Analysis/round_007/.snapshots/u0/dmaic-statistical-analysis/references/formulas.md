# Statistical Formulas & Constants

## I-MR Chart (Individuals & Moving Range)

- **Moving Range (MR)**: `|x_i - x_{i-1}|`
- **MR_bar**: Mean of all MR values.
- **Center Line (CL)**: Mean of individual values.
- **d2 constant**: 1.128 (for subgroup size n=2)
- **Sigma estimate**: `MR_bar / 1.128`
- **UCL / LCL (Individuals)**: `CL ± 3 × sigma_est = CL ± (3/1.128) × MR_bar ≈ CL ± 2.667 × MR_bar`
- **MR_UCL**: `3.267 × MR_bar`
- **MR_LCL**: `0` (for individuals chart)

Constants: E2 = 2.667, D3 = 0, D4 = 3.267 (for n=1 individual points)

## Process Capability (Cpk)

- **Sample Std Dev**: `sqrt(sum((x - mean)^2) / (n - 1))` — use ddof=1
- **Cpk_lower**: `(mean - LSL) / (3 × std_dev)`
- **Cpk_upper**: `(USL - mean) / (3 × std_dev)`
- Negative Cpk indicates mean is below LSL (or above USL).

## One-Way ANOVA

- Groups: Weekday (Monday-Friday)
- Test: `scipy.stats.f_oneway(*groups)`
- Report: F-statistic, p-value, highest/lowest mean day.

## Linear Regression

- X: `day_index` (1 to N for sorted business days)
- Y: Metric value
- Test: `scipy.stats.linregress(x, y)`
- Report: slope, intercept, r_value, r_squared, p_value

## One-Sample t-Test

- Test: `scipy.stats.ttest_1samp(values, target)`
- 95% CI: `scipy.stats.t.interval(0.95, n-1, loc=mean, scale=sem)`
- Decision: `reject_h0` if p < 0.05, else `fail_to_reject_h0`

## Precision Rules

- p-values < 1e-10 should be stored as `1e-15` to avoid `0.0` truncation.
- Means, limits: 4 decimal places.
- Slope, intercept: 6 and 4 decimal places respectively.
- R-values: 4 decimal places.
