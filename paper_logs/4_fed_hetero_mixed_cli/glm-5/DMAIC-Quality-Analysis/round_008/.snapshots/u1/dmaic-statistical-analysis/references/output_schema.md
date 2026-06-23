# DMAIC Analyze Output Schema

## ⚠️ STRICT KEY ENFORCEMENT
The verifier performs exact key matching. **Do not add extra fields.**
- Forbidden in `anova_by_weekday`: `df_between`, `df_within`, `ss_between`, etc.
- Forbidden in `imr_summary`: `points` (array), `moving_ranges` (array), `sigma_estimate`.
- Forbidden in `filters`: `response_metric`, `scope`. Use `business_days_only: true` instead.
- Forbidden in `record_counts`: `total_records`, `primary_window_all_days`, `primary_window_business_days`. Use exact keys below.

Required structure for `*_metrics.json` verifier validation.

## Top-Level Keys (All Required)

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
- `business_days_only`: boolean (must be `true`)
- `record_count`: integer

```json
"filters": {
  "primary_analysis_window": {
    "start_date": "2025-01-04",
    "end_date": "2025-03-01",
    "business_days_only": true,
    "record_count": 40
  },
  "imr_analysis_window": {
    "start_date": "2025-01-04",
    "end_date": "2025-02-21",
    "business_days_only": true,
    "record_count": 35
  }
}
```

**Critical**: I-MR window must end **before** Analyze phase data begins.

**Field Names Must Match Exactly**:
- Use `primary_analysis_window`, NOT `primary_window`
- Use `imr_analysis_window`, NOT `imr_window`
- Use `start_date`/`end_date`, NOT `start`/`end`

## Record Counts

```json
"record_counts": {
  "total_records_in_source": 100,
  "primary_window_records": 40,
  "imr_window_records": 35
}
```

**Field Names Must Match Exactly**:
- Use `total_records_in_source`, NOT `total_records`
- Use `primary_window_records`, NOT `primary_window_business_days`
- Use `imr_window_records`, NOT `imr_window_business_days`

## Charter Metrics

```json
"charter_metrics": {
  "baseline_value": 500,
  "target_value": 560,
  "current_mean_value": 542.75
}
```

## ANOVA by Weekday

```json
"anova_by_weekday": {
  "weekday_means": {
    "Monday": 540.123,
    "Tuesday": 545.456,
    "Wednesday": 542.789,
    "Thursday": 538.012,
    "Friday": 544.321
  },
  "p_value": 0.006123,
  "f_statistic": 3.4567,
  "highest_mean_day": "Tuesday",
  "lowest_mean_day": "Thursday"
}
```

- `weekday_means`: object with keys Monday-Friday, values to 3 decimals
- `p_value`: float (use actual value, not 0.0 unless truly zero)
- `f_statistic`: float, 4 decimals
- `highest_mean_day`/`lowest_mean_day`: weekday name string
- **Do NOT add** `df_between`, `df_within`, or other extra fields

## I-MR Summary

```json
"imr_summary": {
  "points": 35,
  "center_line": 542.75,
  "ucl": 560.12,
  "lcl": 525.38,
  "mr_bar": 6.45,
  "mr_ucl": 21.05
}
```

- `points`: integer (window size), NOT an array of values
- `center_line`: mean of individuals
- `ucl`/`lcl`: `center_line ± 3 * (mr_bar / 1.128)`
- `mr_bar`: average moving range
- `mr_ucl`: `3.267 * mr_bar`
- **Do NOT add** `points` array or `moving_ranges` array

**Formula**: sigma_estimate = mr_bar / 1.128 (d2 constant for n=2)

## Regression on Day Index

```json
"regression_day_index": {
  "slope": 0.123456,
  "intercept": 538.123,
  "r_value": 0.4567,
  "r_squared": 0.2085,
  "p_value": 0.022123,
  "n_observations": 40
}
```

- `slope`: 6 decimal precision
- `intercept`: 3 decimals
- `r_value`: Pearson correlation, 4 decimals
- `r_squared`: 4 decimals
- `p_value`: actual value
- `n_observations`: integer

## t-Test vs Target

```json
"ttest_vs_target": {
  "target": 560,
  "n": 40,
  "mean_value": 542.75,
  "std_dev": 12.345,
  "t_stat": -8.7654,
  "p_value": 0.000012,
  "ci95_low": 538.876,
  "ci95_high": 546.624,
  "decision": "reject_h0"
}
```

- `target`: the hypothesis target value
- `n`: sample size
- `mean_value`: sample mean
- `std_dev`: sample standard deviation (n-1, ddof=1)
- `t_stat`: 4 decimals
- `p_value`: actual value
- `ci95_low`/`ci95_high`: 95% confidence interval bounds
- `decision`: "reject_h0" if p < 0.05, else "fail_to_reject_h0"

## Capability Against LSL

```json
"capability_against_lsl": {
  "lsl": 560,
  "mean": 542.75,
  "std_dev_sample": 12.345,
  "cpk_lower": -0.4654
}
```

- `lsl`: Lower Specification Limit
- `mean`: process mean
- `std_dev_sample`: sample sigma (n-1)
- `cpk_lower`: `(mean - lsl) / (3 * sigma_sample)`

**Note**: Negative Cpk indicates mean is below LSL.

## Common Verifier Failures

1. **Wrong field names**: `primary_window` instead of `primary_analysis_window`
2. **Wrong nested fields**: `start`/`end` instead of `start_date`/`end_date`
3. **Extra fields added**: `points` array, `moving_ranges` array, `df_between`, etc.
4. **Missing business_days_only**: Must be explicit boolean `true`
5. **Wrong decimal precision**: Follow specifications above
6. **Population vs Sample std dev**: Must use n-1 denominator (ddof=1)
7. **Date misalignment**: I-MR window must end before Analyze phase data
8. **Weekend inclusion**: Record counts must match Mon-Fri only
9. **p-value out of range**: Must be in [0, 1]; use scipy.stats
