# Logistics Reliability Report Schema

**DO NOT RENAME KEYS** - all key names must match exactly.

## JSON Structure (`logistics_reliability_report.json`)

```json
{
  "damage_rates": {
    "overall_rate_pct": <float>,
    "wilson_ci_lower": <float>,
    "wilson_ci_upper": <float>,
    "capability_vs_target": "Capable" | "Not Capable",
    "total_damaged": <int>,
    "total_shipments": <int>,
    "uses_varying_denominators": true,
    "target_rate_pct": 1.5
  },
  "variance_diagnostic": {
    "delivery_times": { "mean": <float>, "std": <float>, "cv": <float>, "slope": <float>, "t_stat": <float>, "stability": "Stable" | "Unstable" },
    "order_accuracy": { "mean": <float>, "std": <float>, "cv": <float>, "slope": <float>, "t_stat": <float>, "stability": "Stable" | "Unstable" }
  },
  "variability_ranking": [
    {"process": "<process_name>", "coefficient_of_variation": <float>}
  ],
  "highest_variability_process": "<process_name>",
  "highest_risk_statement": "<exact_sentence>",
  "action_plan": {
    "project_codename": "<string>",
    "milestones_30_days": "<string>",
    "milestones_60_days": "<string>",
    "milestones_90_days": "<string>",
    "checklist": ["<item1>", ..., "<item7>"]
  }
}
```

## Markdown Structure (`logistics_reliability_brief.md`)

Required sections in order:
1. `# Summary of Findings`
2. `# Most Significant Risks`
3. `# Prioritized Corrective Actions`
4. `# Variance Diagnostic`
5. `# Action Plan` (includes 30/60/90-day milestones and 7-item checklist)