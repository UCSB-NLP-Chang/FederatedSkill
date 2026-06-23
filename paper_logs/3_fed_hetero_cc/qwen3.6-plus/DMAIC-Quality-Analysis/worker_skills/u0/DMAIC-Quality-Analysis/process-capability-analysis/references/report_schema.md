# Process Capability Report Schema

**DO NOT RENAME KEYS** - all key names must match exactly.

## JSON Structure (`process_capability_report.json`)

```json
{
  "task_duration": {
    "mean": <float>,
    "sample_std": <float>,
    "cv": <float>,
    "trend_analysis": {"slope": <float>, "t_stat": <float>, "stability": "Stable|Trending"}
  },
  "failure_rate": {
    "overall_rate_pct": <float>,
    "wilson_95_ci_pct": [<float>, <float>],
    "total_failures": <int>,
    "total_units_processed": <int>,
    "target_rate_pct": <float>,
    "capability_vs_target": "Capable|Not Capable",
    "uses_varying_denominators": true,
    "cv": <float>
  },
  "system_errors": {
    "mean": <float>,
    "sample_std": <float>,
    "cv": <float>,
    "trend_analysis": {"slope": <float>, "t_stat": <float>, "stability": "Stable|Trending"}
  },
  "variability_ranking": [
    {"process": "<process_name>", "cv": <float>}
  ],
  "highest_variability_process": "<process_name>",
  "highest_risk_statement": "<exact_sentence>",
  "monitoring_plan": {
    "process_to_be_monitored": "<string>",
    "inputs": ["<item1>", ...],
    "outputs": ["<item1>", ...],
    "key_performance_indicators": ["<item1>", ...],
    "frequency_of_monitoring": "<string>",
    "observation_format": "<string>",
    "roles": ["<item1>", ...],
    "reporting_format": "<string>",
    "corrective_action_process": "<string>",
    "benchmarks": ["<item1>", ...],
    "checklist": ["<item1>", ..., "<item7>"],
    "momentum_plan_30_60_90": {"30_day": "<string>", "60_day": "<string>", "90_day": "<string>"},
    "project_codename": "<string>"
  }
}
```

## Markdown Structure (`process_capability_brief.md`)

Required sections in order:
1. `# Process Capability Brief: <Location>`
2. `## Summary of Findings`
3. `## Most Significant Risks`
4. `## Prioritized Corrective Actions`
5. `## Monitoring Plan` — with subsections: Process to be Monitored, Inputs, Outputs, Key Performance Indicators, Frequency of Monitoring, Observation Format, Roles, Reporting Format, Corrective Action Process, Benchmarks
6. `## 30/60/90-Day Momentum Plan`

## Required Content

- `highest_risk_statement` must appear as exact sentence in Markdown
- `project_codename` must be in format "Project <NAME>"
- `checklist` must have exactly 7 items