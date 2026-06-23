# Expected Output Schema & Structure

## JSON Metrics (`logistics_reliability_report.json`)
Top-level keys:
- `<sheet_name_snake_case>`: object containing metric stats.
  - Standard: `mean_<unit>`, `sample_std_<unit>`, `coefficient_of_variation`, `trend` (`slope`, `t_stat`, `stability`)
  - Proportion: `uses_varying_denominators`, `total_shipments` (or denom), `total_damaged` (or num), `overall_rate_pct`, `wilson_ci_lower_pct`, `wilson_ci_upper_pct`, `mean_proportion`, `sample_std_proportion`, `coefficient_of_variation`, `trend`, `target_rate_pct`, `capability_vs_target`
- `variability_ranking`: array of `{process, cv}` sorted by CV descending.
- `highest_variability_process`: string naming the highest CV process.
- `highest_risk_statement`: string explicitly naming the highest risk process (must match Markdown verbatim).
- `extended_analysis`: object with `<process>_summary` strings, `risk_assessment` string, `key_concerns` array of 4 strings.
- `variance_diagnostic`: object with `process_analyzed`, `amplification_detected` (bool), `severity`, `pattern_type`, `origin_layer`, `recommended_intervention`.
- `action_plan`: object with `prioritized_actions` (array of 3 objects), `checklist` (array of exactly 8 strings), `milestones_30_60_90_days` (object or array), `codename`.

## Markdown Brief (`logistics_reliability_brief.md`)
Required top-level sections (exact titles):
1. `# Logistics Reliability Assessment — [Company Name]`
2. `## Summary of Findings`
3. `## Most Significant Risks`
4. `## Prioritized Corrective Actions`
5. `## Variance Diagnostic`
6. `## Action Plan`

Under `## Action Plan`, required subsections:
- `### Prioritized Actions`
- `### Checklist`
- `### 30/60/90-Day Momentum Milestones`

**Consistency Rule**: Narrative must align with stats. Highest CV = highest risk. Stability determined by |t| > 2.0 threshold. Capability determined by rate vs target. The exact `highest_risk_statement` string must appear in the Markdown without Markdown formatting.