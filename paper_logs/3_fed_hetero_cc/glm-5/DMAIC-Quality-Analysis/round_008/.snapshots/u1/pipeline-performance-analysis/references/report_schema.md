# Pipeline Report Schema

## JSON Structure (`pipeline_performance_report.json`)

### Required Top-Level Keys
- `build_duration`
- `bug_rate`
- `deployment_failures`
- `variability_ranking`
- `highest_variability_process`
- `highest_risk_statement`
- `improvement_plan`

### Full Schema
```json
{
  "build_duration": {
    "mean": float,
    "sample_std": float,
    "cv": float,
    "trend_slope": float,
    "t_statistic": float,
    "stability": "Stable|Trending"
  },
  "bug_rate": {
    "total_bugs": int,
    "total_lines": int,
    "overall_rate_pct": float,
    "wilson_ci_lower": float,
    "wilson_ci_upper": float,
    "cv": float,
    "target_rate_pct": float,
    "capability_vs_target": "Capable|Not Capable",
    "uses_varying_denominators": true
  },
  "deployment_failures": {
    "mean": float,
    "sample_std": float,
    "cv": float,
    "trend_slope": float,
    "t_statistic": float,
    "stability": "Stable|Trending"
  },
  "variability_ranking": [
    {"process": "Deployment Failures", "coefficient_of_variation": float},
    {"process": "Bug Rate", "coefficient_of_variation": float},
    {"process": "Build Duration", "coefficient_of_variation": float}
  ],
  "highest_variability_process": "string",
  "highest_risk_statement": "string",
  "improvement_plan": {
    "project_codename": "string",
    "milestones_30_days": "string",
    "milestones_60_days": "string",
    "milestones_90_days": "string"
  }
}
```

## Markdown Structure (`pipeline_performance_brief.md`)

### Required Sections
1. `# Summary of Findings` — include summary table
2. `# Most Significant Risks`
3. `# Prioritized Corrective Actions` — exactly 5 actions (numbered list)
4. `# Improvement Plan` — 5 subsections + 30/60/90-day milestones

### Summary Table Format
| Process | Mean | Std | CV | Stability |
|---------|------|-----|----|-----------| 
| Build Duration | X | X | X | Stable/Trending |
| Bug Rate | X | X | X | Stable/Trending |
| Deployment Failures | X | X | X | Stable/Trending |

### Corrective Actions Format
1. [Action 1]
2. [Action 2]
3. [Action 3]
4. [Action 4]
5. [Action 5]

### Improvement Plan Subsections
1. Problem Statement
2. Goal Definition
3. Root Cause Analysis
4. Countermeasures
5. Implementation Timeline
