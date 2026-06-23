# Healthcare Quality Output Schema

## ⚠️ STRICT KEY ENFORCEMENT
The verifier performs exact key matching. **Do not add extra fields.**
- All top-level keys are required.
- Nested keys must match exactly.

## Top-Level Structure
```json
{
  "wait_times": { "mean_minutes", "sample_std_minutes", "cv", "trend_slope", "trend_t_stat", "stability" },
  "medication_errors": { "mean_proportion", "sample_std_proportion", "cv", "overall_rate_pct", "wilson_ci_lower_pct", "wilson_ci_upper_pct", "trend_slope", "trend_t_stat", "stability", "uses_varying_denominators", "target_rate_pct", "capability_vs_target" },
  "readmission_rates": { "mean_rate", "sample_std_rate", "cv", "trend_slope", "trend_t_stat", "stability" },
  "variability_ranking": [{ "process", "cv" }],
  "highest_variability_process": "string",
  "highest_risk_statement": "string",
  "extended_analysis": { "wait_times": {}, "medication_errors": {}, "readmission_rates": {} },
  "monitoring_plan": { "process_to_be_monitored", "inputs", "outputs", "key_performance_indicators", "frequency_of_monitoring", "observation_format", "roles", "reporting_format", "corrective_action_process", "benchmarks", "prioritized_actions" }
}
```

## Key Details
- `stability`: "Stable" or "Unstable" based on `|trend_t_stat| < 2.0`.
- `capability_vs_target`: "Capable" or "Not Capable".
- `highest_risk_statement`: Must exactly follow format `"{Process} is the highest-risk department."`
- `extended_analysis`: Contains `data_points`, `min_value`/`min_proportion`, `max_value`/`max_proportion`, `range` (or `total_errors`/`total_prescriptions_filled` for med errors).
- `monitoring_plan.benchmarks`: Must include `target_readmission_rate_pct`, `max_acceptable_cv` (0.15), `stability_threshold_t_stat` (2.0).
- `monitoring_plan.prioritized_actions`: Array of objects with `priority`, `action`, `owner`, `timeline`.