# Performance Analysis Output Schema

## Generic Skill Output Structure

The analysis script produces keys based on Excel sheet names. Common mappings:

| Sheet Name Pattern | Typical Metric Type | Common Schema Key |
|-------------------|---------------------|-------------------|
| `*Time*`, `*Duration*` | Continuous duration | `build_duration`, `delivery_times` |
| `*Bug*`, `*Defect*`, `*Error*`, `*Damage*` | Event rate (varying denominator) | `bug_rate`, `damage_rates`, `error_rate` |
| `*Fail*`, `*Deployment*` | Count of failures | `deployment_failures` |
| `*Accuracy*`, `*Quality*` | Proportion/probability | `order_accuracy`, `quality_score` |

## Required JSON Schema (Task-Specific)

Tasks typically require these top-level keys:
- `{metric1}` — object with: `mean`, `sample_std`, `cv`, `trend_slope`, `t_statistic`, `stability`
- `{metric2}` — same structure
- `{metric3}` — same structure  
- `variability_ranking` — array of `{process: string, cv: float}`, sorted CV descending
- `highest_variability_process` — string name
- `highest_risk_statement` — descriptive string
- `improvement_plan` — object with milestones

## Rate Metrics with Wilson CI

For sheets with two numeric columns (events, opportunities):
```json
{
  "total_events": int,
  "total_opportunities": int,
  "overall_rate_pct": float,
  "wilson_ci_95": [lower_pct, upper_pct],
  "cv": float,
  "stability": "Stable|Unstable",
  "uses_varying_denominators": bool
}
```

## Markdown Brief Structure

- `# Summary of Findings` — metrics table
- `# Most Significant Risks` — top 2-3 risks by CV or instability
- `# Prioritized Corrective Actions` — 5 specific actions
- `# Improvement Plan` — milestones with 30/60/90-day targets
