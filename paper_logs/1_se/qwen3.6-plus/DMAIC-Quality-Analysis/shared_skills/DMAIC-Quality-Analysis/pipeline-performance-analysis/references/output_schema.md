# Expected Output Schema & Structure

## JSON Metrics (`pipeline_performance_report.json`)
Top-level keys:
- `build_duration`, `bug_rate`, `deployment_failures` (or snake_case sheet names): objects containing metric stats.
  - Standard: `mean`, `sample_std`, `coefficient_of_variation`, `trend_slope`, `trend_t_stat`, `stability`, `n_observations`
  - Proportion: `mean_proportion`, `sample_std_proportion`, `coefficient_of_variation`, `overall_rate_percent`, `overall_bugs_found`, `overall_lines_reviewed`, `wilson_ci_lower_pct`, `wilson_ci_upper_pct`, `trend_slope`, `trend_t_stat`, `stability`, `n_observations`, `uses_varying_denominators`, `target_rate_pct`, `capability_vs_target`
- `variability_ranking`: array of `{process, coefficient_of_variation, rank}` sorted by CV descending.
- `highest_variability_process`: string naming the highest CV process.
- `highest_risk_statement`: string explicitly naming the highest risk stage.
- `extended_analysis`: object mapping process names to `{min_value, max_value, range, median, trend_direction}`.
- `improvement_plan`: object with exactly 8 keys: `process`, `methodology`, `root_cause_approach`, `incident_response_plan`, `technical_debt_assessment`, `milestones_30_60_90_days` (object with `30_days`, `60_days`, `90_days`), `codename`, `success_criteria`.

## Markdown Brief (`pipeline_performance_brief.md`)
Required top-level sections (exact titles):
1. `# Pipeline Performance & Risk Assessment`
2. `## Summary of Findings`
3. `## Most Significant Risks`
4. `## Prioritized Corrective Actions`
5. `## Improvement Plan`

Under `## Improvement Plan`, required subsections (exact titles):
- `### Process Under Review`
- `### Methodology`
- `### Root Cause Approach`
- `### Incident Response Plan`
- `### Technical Debt Assessment`

**Consistency Rule**: Narrative must align with stats. Highest CV = highest risk. Stability determined by |t| > 2.0 threshold. Capability determined by rate vs target.