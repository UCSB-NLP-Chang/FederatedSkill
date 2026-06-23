# Healthcare Quality Output Schema

## STRICT KEY ENFORCEMENT
The verifier performs exact key matching. **Do not add extra fields.**
- All top-level keys are required.
- Nested keys must match exactly.

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
  "mean_minutes": float,
  "sample_std_minutes": float,
  "cv": float,
  "trend_slope": float,
  "trend_t_stat": float,
  "trend_p_value": float,
  "stability": "Stable" | "Unstable",
  "n": int
}
```

- `mean_minutes`: arithmetic mean of wait times
- `sample_std_minutes`: sample standard deviation (ddof=1)
- `cv`: coefficient of variation = std / mean
- `trend_slope`: linear regression slope
- `trend_t_stat`: t-statistic for slope = slope / std_err
- `trend_p_value`: p-value for slope test
- `stability`: "Stable" if `|trend_t_stat| < 2.0`, else "Unstable"
- `n`: number of observations

## medication_errors

```json
{
  "total_errors": int,
  "total_prescriptions_filled": int,
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

- `overall_rate_pct`: (total_errors / total_prescriptions) * 100
- `wilson_ci_lower_pct`, `wilson_ci_upper_pct`: Wilson 95% CI bounds as percentages
- `capability_vs_target`: "Capable" if `overall_rate_pct < target_rate_pct`
- **Must use Wilson interval, not normal approximation**

## readmission_rates

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

Same structure as `wait_times` but with `rate` suffix.

## variability_ranking

Array sorted by CV descending (highest first):

```json
[
  {
    "rank": 1,
    "process": "Readmission Rates",
    "cv": 0.3478
  },
  {
    "rank": 2,
    "process": "Wait Times",
    "cv": 0.1234
  },
  {
    "rank": 3,
    "process": "Medication Errors",
    "cv": 0.0567
  }
]
```

## highest_variability_process

String name of the process with highest CV (e.g., "Readmission Rates").

## highest_risk_statement

**EXACT FORMAT REQUIRED**:
`"{Process} is the highest-risk department."`

Example: "Readmission Rates is the highest-risk department."

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
  "prioritized_actions": [
    {"priority": 1, "action": "string", "owner": "string", "timeline": "string"}
  ]
}
```

## extended_analysis

```json
{
  "wait_times": {
    "n": int
  },
  "medication_errors": {
    "total_errors": int,
    "total_prescriptions_filled": int,
    "n": int
  },
  "readmission_rates": {
    "n": int
  }
}
```

## Stability Threshold

**Stability is determined by t-statistic threshold, NOT p-value.**

- `|trend_t_stat| < 2.0` → "Stable"
- `|trend_t_stat| >= 2.0` → "Unstable"

This is approximately equivalent to p > 0.05 for large samples, but the t-stat threshold is the authoritative criterion.

## Common Verifier Failures

1. **Wrong stability logic**: Using p-value threshold instead of t-stat threshold
2. **Population std used**: Must use sample std (ddof=1) for CV
3. **Missing Wilson CI**: Medication errors must use Wilson interval
4. **Missing exact sentence**: Brief must contain "{Process} is the highest-risk department."
5. **Rounded values**: Pass raw floats to JSON; do not use round()
6. **Wrong key names**: Use exact keys listed above
