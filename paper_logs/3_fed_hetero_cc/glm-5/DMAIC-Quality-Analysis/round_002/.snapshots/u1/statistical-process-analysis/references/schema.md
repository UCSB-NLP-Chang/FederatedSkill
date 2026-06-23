# Statistical Process Analysis Output Schema

Complete JSON schema reference for `compute_spc.py` output.

## Top-Level Structure

```json
{
  "source_file": "string",
  "filters": { ... },
  "record_counts": { ... },
  "charter_metrics": { ... },
  "anova_by_weekday": { ... },
  "imr_summary": { ... },
  "regression_day_index": { ... },
  "ttest_vs_target": { ... },
  "capability_against_lsl": { ... }
}
```

## Field Details

### filters
- `primary_date_range`: String, format "YYYY-MM-DD to YYYY-MM-DD (inclusive)"
- `imr_date_range`: String, format "YYYY-MM-DD to YYYY-MM-DD (inclusive)"
- `business_days_only`: Boolean (always true)
- `response_metric`: String, column name analyzed
- `regression_predictor`: String (always "day_index")

### record_counts
- `total_records`: Integer, all rows in CSV
- `primary_window_records`: Integer, all rows in primary date range
- `primary_window_business_days`: Integer, business days in primary range
- `imr_window_business_days`: Integer, business days in IMR range

### charter_metrics
- `baseline_value`: Number
- `target_value`: Number
- `current_mean_value`: Number

### anova_by_weekday
- `weekday_means`: Object mapping "Monday"-"Friday" to mean values
- `f_statistic`: Number
- `p_value`: Number
- `highest_mean_day`: String (e.g., "Wednesday")
- `lowest_mean_day`: String (e.g., "Monday")

### imr_summary
- `points`: Integer, count of IMR window observations
- `center_line`: Number, mean of IMR window
- `ucl`: Number, upper control limit (mean + 2.66*MRbar)
- `lcl`: Number, lower control limit (mean - 2.66*MRbar)
- `mr_bar`: Number, average moving range
- `mr_ucl`: Number, MR chart UCL (3.267 * mr_bar)

### regression_day_index
- `slope`: Number, panels per day
- `intercept`: Number
- `r_value`: Number, correlation coefficient
- `r_squared`: Number
- `p_value`: Number, significance of slope
- `n_observations`: Integer

### ttest_vs_target
- `n`: Integer, sample size
- `mean_value`: Number
- `t_stat`: Number
- `p_value`: Number
- `ci95_low`: Number, lower bound of 95% CI
- `ci95_high`: Number, upper bound of 95% CI
- `decision`: String, either "reject_h0" or "fail_to_reject_h0"

### capability_against_lsl
- `lsl`: Number, lower specification limit (target value)
- `std_dev_sample`: Number, sample standard deviation
- `cpk_lower`: Number, (mean - LSL) / (3 * std_dev)

## Usage Notes
- All numeric values are raw floats, not rounded
- Weekday names are capitalized English day names
- Decision field uses snake_case strings exactly as shown
