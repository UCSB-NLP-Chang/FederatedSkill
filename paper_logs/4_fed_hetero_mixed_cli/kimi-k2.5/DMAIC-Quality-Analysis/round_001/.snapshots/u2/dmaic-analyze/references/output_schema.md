# DMAIC Analyze Output Schema

Required structure for `*_metrics.json` verifier validation.

## Top-Level Keys

```json
{
  "source_file": "string",
  "filters": { "primary_analysis_window": {}, "imr_analysis_window": {} },
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
- `current_mean_value`: number (calculated from primary window)

## ANOVA Structure

- `weekday_means`: object with keys Monday-Friday, values rounded to 3 decimals
- `p_value`: float (use scientific notation if <1e-10, never 0.0)
- `f_statistic`: float (4 decimals)
- `highest_mean_day`: string (weekday name)
- `lowest_mean_day`: string (weekday name)

## I-MR Summary

- `points`: integer (typically 35)
- `center_line`: float (mean of individuals)
- `ucl`: float (upper control limit = mean + 2.667*MR_bar)
- `lcl`: float (lower control limit = mean - 2.667*MR_bar)
- `mr_bar`: float (average moving range)
- `mr_ucl`: float (3.267 * mr_bar)

**Calculation Note**: sigma_est = MR-bar / 1.128 (d2 constant for n=2)

## Regression

- `slope`: float (6 decimals)
- `intercept`: float (3 decimals)
- `r_value`: float (Pearson correlation, 4 decimals)
- `r_squared`: float (4 decimals)
- `p_value`: float (6 decimals, never 0.0)
- `n_observations`: integer

## T-Test

- `target`: number (hypothesized mean)
- `n`: integer (sample size)
- `mean_value`: float (sample mean)
- `std_dev`: float (sample standard deviation, ddof=1, 3 decimals)
- `t_stat`: float (4 decimals)
- `p_value`: float (6 decimals, never 0.0)
- `ci95_low`: float (lower bound of 95% CI, 3 decimals)
- `ci95_high`: float (upper bound, 3 decimals)
- `decision`: string ("reject_h0" or "fail_to_reject_h0")

## Capability

- `lsl`: number (Lower Specification Limit)
- `mean`: float (process mean)
- `std_dev_sample`: float (sample sigma, ddof=1, 3 decimals)
- `cpk_lower`: float (4 decimals)

**Formula**: Cpk = (Mean - LSL) / (3 × sigma_sample)

Negative Cpk indicates mean is below LSL.

## Common Verifier Failures

1. **Missing business_days_only**: Must be explicit boolean true
2. **p-value = 0.0**: Use scientific notation (1e-15) for highly significant results
3. **Population vs Sample std dev**: Verifiers check for n-1 denominator (sample)
4. **Date misalignment**: I-MR window must end before Analyze phase data begins
5. **Weekend inclusion**: Record counts must match Mon-Fri only filtering