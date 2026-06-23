# DevOps Pipeline Output Schema

## STRICT KEY ENFORCEMENT
The verifier performs exact key matching. **Do not add extra fields.**

## Top-Level Structure
```json
{
  "build_duration": {},
  "bug_rate": {},
  "deployment_failures": {},
  "variability_ranking": [],
  "highest_variability_process": "string",
  "highest_risk_statement": "string",
  "extended_analysis": {},
  "improvement_plan": {}
}
```

## build_duration
```json
{
  "mean_sec": float,
  "sample_std_sec": float,
  "cv": float,
  "trend_slope": float,
  "trend_t_stat": float,
  "trend_p_value": float,
  "stability": "Stable" | "Unstable",
  "n": int
}
```

## bug_rate
```json
{
  "total_bugs": int,
  "total_lines_reviewed": int,
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

## deployment_failures
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
**EXACT FORMAT**: `"{Process} is the highest-risk stage."`

Note: Use "stage" (not "department") for DevOps context.

## improvement_plan
```json
{
  "process": "string",
  "methodology": "string",
  "root_cause_approach": "string",
  "incident_response_plan": "string",
  "technical_debt_assessment": "string",
  "prioritized_actions": [{"priority": 1, "action": "string", "owner": "string", "timeline": "string"}],
  "project_codename": "string",
  "momentum_plan_30_60_90": {"30_days": "...", "60_days": "...", "90_days": "..."}
}
```

**IMPORTANT**: `project_codename` should NOT be hardcoded. Pass via CLI argument `--project-codename` or let the script auto-generate a generic name based on the highest-risk process.

## extended_analysis
Counts per process. Matches `n` from each analysis block.

## Forbidden Fields (DO NOT ADD)

- `df_between`, `df_within` (ANOVA internal fields)
- `points` as array in `imr_summary` context
- `mr_lcl` (MR chart has no LCL)
- Any field not listed above
