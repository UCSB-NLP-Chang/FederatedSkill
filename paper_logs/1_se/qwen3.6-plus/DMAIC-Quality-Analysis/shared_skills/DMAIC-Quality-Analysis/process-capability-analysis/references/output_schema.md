# Expected Output Schema & Structure

## JSON Metrics (`process_capability_report.json`)
Top-level keys:
- `<sheet_name_snake_case>`: object containing metric stats.
  - Standard: `mean_<unit>`, `sample_std_<unit>`, `coefficient_of_variation`, `trend` (`slope`, `t_stat`, `stability`)
  - Proportion: `uses_varying_denominators`, `total_trials`, `total_errors`, `overall_rate_pct`, `wilson_ci_lower_pct`, `wilson_ci_upper_pct`, `mean_proportion`, `sample_std_proportion`, `coefficient_of_variation`, `trend`, `target_rate_pct`, `capability_vs_target`
- `variability_ranking`: array of `{process, cv}` sorted by CV descending.
- `highest_variability_process`: string naming the highest CV process.
- `highest_risk_statement`: string explicitly naming the highest risk process (must match Markdown verbatim).
- `extended_analysis`: object with `<process>_summary` strings and `risk_assessment`.
- `monitoring_plan`: object with `process_to_be_monitored`, `inputs`, `outputs`, `key_performance_indicators`, `frequency_of_monitoring`, `observation_format`, `roles`, `reporting_format`, `corrective_action_process`, `benchmarks`, `checklist` (array of 8 strings), `prioritized_actions` (array of 3 objects), `milestones_30_60_90_days`, `project_codename`.

## Markdown Brief (`process_capability_brief.md`)
Required top-level sections (exact titles):
1. `# Process Capability Assessment — [Organization Name]`
2. `## Summary of Findings`
3. `## Most Significant Risks`
4. `## Prioritized Corrective Actions`
5. `## Monitoring Plan`

Under `## Monitoring Plan`, required subsections:
- `### Process to be Monitored`
- `### Inputs`
- `### Outputs`
- `### Key Performance Indicators (KPIs)`
- `### Frequency of Monitoring`
- `### Observation Format`
- `### Roles`
- `### Reporting Format`
- `### Corrective Action Process`
- `### Benchmarks`

**Consistency Rule**: Narrative must align with stats. Highest CV = highest risk. Stability determined by |t| > 2.0 threshold. Capability determined by rate vs target. The exact `highest_risk_statement` string must appear in the Markdown without Markdown formatting.