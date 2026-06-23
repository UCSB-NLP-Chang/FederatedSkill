# Pipeline Performance Output Schema

## JSON Structure

Required top-level keys:
- `build_duration` — object with: mean, sample_std, cv, trend_slope, t_statistic, stability
- `bug_rate` — object with: total_bugs, total_lines, overall_rate_pct, wilson_ci_95, cv, stability, uses_varying_denominators
- `deployment_failures` — object with: mean, sample_std, cv, trend_slope, t_statistic, stability
- `variability_ranking` — array of {process: string, cv: float}, sorted CV descending
- `highest_variability_process` — string, name of highest-CV process
- `highest_risk_statement` — string describing the highest-risk finding
- `improvement_plan` — object with project_codename, milestones_30_days, milestones_60_days, milestones_90_days

## Markdown Brief Structure

- `# Summary of Findings` — include summary table
- `# Most Significant Risks` — detail top risks
- `# Prioritized Corrective Actions` — exactly 5 actions
- `# Improvement Plan` — 5 subsections + 30/60/90-day milestones
