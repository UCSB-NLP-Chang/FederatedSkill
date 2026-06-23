---
name: hospital-patient-safety-analysis
description: Perform multi-metric statistical analysis on operational data with three metric types: continuous values (CV, trend), proportions with varying denominators (Wilson CI, daily rate CV), and rates/proportions (CV, trend). Use for healthcare patient safety, CI/CD pipeline performance, manufacturing quality, logistics/supply chain reliability, or any domain with mixed metric types requiring variability ranking and stability assessment. Trigger when task requires CV comparison across processes, linear regression t-test for trends (|t|>2.0 = unstable), Wilson confidence intervals for proportions, and identifying highest-risk process by variability. This is the BASE skill - for domain-specific outputs, use a wrapper skill like ci-cd-pipeline-analysis or process-capability-analysis.
---

# Multi-Metric Statistical Analysis

Analyze operational data with mixed metric types: continuous values, proportions with varying denominators, and rates. Ranks processes by coefficient of variation (CV) to identify highest-risk item.

## When to Use

- Multiple processes/metrics to compare (3+ items)
- Mixed data types: continuous values, proportions with varying denominators, rates
- Need variability ranking by CV
- Trend stability analysis required (|t-statistic| > 2.0 = unstable)
- Wilson CI needed for proportion data
- Must identify single highest-risk process
- **Common domains**: Healthcare (wait times, medication errors, readmissions), CI/CD (build duration, bug rates, deployment failures), Logistics (delivery times, damage rates, order accuracy), Manufacturing (throughput, defect rates, cycle times)

## ⚠️ DOMAIN-SPECIFIC OUTPUTS REQUIRE WRAPPER

This skill produces **generic output field names** (wait_times, medication_errors, readmission_rates). For domain-specific requirements:

| Domain | Use This Wrapper Skill |
|--------|------------------------|
| CI/CD Pipeline | `ci-cd-pipeline-analysis` |
| Process Capability | `process-capability-analysis` |
| Custom domain | Create new wrapper following the pattern |

**Wrapper pattern**: Run this script → Transform outputs → Add domain-specific sections

## Critical First Step: Check for Tests

**Before any analysis, check for and run the test suite:**

```bash
ls -la test_*.py pytest.ini 2>/dev/null && python -m pytest test_output.py -v
```

If tests exist, run them first to understand expected output format, then re-run after generating outputs to verify.

## Input Data Format

Excel (.xlsx) with multiple sheets. Each sheet represents one process/metric:

| Metric Type | Sheet Contains | Example Columns |
|-------------|---------------|-----------------|
| Continuous | Date, Value | Date, Patient Wait Time (min), Delivery Time (hrs), Task Duration (min) |
| Proportion (varying denominator) | Date, Denominator, Count | Date, Lines Reviewed, Bugs Found; Date, Shipments, Damaged; Date, Prescriptions Filled, Errors |
| Rate/Proportion | Date, Rate | Date, Readmission Rate, Error Rate |

## Quick Start: Use the Skill Script

**ALWAYS use the provided script** — do not write custom analysis code:

```bash
python3 shared-skills/hospital-patient-safety-analysis/scripts/patient_safety_analysis.py \
  <input.xlsx> \
  --output-json <report.json> \
  --output-brief <brief.md> \
  [--medication-target <pct>]
```

**For non-healthcare domains**: The script works for any multi-metric analysis. The output uses generic field names (wait_times, medication_errors, readmission_rates) that you must map to your domain using a transformation wrapper.

## Critical: Inspect Data Before Running

```bash
python3 << 'EOF'
import pandas as pd
xl = pd.ExcelFile('/path/to/data.xlsx')
print('Sheets:', xl.sheet_names)
for s in xl.sheet_names:
    print(f'\n=== {s} ===')
    print(pd.read_excel(xl, s).head(3).to_string())
EOF
```

Verify sheet names, column names, and data completeness.

## Key Calculations

| Metric Type | CV Calculation | Trend Test | Special Handling |
|-------------|---------------|------------|------------------|
| Continuous | std/mean | Linear regression t-test | None |
| Proportion (varying denom) | CV of daily proportions | Linear regression on counts | Wilson 95% CI |
| Rate | std/mean | Linear regression t-test | None |

### Wilson Score Interval (for proportions)

```python
p = k/n  # overall proportion
z = 1.96  # 95% CI
denominator = 1 + z**2/n
centre = (p + z**2/(2*n)) / denominator
margin = z * sqrt((p*(1-p) + z**2/(4*n)) / n) / denominator
lower = centre - margin
upper = centre + margin
```

### Stability Decision Rule

```
IF |t_statistic| > 2.0 THEN "Unstable" ELSE "Stable"
```

## Output Schema (Generic)

See `references/output_schema.json` for complete schema. Key fields:

```json
{
  "wait_times": { "mean": float, "sample_std": float, "cv": float, ... },
  "medication_errors": { "overall_rate_percent": float, "wilson_95_ci_lower": float, ... },
  "readmission_rates": { "mean": float, "cv": float, ... },
  "variability_ranking": [{"process": "name", "cv": float}],
  "highest_variability_process": "Process Name",
  "highest_risk_statement": "... is the highest-risk department."
}
```

**Note**: Field names are healthcare-oriented. Use a wrapper skill to transform to domain-specific names.

## Domain Adaptation

This skill is domain-agnostic. For domain-specific outputs (monitoring plans, improvement plans, momentum milestones):

1. Run this script to get base analysis
2. Transform outputs to domain-specific format using a wrapper script
3. Add domain-specific sections (30/60/90 milestones, project codename, etc.)

See `ci-cd-pipeline-analysis/` and `process-capability-analysis/` for wrapper examples.

## Validation Checklist

- [ ] Wilson CI used for proportion data (not normal approximation)
- [ ] CV calculated from daily proportions for varying-denominator data
- [ ] Stability uses |t| > 2.0 threshold exactly
- [ ] Variability ranking sorted by CV descending
- [ ] highest_risk_statement matches exact required format
- [ ] Test suite passes if test_output.py exists

## Anti-Patterns to Avoid

- **DON'T** write custom analysis code when this script exists — this is the #1 cause of test failures
- **DON'T** use normal approximation CI for proportions
- **DON'T** calculate CV on raw counts for proportion data (use daily rates)
- **DON'T** use |t| > 1.96 or other thresholds for stability
- **DON'T** skip running test_output.py first
- **DON'T** assume healthcare-only — the script handles any three-metric analysis
- **DON'T** use raw output for domain-specific tasks — always use wrapper transformation

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Test fails on Wilson CI | Using normal approximation | Use exact Wilson formula from `references/formulas.md` |
| Test fails on proportion CV | Calculating on raw counts | Compute daily rates first, then CV |
| Test fails on stability | Wrong t threshold | Verify \|t\| > 2.0 exactly |
| Script fails on Excel | Wrong sheet/column names | Inspect Excel structure first |
| Test fails on field names | Custom code instead of script | Use provided script, don't write your own |
| Domain mismatch in output | Using raw output without transformation | Use wrapper skill for your domain |
| Missing 30/60/90 milestones | Using raw output | Use process-capability-analysis wrapper |

## Script Reference

`scripts/patient_safety_analysis.py` — handles multi-sheet Excel, automatic metric type detection, Wilson CI, CV ranking, stability assessment.

`references/formulas.md` — exact statistical formulas.
`references/output_schema.json` — complete JSON schema.
