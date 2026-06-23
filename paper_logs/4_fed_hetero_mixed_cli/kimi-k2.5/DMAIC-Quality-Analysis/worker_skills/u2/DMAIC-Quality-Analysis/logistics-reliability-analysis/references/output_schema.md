# Logistics Reliability Output Schema

## STRICT KEY ENFORCEMENT
The verifier performs exact key matching. **Do not add extra fields.**

## Top-Level Structure
```json
{
  "delivery_times": {},
  "damage_rates": {},
  "order_accuracy": {},
  "variability_ranking": [],
  "highest_variability_process": "string",
  "highest_risk_statement": "string",
  "extended_analysis": {},
  "action_plan": {}
}
```

## delivery_times
```json
{
  "mean_hrs": float,
  "sample_std_hrs": float,
  "cv": float,
  "trend_slope": float,
  "trend_t_stat": float,
  "trend_p_value": float,
  "stability": "Stable" | "Unstable",
  "n": int
}
```

## damage_rates
```json
{
  "total_damaged": int,
  "total_shipments": int,
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

## order_accuracy
```json
{
  "mean_error_rate": float,
  "sample_std": float,
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

Note: Use "process" (not "department" or "stage") for logistics context.

## action_plan
```json
{
  "process": "string",
  "prioritized_actions": [{"priority": 1, "action": "string", "owner": "string", "timeline": "string"}],
  "project_codename": "string",
  "momentum_plan_30_60_90": {"30_days": "...", "60_days": "...", "90_days": "..."}
}
```

**IMPORTANT**: `project_codename` must be derived from task context (e.g., filename, task description). Do NOT use hardcoded placeholder values.

## extended_analysis
Counts per process. Matches `n` from each analysis block.

## Key Differences from Other Skills
- Process names: "Delivery Times", "Damage Rates", "Order Accuracy"
- `highest_risk_statement` uses "process" (not "department" or "stage")
- Has `action_plan` instead of `monitoring_plan` or `improvement_plan`
- Damage rates use `total_shipments` (not `total_prescriptions_filled` or `total_lines_reviewed`)
- Order accuracy uses `mean_error_rate` and `sample_std` (no `_rate` suffix on std)
