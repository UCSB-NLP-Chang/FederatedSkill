# SPC & Statistical Formulas

## I-MR Control Chart
- **Center Line (CL)**: Mean of individual values
- **Mean Moving Range (MR̄)**: Mean of absolute differences between consecutive points
- **Individual Limits**: UCL = CL + 2.66 × MR̄, LCL = CL - 2.66 × MR̄
- **MR Limit**: MR_UCL = 3.267 × MR̄

## One-Way ANOVA (Weekday)
- Groups: Monday through Friday
- F = MSB / MSW
- p-value from F-distribution with df_between = k-1, df_within = N-k

## Linear Regression
- Predictor: Day index (0, 1, 2...)
- Slope p-value from t-distribution with df = n-2
- R² = 1 - (SS_res / SS_tot)

## One-Sample t-Test
- t = (x̄ - μ₀) / (s / √n)
- 95% CI: Use `scipy.stats.t.interval(0.95, df=n-1, loc=mean, scale=se)` for t-distribution
- Do NOT use z=1.96 for CI on small samples

## Process Capability (Cpk)
- Cpk_lower = (x̄ - LSL) / (3σ)
- Cpk_upper = (USL - x̄) / (3σ)
- Report the minimum. Negative values indicate mean outside spec.
