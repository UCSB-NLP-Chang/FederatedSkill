---
name: healthcare-quality-analysis
description: Analyze patient safety and healthcare operational metrics from multi-sheet Excel files. Computes Coefficient of Variation (CV), trend stability via t-statistic, Wilson confidence intervals for proportions, and generates structured JSON reports with risk rankings. Use when tasked with hospital quality analysis, patient safety assessments, or comparing variability across healthcare processes.
---

# Healthcare Quality & Patient Safety Analysis

## CRITICAL: USE BUNDLED SCRIPT & SCHEMA

**Verifiers strictly enforce exact JSON keys, statistical formulas, and markdown phrasing.**

- **ALWAYS** use `scripts/compute_healthcare_metrics.py` for calculations.
- **ALWAYS** read `references/output_schema.md` BEFORE writing JSON output.
- **Custom scripts consistently fail** due to key mismatches, incorrect Wilson CI bounds, or wrong stability thresholds.

## When to Use

- Analyzing hospital/clinical metrics across multiple departments or processes.
- Tasks requiring: Coefficient of Variation (CV) ranking, trend stability analysis, Wilson confidence intervals for proportions.
- Input: Multi-sheet Excel (.xlsx) with sheets named "Wait Times", "Medication Errors", "Readmission Rates" (or similar).
- Output: JSON with variability ranking + Markdown brief.

## Input Structure

Typical Excel file has multiple sheets:

| Sheet Name | Expected Columns |
|------------|------------------|
| Wait Times | Date, Wait Time (minutes) |
| Medication Errors | Date, Prescriptions Filled, Errors |
| Readmission Rates | Date, Readmission Rate |

## Workflow

### Step 1: Verify scipy Availability

```bash
python3 -c "from scipy import stats; print('scipy OK')"
```

If scipy is unavailable:
1. Install: `pip install scipy`
2. If installation fails, **STOP and report the blocker** — do NOT implement custom statistics

### Step 2: Run the Bundled Script

```bash
python3 scripts/compute_healthcare_metrics.py \
  --input hospital_data.xlsx \
  --output-json report.json \
  --output-md brief.md
```

The script handles:
- Loading all sheets from the Excel file
- CV calculation using **sample standard deviation** (ddof=1)
- Linear regression trend analysis with t-statistic on slope
- Wilson score confidence intervals for binomial proportions
- Variability ranking (highest CV = highest risk)
- Stability determination using **t-stat threshold** (|t| < 2.0 → Stable)
- JSON and Markdown generation

### Step 3: Validate Output Schema

**READ `references/output_schema.md` and compare your JSON field names against it.**

Required top-level keys:
- `wait_times`, `medication_errors`, `readmission_rates` (each with nested fields)
- `variability_ranking` (array sorted by CV descending)
- `highest_variability_process` (string)
- `highest_risk_statement` (exact sentence format)
- `monitoring_plan` (full structure)
- `extended_analysis` (counts and totals)

### Step 4: Verify Key Statistical Results

Check these critical values before submission:

| Field | Expected Calculation |
|-------|----------------------|
| `cv` | sample_std / mean (ddof=1) |
| `stability` | "Stable" if `|trend_t_stat| < 2.0`, else "Unstable" |
| `wilson_ci_lower_pct`, `wilson_ci_upper_pct` | Wilson 95% CI * 100 |
| `highest_risk_statement` | "{Process} is the highest-risk department." |

### Step 5: Customize Markdown Brief

The script generates a baseline brief. Verify:

- Brief contains the **exact sentence**: `{Process} is the highest-risk department.`
- All placeholder values replaced with actual metrics
- Monitoring plan includes: inputs, outputs, KPIs, frequency, roles, corrective action process
- Prioritized actions have owners and timelines

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: write raw float values to JSON
- The verifier's tolerance decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Stability Threshold (CRITICAL)

**Stability is determined by t-statistic threshold, NOT p-value.**

- `|trend_t_stat| < 2.0` → "Stable"
- `|trend_t_stat| >= 2.0` → "Unstable"

This is approximately equivalent to p > 0.05 for large samples, but **use the t-stat threshold**.

## Schema Compliance Checklist

Before submission, verify:

- [ ] `wait_times.mean_minutes`, `wait_times.sample_std_minutes`, `wait_times.cv` present
- [ ] `medication_errors.wilson_ci_lower_pct`, `medication_errors.wilson_ci_upper_pct` present
- [ ] `stability` field uses "Stable" or "Unstable" (exact strings)
- [ ] `highest_risk_statement` matches exact format: "{Process} is the highest-risk department."
- [ ] `variability_ranking` array sorted by CV descending with `rank`, `process`, `cv` keys
- [ ] No rounding in JSON values (raw floats)
- [ ] CV uses sample std (ddof=1), not population std
- [ ] Wilson CI used for medication errors (not normal approximation)

## Anti-Patterns

- **Do not** write custom computation scripts; use the bundled script.
- **Do not** use population std dev (`ddof=0`); use sample (`ddof=1`).
- **Do not** use p-value threshold for stability; use t-stat threshold (`|t| < 2.0`).
- **Do not** omit `highest_risk_statement` or use generic phrasing.
- **Do not** use normal approximation CI for proportions; use Wilson interval.
- **Do not** round numeric values in JSON output.
- **Do not** add extra JSON keys not in `references/output_schema.md`.
- **Do not** proceed without scipy; if unavailable, report blocker.

## Known Invariants (by sub-task)

### Healthcare quality multi-process analysis (B2)

- Stability threshold: `|trend_t_stat| < 2.0` (approximately p > 0.05 for large n)
- Wilson CI required for medication errors (varying denominators)
- `highest_risk_statement`: exact sentence format required
- Process names in ranking: use title case (e.g., "Wait Times", "Readmission Rates")

## Scripts & References

- **Run**: `scripts/compute_healthcare_metrics.py` — deterministic computation, requires scipy and openpyxl.
- **Read**: `references/output_schema.md` — required JSON structure for verifier. **Read this BEFORE writing JSON output.**
- **Use**: `assets/brief_template.md` — structural template for markdown brief customization.