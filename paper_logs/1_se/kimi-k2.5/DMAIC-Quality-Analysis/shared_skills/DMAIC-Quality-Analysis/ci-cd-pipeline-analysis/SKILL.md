---
name: ci-cd-pipeline-analysis
description: Analyze CI/CD pipeline performance data with three metrics: build duration (continuous), bug rate (proportion with varying denominators), and deployment failures (rate). Use when tasks require calculating CV, Wilson CI for bug rates, trend stability analysis, and identifying highest-risk pipeline stage. Trigger when you see Excel data with Build Duration, Bug Rate, and Deployment Failures sheets. Always check for test_output.py first and run it early.
---

# CI/CD Pipeline Performance Analysis

Analyze CI/CD pipeline metrics to identify highest-risk stage and generate improvement plan.

## When to Use

- CI/CD pipeline performance assessment
- Three metrics: Build Duration, Bug Rate, Deployment Failures
- Need variability ranking and highest-risk identification
- Require improvement plan with DMAIC methodology

## Critical First Step: Check for Tests

```bash
ls -la test_*.py pytest.ini 2>/dev/null && python -m pytest test_output.py -v
```

## Quick Start

**Step 1: Run the base analysis script**

```bash
python3 shared-skills/hospital-patient-safety-analysis/scripts/patient_safety_analysis.py \
  /root/pipeline_performance_data.xlsx \
  --output-json /tmp/base_analysis.json \
  --output-brief /tmp/base_brief.md \
  --medication-target 3.0
```

**Step 2: Transform to CI/CD-specific format**

Use `scripts/transform_to_cicd_format.py` to convert base outputs to required CI/CD format:

```bash
python3 shared-skills/ci-cd-pipeline-analysis/scripts/transform_to_cicd_format.py \
  /tmp/base_analysis.json \
  /tmp/base_brief.md \
  --output-json /root/pipeline_performance_report.json \
  --output-brief /root/pipeline_performance_brief.md
```

## Input Data Format

Excel with three sheets:
- **Build Duration**: Date, Build Duration (sec)
- **Bug Rate**: Date, Lines Reviewed, Bugs Found
- **Deployment Failures**: Date, Failure Rate

## Output Requirements

### JSON Structure

```json
{
  "build_duration": {
    "mean": float, "sample_std": float, "cv": float,
    "trend": {"slope": float, "t_stat": float, "stability": "Stable|Unstable"}
  },
  "bug_rate": {
    "uses_varying_denominators": true,
    "target_rate_pct": 3.0,
    "overall_rate_pct": float,
    "sample_std": float, "cv": float,
    "wilson_95_ci_pct": {"lower": float, "upper": float},
    "capability_vs_target": "Capable|Not Capable",
    "trend": {...}
  },
  "deployment_failures": {...},
  "variability_ranking": [{"process": "...", "cv": float}],
  "highest_variability_process": "...",
  "highest_risk_statement": "... is the highest-risk stage.",
  "extended_analysis": {"summary": "...", "key_findings": [...]},
  "improvement_plan": {...}
}
```

### Required Brief Elements

- Summary table with CV, stability for each process
- Exact sentence: "{Process} is the highest-risk stage."
- Prioritized corrective actions (4 items)
- Improvement plan with all subsections
- 30/60/90-day momentum milestones

## Validation Checklist

- [ ] JSON matches expected structure
- [ ] highest_risk_statement ends with "is the highest-risk stage."
- [ ] improvement_plan includes all required fields
- [ ] Brief includes 30/60/90-day milestones
- [ ] Test suite passes

## Anti-Patterns

- **DON'T** write custom analysis code — use the base script
- **DON'T** manually calculate statistics — let the script handle it
- **DON'T** skip the transformation step — domain-specific formatting required

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Test fails on field names | Run transformation script to add CI/CD-specific fields |
| Missing improvement_plan | Ensure transformation script adds all required subsections |
| Wrong output format | Check base script outputs first, then verify transformation |

## References

- `scripts/transform_to_cicd_format.py` — domain-specific output transformation
- `references/cicd_output_schema.json` — complete JSON schema for CI/CD format
- `references/improvement_plan_template.md` — improvement plan structure
