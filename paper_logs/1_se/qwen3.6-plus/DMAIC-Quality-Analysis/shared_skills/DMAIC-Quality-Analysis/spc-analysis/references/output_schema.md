# Expected Output Schema

## JSON Metrics (`soc_analyze_metrics.json`)
Must contain these top-level keys:
- `source_file`: string
- `filters`: object with `date_range_primary`, `date_range_imr`, `business_days_only`, `response_metric`
- `record_counts`: object with `total_rows_in_file`, `primary_window_all_days`, `primary_window_business_days`, `imr_window_business_days`
- `charter_metrics`: object with `baseline_value`, `target_value`, `current_mean_value`
- `anova_by_weekday`: object with `weekday_means`, `p_value`, `highest_mean_day`, `lowest_mean_day`, `f_statistic`, `df_between`, `df_within`
- `imr_summary`: object with `points`, `center_line`, `ucl`, `lcl`, `mr_bar`, `mr_ucl`
- `regression_day_index`: object with `slope`, `intercept`, `r_value`, `p_value`, `n`
- `ttest_vs_target`: object with `n`, `mean_value`, `t_stat`, `p_value`, `ci95_low`, `ci95_high`, `decision`
- `capability_against_lsl`: object with `lsl`, `std_dev_sample`, `cpk_lower`

## Markdown Brief (`soc_analyze_brief.md`)
Required sections in order:
1. `# SOC Analyze Tollgate Brief`
2. `## Project Charter` (table with Baseline, Target, Current Mean, Primary Window, Response Metric)
3. `## Statistical Analysis`
   - `### One-Way ANOVA (ResolvedAlerts by Weekday)`
   - `### I-MR Control Chart (...)`
   - `### Linear Regression (ResolvedAlerts ~ day_index)`
   - `### One-Sample t-Test vs Target (...)`
   - `### Process Capability (Cpk)`
4. `## A3 Summary` (Current State, Root Causes, Operational Impacts [3 items], Countermeasures)
5. `## Timeline` (Define, Measure, Analyze dates)
6. `## Next Steps` (2 actions with owners and due dates)

**Consistency Rule**: Every number in the Markdown must exactly match the JSON. Narrative conclusions must align with statistical significance thresholds (p < 0.05).
