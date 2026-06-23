# Process Capability Report Schema

**DO NOT RENAME KEYS** - all key names must match exactly.

## JSON Structure (`process_capability_report.json`)

```json
{
  "<process_name>": {
    "mean": <float>,
    "sample_std": <float>,
    "cv": <float>,
    "cp": <float>,
    "cpk": <float>,
    "pp": <float>,
    "ppk": <float>,
    "cpu": <float>,
    "cpl": <float>,
    "capability_classification": "Capable|Marginal|Not Capable",
    "n": <int>
  },
  "capability_ranking": [
    {"process": "<process_name>", "cpk": <float>, "classification": "<string>"}
  ],
  "variability_ranking": [
    {"process": "<process_name>", "cv": <float>}
  ],
  "highest_variability_process": "<process_name>",
  "highest_risk_process": "<process_name>",
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

## Capability Classification Rules

| Cpk Value | Classification | Action |
|-----------|----------------|--------|
| Cpk ≥ 1.33 | Capable | Monitor |
| 1.0 ≤ Cpk < 1.33 | Marginal | Target for improvement |
| Cpk < 1.0 | Not Capable | Priority improvement |

## Rate-Based Capability (No Spec Limits)

When analyzing defect/failure rates with target but no USL/LSL:
- Wilson CI entirely above target → Not Capable
- Wilson CI entirely below target → Capable
- Target falls within Wilson CI → Marginal

## Markdown Structure (`process_capability_brief.md`)

Required sections in order:
1. `# Process Capability Brief: <Location>`
2. `## Summary of Findings`
3. `## Most Significant Risks`
4. `## Prioritized Corrective Actions`
5. `## Monitoring Plan` — with subsections: Process to be Monitored, Inputs, Outputs, Key Performance Indicators, Frequency of Monitoring, Observation Format, Roles, Reporting Format, Corrective Action Process, Benchmarks
6. `## 30/60/90-Day Momentum Plan`

## Required Content

- `highest_risk_process` must appear in Markdown
- `project_codename` must be in format "Project <NAME>"
- `checklist` must have exactly 7 items
