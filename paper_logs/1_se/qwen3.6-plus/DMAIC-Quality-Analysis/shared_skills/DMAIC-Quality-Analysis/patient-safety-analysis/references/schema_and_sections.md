# Expected Output Schema & Structure

## JSON Metrics (`patient_safety_report.json`)
Top-level keys:
- `process_metrics`: object mapping process name to `{mean, std, cv, slope, t_stat, stability}`
- `variability_ranking`: array of process names sorted by CV descending
- `highest_risk_statement`: string explicitly naming the highest CV process
- `medication_errors`: object with `overall_rate_pct`, `wilson_ci_low_pct`, `wilson_ci_high_pct`, `uses_varying_denominators` (bool), `target_rate_pct`, `capability` ("Capable" or "Not Capable")
- `monitoring_plan`: object with exactly 12 keys:
  - `process_to_be_monitored`, `inputs`, `outputs`, `key_performance_indicators`, `frequency_of_monitoring`, `observation_format`, `roles`, `reporting_format`, `corrective_action_process`, `benchmarks`
  - `checklist`: array of exactly 9 strings
  - `prioritized_actions`: array of exactly 3 objects/strings

## Markdown Brief (`patient_safety_brief.md`)
Required top-level sections (exact titles):
1. `# Patient Safety Brief -- [Hospital Name]`
2. `## Summary of Findings`
3. `## Most Significant Risks`
4. `## Prioritized Corrective Actions`
5. `## Monitoring Plan`

Under `## Monitoring Plan`, required subsections (exact titles):
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

**Consistency Rule**: Narrative must align with stats. Highest CV = highest risk. Stability determined by |t| > 2.0 threshold.