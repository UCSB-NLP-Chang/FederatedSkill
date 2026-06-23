# Healthcare Quality Analysis Output Schema

## Top-Level Structure

```json
{
  "wait_times": {},
  "medication_errors": {},
  "readmission_rates": {},
  "variability_ranking": [],
  "highest_variability_process": "string",
  "highest_risk_statement": "string",
  "monitoring_plan": {},
  "extended_analysis": {}
}
```

## wait_times

```json
{
  "mean": float,
  "sample_std": float,
  "cv": float,
  "n": int,
  "trend": {
    "slope": float,
    "intercept": float,
    "t_statistic": float,
    "p_value": float,
    "r_squared": float,
    "stability": "Stable" | "Unstable",
    "n_observations": int
  }
}
```

## medication_errors

```json
{
  "total_errors": int,
  "total_prescriptions_filled": int,
  "overall_rate_percent": float,
  "wilson_95_ci": {
    "lower": float,
    "upper": float
  },
  "mean_of_per_point_proportions": float,
  "sample_std_of_per_point_proportions": float,
  "cv": float,
  "uses_varying_denominators": true,
  "target_rate_pct": float,
  "capability_vs_target": "Capable" | "Not Capable",
  "trend": {
    "slope": float,
    "t_statistic": float,
    "p_value": float,
    "r_squared": float,
    "stability": "Stable" | "Unstable",
    "n_observations": int
  }
}
```

**CRITICAL**: Must use Wilson score interval, not normal approximation.

## readmission_rates

Same structure as `wait_times`.

## variability_ranking

Array sorted by CV descending (highest first):

```json
[
  {
    "rank": 1,
    "process": "Readmission Rates",
    "cv": 0.3478
  }
]
```

## highest_variability_process

String name of the process with highest CV (e.g., "Readmission Rates").

## highest_risk_statement

**EXACT FORMAT REQUIRED**:
"`{Process}` is the highest-risk department."

Example: "Readmission Rates is the highest-risk department."

## monitoring_plan

```json
{
  "process_to_be_monitored": string,
  "inputs": [string],
  "outputs": [string],
  "key_performance_indicators": [string],
  "frequency_of_monitoring": string,
  "observation_format": string,
  "roles": {
    "data_collector": string,
    "analyst": string,
    "reviewer": string
  },
  "reporting_format": string,
  "corrective_action_process": string,
  "benchmarks": object,
  "prioritized_actions": [string],
  "checklist": [string]
}
```

**Checklist must have 5-9 items.**

## extended_analysis

Raw data arrays for verification:

```json
{
  "wait_times_per_point": [float],
  "medication_errors_per_point_proportions": [float],
  "readmission_rates_per_point": [float]
}
```

## Common Failures

1. **Missing Wilson CI**: Medication errors must have Wilson interval, not standard CI
2. **Wrong stability logic**: Stable means p >= 0.05 (fail to reject null of zero slope)
3. **Population std used**: Must use sample std (ddof=1) for CV
4. **Missing exact sentence**: Brief must contain "{Process} is the highest-risk department."
5. **Checklist too short**: Must have 5-9 items
6. **Rounded values**: Pass raw floats to JSON, do not round
7. **Wrong field names**: Use exact names in schema (e.g., `t_statistic` not `t_stat`, `sample_std` not `std`)
