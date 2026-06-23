# SPC & Statistical Formulas

## I-MR Control Chart
- **Center Line (CL)**: Mean of individual values
- **Mean Moving Range (MR̄)**: Mean of absolute differences between consecutive points
- **Individual Limits**: UCL = CL + 2.66 × MR̄, LCL = CL - 2.66 × MR̄
- **MR Limit**: MR_UCL = 3.267 × MR̄
- Constants 2.66 and 3.267 are derived from d2 and D4 for subgroup size 2. Do NOT substitute standard deviation-based limits.

## One-Way ANOVA (Weekday)
- Groups: Monday through Friday (business days only)
- Use `scipy.stats.f_oneway(group1, group2, ...)` directly
- F = MSB / MSW; p-value from F-distribution with df_b = k-1, df_w = N-k

## Linear Regression
- Predictor: Day index (0, 1, 2...)
- Use `scipy.stats.linregress(x, y)` directly
- Returns slope, intercept, r_value, p_value, std_err
- R² = r_value²

## One-Sample t-Test
- Use `scipy.stats.ttest_1samp(sample, popmean=target_value)` directly
- 95% CI: use `scipy.stats.t.interval(0.95, df=n-1, loc=mean, scale=se_mean)`
- Do NOT use z=1.96 for CI on small samples

## Process Capability (Cpk)
- Cpk_lower = (x̄ - LSL) / (3σ)
- Cpk_upper = (USL - x̄) / (3σ)
- Report the minimum. Negative values indicate mean outside spec.
