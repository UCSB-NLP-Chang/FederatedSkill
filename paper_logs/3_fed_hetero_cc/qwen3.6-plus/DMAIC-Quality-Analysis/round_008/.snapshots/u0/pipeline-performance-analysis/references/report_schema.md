# Pipeline Report Schema

**DO NOT RENAME KEYS** - all key names must match exactly.

## JSON Structure (`pipeline_performance_report.json`)

```json
{
  "build_duration": {
    "mean": <float>,
    "std": <float>,
    "cv": <float>,
    "slope": <float>,
    "t_stat": <float>,
    "stability": "Stable" | "Trending"
  },
  "bug_rate": {
    "overall_rate_pct": <float>,
    "wilson_ci_lower": <float>,
    "wilson_ci_upper": <float>,
    "capability_vs_target": "Capable" | "Not Capable",
    "total_bugs": <int>,
    "total_lines": <int>
  },
  "deployment_failures": {
    "mean": <float>,
    "std": <float>,
    "cv": <float>,
    "slope": <float>,
    "t_stat": <float>,
    "stability": "Stable" | "Trending"
  },
  "variability_ranking": [
    {"process": "<process_name>", "coefficient_of_variation": <float>}
  ],
  "highest_variability_process": "<process_name>",
  "highest_risk_statement": "<string>",
  "improvement_plan": {
    "project_codename": "<string>",
    "milestones_30_days": "<string>",
    "milestones_60_days": "<string>",
    "milestones_90_days": "<string>"
  }
}
```

## Markdown Structure (`pipeline_performance_brief.md`)

Required sections in order:

1. `# Summary of Findings` - Include summary table with all metrics
2. `# Most Significant Risks` - Bullet list of key risks
3. `# Prioritized Corrective Actions` - Exactly 5 numbered actions
4. `# Improvement Plan` - 5 subsections + milestone timeline

## Key Calculation Rules

- **Bug rate**: Use pooled rate `total_bugs / total_lines`, NOT mean of daily rates
- **CV ranking**: Sort descending (highest variability first)
- **Stability**: `|t_stat| < 2.0` → Stable
- **Wilson CI**: Pure numpy implementation (no scipy)
