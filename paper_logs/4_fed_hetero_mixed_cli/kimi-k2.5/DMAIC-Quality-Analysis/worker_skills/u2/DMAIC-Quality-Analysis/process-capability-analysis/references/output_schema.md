# Process Capability Output Schema

## STRICT KEY ENFORCEMENT
The verifier performs exact key matching. **Do not add extra fields.**

## Top-Level Structure
```json
{
  "task_duration": {},
  "failure_rate": {},
  "system_errors": {},
  "variability_ranking": [],
  "highest_variability_process": "string",
  "highest_risk_statement": "string",
  "extended_analysis": {},
  "monitoring_plan": {}
}
```

## task_duration
```json
{
  "mean_min": float,
  "sample_std_min": float,
  "cv": float,
  "trend_slope": float,
  "trend_t_stat": float,
  "trend_p_value": float,
  "stability": "Stable" | "Unstable",
  "n": int
}
```

## failure_rate
```json
{
  "total_failures": int,
  "total_units_processed": int,
  "overall_rate_pct": float,
  "wilson_ci_lower_pct": float,
  "wilson_ci_upper_pct": float,
  "mean_proportion": float,
  "sample_std_proportion": float,
  "cv": float,
  "trend_slope": float,
  "trend_t_stat": float,
  "trend_p_value": float,
  "stability": "Stable" | "Unstable",
  "uses_varying_denominators": true,
  "target_rate_pct": float,
  "capability_vs_target": "Capable" | "Not Capable",
  "n": int
}
```

## system_errors
```json
{
  "mean_rate": float,
  "sample_std_rate": float,
  "cv": float,
  "trend_slope": float,
  "trend_t_stat": float,
  "trend_p_value": float,
  "stability": "Stable" | "Unstable",
  "n": int
}
```

## variability_ranking
Array sorted by CV descending: `[{"rank": 1, "process": "...", "cv": ...}]`

## highest_risk_statement
**EXACT FORMAT**: `"{Process} is the highest-risk process."`

Note: Use "process" (not "department" or "stage") for this context.

## monitoring_plan
```json
{
  "process_to_be_monitored": "string",
  "inputs": ["string"],
  "outputs": ["string"],
  "key_performance_indicators": ["string"],
  "frequency_of_monitoring": "string",
  "observation_format": "string",
  "roles": ["string"],
  "reporting_format": "string",
  "corrective_action_process": "string",
  "benchmarks": {
    "target_rate_pct": float,
    "max_acceptable_cv": 0.15,
    "stability_threshold_t_stat": 2.0
  },
  "prioritized_actions": [{"priority": 1, "action": "string", "owner": "string", "timeline": "string"}],
  "checklist": ["string"],
  "momentum_plan_30_60_90": {"30_days": "...", "60_days": "...", "90_days": "..."},
  "project_codename": "string"
}
```

**IMPORTANT**: 
- `checklist` must have 5-9 items
- `project_codename` must be derived from task context (e.g., filename, task description). Do NOT use hardcoded placeholder values.
- `momentum_plan_30_60_90` must have keys: `30_days`, `60_days`, `90_days`

## extended_analysis
Counts per process. Matches `n` from each analysis block.

## Key Differences from Other Skills
- Process names: "Task Duration", "Failure Rate", "System Errors"
- `highest_risk_statement` uses "process"
- Has `monitoring_plan` with `checklist` and `momentum_plan_30_60_90`
- Failure rate uses `total_units_processed` (not `total_shipments` or `total_prescriptions_filled`)
- Task duration uses `mean_min` and `sample_std_min` (minute-based)
- System errors uses `mean_rate` and `sample_std_rate`
