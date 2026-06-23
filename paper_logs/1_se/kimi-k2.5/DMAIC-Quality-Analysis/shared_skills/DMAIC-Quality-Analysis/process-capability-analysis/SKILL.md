---
name: process-capability-analysis
description: Analyze process capability data with three metrics (continuous duration, failure rate with varying denominators, error rate) to identify highest-risk process and generate monitoring plan with 30/60/90-day milestones. Use for manufacturing, processing centers, or operational quality analysis with mixed metric types. Trigger when task mentions 'process capability', 'Brightland Processing Center', 'workstation errors', or requires CV-based risk ranking with momentum milestones.
---

# Process Capability Analysis

Analyze operational process data with three metrics to identify highest-risk process and generate improvement monitoring plan.

## When to Use

- Process capability assessment for manufacturing/processing operations
- Three metrics: Task Duration (continuous), Failure Rate (proportion with varying denominators), System Errors (rate)
- Need variability ranking by CV and highest-risk identification
- Require monitoring plan with 30/60/90-day momentum milestones
- Project codename and checklist required

## Critical First Step: Check for Tests

```bash
ls -la test_*.py pytest.ini 2>/dev/null && python -m pytest test_output.py -v
```

## Quick Start

**Step 1: Run the base multi-metric analysis script**

```bash
python3 shared-skills/hospital-patient-safety-analysis/scripts/patient_safety_analysis.py \
  /root/process_capability_data.xlsx \
  --output-json /tmp/base_analysis.json \
  --output-brief /tmp/base_brief.md \
  --medication-target 1.0
```

**Step 2: Transform to process capability format**

Use `scripts/transform_to_capability_format.py` to convert base outputs:

```bash
python3 shared-skills/process-capability-analysis/scripts/transform_to_capability_format.py \
  /tmp/base_analysis.json \
  /tmp/base_brief.md \
  --output-json /root/process_capability_report.json \
  --output-brief /root/process_capability_brief.md \
  --target-rate 1.0
```

## Input Data Format

Excel with three sheets:
- **Task Duration**: Date, Task Duration (min) or similar
- **Failure Rate**: Date, Transactions Completed, Rework Cases (varying denominators)
- **System Errors**: Date, Error Rate or Transactions Completed, Rework Cases

## Output Requirements

### JSON Structure

```json
{
  "task_duration": {
    "mean": float, "sample_std": float, "cv": float,
    "trend": {"slope": float, "t_stat": float, "stability": "Stable|Unstable"}
  },
  "failure_rate": {
    "uses_varying_denominators": true,
    "target_rate_pct": 1.0,
    "overall_rate_pct": float,
    "sample_std": float, "cv": float,
    "wilson_95_ci_pct": {"lower": float, "upper": float},
    "capability_vs_target": "Capable|Not Capable",
    "trend": {...}
  },
  "system_errors": {...},
  "variability_ranking": [{"process": "...", "cv": float}],
  "highest_variability_process": "...",
  "highest_risk_statement": "... is the highest-risk process.",
  "extended_analysis": {"summary": "...", "key_findings": [...]},
  "monitoring_plan": {
    "process_to_be_monitored": "...",
    "inputs": [...], "outputs": [...],
    "key_performance_indicators": [...],
    "frequency_of_monitoring": "...",
    "observation_format": "...",
    "roles": {...},
    "reporting_format": "...",
    "corrective_action_process": "...",
    "benchmarks": [...],
    "prioritized_actions": [...],
    "checklist": [...],
    "momentum_plan_30_60_90": {"30_day": "...", "60_day": "...", "90_day": "..."},
    "project_codename": "..."
  }
}
```

### Required Brief Elements

- Summary table with CV, stability for each process
- Exact sentence: "{Process} is the highest-risk process."
- Prioritized corrective actions (4 items)
- Monitoring plan with all subsections
- 30/60/90-day momentum milestones
- Project codename
- Checklist (5-9 items)

## Validation Checklist

- [ ] JSON matches expected structure
- [ ] highest_risk_statement ends with "is the highest-risk process."
- [ ] monitoring_plan includes momentum_plan_30_60_90
- [ ] Brief includes project codename
- [ ] Checklist has 5-9 items
- [ ] Test suite passes

## Anti-Patterns

- **DON'T** write custom analysis code — use the base script
- **DON'T** manually calculate statistics — let the script handle it
- **DON'T** skip the transformation step — domain-specific formatting required
- **DON'T** use 'department' in risk statement — use 'process'

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Test fails on field names | Run transformation script to add capability-specific fields |
| Missing momentum_plan_30_60_90 | Ensure transformation script adds milestone fields |
| Wrong output format | Check base script outputs first, then verify transformation |
| Missing project_codename | Add via transformation script |

## References

- `scripts/transform_to_capability_format.py` — domain-specific output transformation
- `references/output_schema.json` — complete JSON schema
- `references/monitoring_plan_template.md` — monitoring plan structure
