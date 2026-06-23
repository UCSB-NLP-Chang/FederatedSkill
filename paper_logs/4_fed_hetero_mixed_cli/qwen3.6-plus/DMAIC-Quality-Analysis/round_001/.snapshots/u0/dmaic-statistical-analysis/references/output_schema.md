# DMAIC Analyze Output Schema

Required structure for `*_metrics.json` verifier validation.

## Top-Level Keys

```json
{
  "source_file": "string",
  "filters": {
    "primary_analysis_window": {},
    "imr_analysis_window": {}
  },
  "record_counts": {},
  "charter_metrics": {},
  "anova_by_weekday": {},
  "imr_summary": {},
  "regression_day_index": {},
  "ttest_vs_target": {},
  "capability_against_lsl": {}
}
```

## Filter Windows

Both windows require:
- `start_date`: ISO date string (YYYY-MM-DD)
- `end_date`: ISO date string
- `business_days_only`: boolean (must be true)
- `record_count`: integer

## Charter Metrics

- `baseline_value`: number (original performance)
- `target_value`: number (goal)
- `current_mean_value`: number (4 decimal places)

## ANOVA Structure

- `weekday_means`: object with keys Monday-Friday, values rounded to 4 decimals
- `p_value`: float (6 decimal precision, use 1e-15 for highly significant)
- `f_statistic`: float (4 decimals)
- `highest_mean_day`: string (weekday name)
- `lowest_mean_day`: string (weekday name)

## I-MR Summary

- `points`: array of floats (individual values)
- `center_line`: float (mean of individuals, 4 decimals)
- `ucl`: float (upper control limit, 4 decimals)
- `lcl`: float (lower control limit, 4 decimals)
- `mr_bar`: float (average moving range, 4 decimals)
- `mr_ucl`: float (3.267 × mr_bar, 4 decimals)

**Formula**: sigma_est = MR-bar / 1.128; UCL/LCL = mean ± 3×sigma_est

## Regression

- `slope`: float (6 decimals)
- `intercept`: float (4 decimals)
- `r_value`: float (Pearson correlation, 4 decimals)
- `r_squared`: float (4 decimals)
- `p_value`: float (6 decimals)
- `n_observations`: integer

## T-Test

- `target`: number (hypothesized mean)
- `n`: integer (sample size)
- `mean_value`: float (4 decimals)
- `std_dev`: float (sample std dev, 4 decimals)
- `t_stat`: float (4 decimals)
- `p_value`: float (6 decimals)
- `ci95_low`: float (lower bound of 95% CI, 4 decimals)
- `ci95_high`: float (upper bound, 4 decimals)
- `decision`: string ("reject_h0" or "fail_to_reject_h0")

## Capability

- `lsl`: number (Lower Specification Limit)
- `mean`: float (process mean, 4 decimals)
- `std_dev_sample`: float (sample sigma, 4 decimals)
- `cpk_lower`: float (4 decimals)

**Formula**: Cpk = (Mean - LSL) / (3 × sigma_sample)

Negative Cpk indicates mean is below LSL.

## Common Verifier Failures

1. **Missing business_days_only**: Must be explicit boolean true
2. **Wrong decimal precision**: Follow rounding specifications above
3. **Population vs Sample std dev**: Verifiers check for n-1 denominator
4. **Date misalignment**: I-MR window must end before Analyze phase data
5. **Weekend inclusion**: Record counts must match Mon-Fri only filtering
6. **p-value = 0.0**: Use 1e-15 for highly significant results
