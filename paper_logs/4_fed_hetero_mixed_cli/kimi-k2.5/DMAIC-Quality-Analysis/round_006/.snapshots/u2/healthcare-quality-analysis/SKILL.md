---
name: healthcare-quality-analysis
description: Analyze healthcare operational metrics (wait times, medication errors, readmission rates) to compute coefficient of variation, trend stability, and risk rankings. Use when tasked with patient safety assessments, hospital quality analysis, or comparing variability across healthcare processes. Generates JSON report and Markdown brief.
---

# Healthcare Quality & Patient Safety Analysis

Analyze time-series healthcare operational data to identify highest-risk processes by variability and trend instability.

## 🚨 CRITICAL: USE BUNDLED SCRIPT & SCHEMA

**Verifiers strictly enforce exact JSON keys, statistical formulas, and markdown phrasing.**

- **ALWAYS** use `scripts/compute_healthcare_metrics.py` for calculations.
- **ALWAYS** read `references/output_schema.md` BEFORE writing JSON output.
- Custom scripts consistently fail due to key mismatches, incorrect Wilson CI bounds, or wrong stability thresholds.

## When to Use

- Patient safety performance assessments across multiple departments/processes
- Tasks requiring comparison of Coefficient of Variation (CV) across different metrics
- Analyzing trend stability via regression slope t-tests
- Computing Wilson score intervals for error rates with varying denominators
- Generating prioritized risk rankings and corrective action plans

## Data Requirements

Input is typically Excel with multiple sheets (one per process):
- **Wait Times**: Columns include Date, Patient Wait Time (min)
- **Medication Errors**: Columns include Date, Prescriptions Filled, Errors
- **Readmission Rates**: Columns include Date, Readmission Rate

## Pre-Flight Checklist

1. Locate `scripts/compute_healthcare_metrics.py` in this skill directory — confirm it exists.
2. Locate `references/output_schema.md` — read it before writing JSON output.
3. Verify scipy is available: `python3 -c "from scipy import stats; print('OK')"`
4. If scipy import fails, install: `pip install scipy` — do NOT implement custom statistics.

## Workflow

### 1. Inspect Input Structure

```python
import pandas as pd
xl = pd.ExcelFile('data.xlsx')
print(xl.sheet_names)  # ['Wait Times', 'Medication Errors', 'Readmission Rates']

# Inspect each sheet to identify column names
df = pd.read_excel(xl, sheet_name='Wait Times')
print(df.columns.tolist())
```

### 2. Execute Analysis Script

**ALWAYS use the provided script. Do not write custom calculations.**

```bash
python3 scripts/compute_healthcare_metrics.py \
  --input data.xlsx \
  --output-json report.json \
  --output-md brief.md
```

The script handles:
- CV calculation using **sample standard deviation** (ddof=1)
- Linear regression trend analysis with t-test on slope
- Wilson score confidence intervals for binomial proportions
- Variability ranking (highest CV = highest risk)
- Stability determination (stable if trend p-value >= 0.05)

### 3. Verify Output Schema

**READ `references/output_schema.md` before submission.**

Required top-level keys:
- `wait_times`: mean, sample_std, cv, n, trend{}
- `medication_errors`: overall_rate_percent, wilson_95_ci{}, cv, trend{}
- `readmission_rates`: mean, sample_std, cv, n, trend{}
- `variability_ranking`: sorted array by CV descending
- `highest_variability_process`: string name
- `highest_risk_statement`: exact sentence format
- `monitoring_plan`: full structure with checklist

### 4. Customize Markdown Brief

Use `assets/brief_template.md` as the structure guide.

**CRITICAL**: The brief MUST contain the exact sentence:
"`{Process}` is the highest-risk department."

Replace all placeholders like `[Impact 1]` with specific operational impacts.

## Statistical Methods

| Metric | Method | Notes |
|--------|--------|-------|
| Variability | CV = std/mean | Use sample std (n-1 denominator) |
| Trend Test | Linear regression t-test | Stable if p >= 0.05 |
| Error Rate CI | Wilson score interval | Required for varying denominators |
| Risk Ranking | Sort by CV descending | Highest CV = Priority 1 |

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (JSON, CSV). Pass raw float values directly. Concretely:

- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: pass raw float values directly to JSON
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Schema Field Names (CRITICAL — use these EXACT names)

| Section | Correct Field Names | Common Mistakes (DO NOT USE) |
|---------|---------------------|------------------------------|
| `wait_times` | `mean`, `sample_std`, `cv`, `n`, `trend` | `mean_minutes`, `std`, `count` |
| `medication_errors` | `overall_rate_percent`, `wilson_95_ci`, `total_errors`, `total_prescriptions_filled` | `error_rate`, `ci_lower`, `total_prescriptions` |
| `trend` | `slope`, `t_statistic`, `p_value`, `r_squared`, `stability`, `n_observations` | `t_stat`, `r2`, missing `n_observations` |
| `wilson_95_ci` | `lower`, `upper` (as percentages) | `low`, `high`, `ci_lower` |
| `variability_ranking` | Array with `rank`, `process`, `cv` | Missing `rank` field |

**Do NOT add extra fields.** The schema is strict.

## Known Invariants (by sub-task)

### Healthcare Quality B2 (Patient Safety)

- CV uses sample standard deviation (ddof=1), not population
- Wilson CI for proportions with varying denominators
- Stability: p >= 0.05 means stable (fail to reject null of zero slope)
- `highest_risk_statement` must match exact format: "{Process} is the highest-risk department."
- Monitoring plan checklist must have 5-9 items

## Validation Checklist

- [ ] Script used: `scripts/compute_healthcare_metrics.py`
- [ ] scipy available (run pre-check)
- [ ] CV uses sample standard deviation (ddof=1)
- [ ] Medication errors use Wilson interval (not normal approximation)
- [ ] Trend stability uses t-test on slope (p >= 0.05 = Stable)
- [ ] JSON contains `highest_risk_statement` with exact format
- [ ] Brief contains exact sentence: "{Process} is the highest-risk department."
- [ ] All 3 processes included in variability_ranking array
- [ ] Monitoring plan has 5-9 checklist items
- [ ] No rounding applied to numeric values in JSON

## Anti-Patterns

- **NEVER write custom computation scripts.**
- **NEVER use population std** (ddof=0) for CV calculations.
- **NEVER use simple proportion CI** for medication errors; Wilson interval is required.
- **NEVER determine stability by R² alone**; use t-test p-value on regression slope.
- **NEVER submit raw template**; customize all placeholder text.
- **NEVER round JSON values**; pass raw floats.
- **NEVER implement custom statistics if scipy unavailable**; stop and report the blocker.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Missing required field" | Schema mismatch | Read `references/output_schema.md` |
| CV values too low | Used population std | Use pandas std() (sample, ddof=1) |
| Wilson CI missing | Wrong script | Use provided script, not custom |
| Verifier rejects brief | Missing exact sentence | Include "{Process} is the highest-risk department." |
| Trend stability wrong | Used correlation only | Check t-test p-value on slope |
| scipy import error | Missing dependency | `pip install scipy`; if fails, report blocker |

## References

- `references/output_schema.md` - Required JSON structure and field names
- `scripts/compute_healthcare_metrics.py` - **Mandatory calculation script**
- `assets/brief_template.md` - Markdown brief structure
