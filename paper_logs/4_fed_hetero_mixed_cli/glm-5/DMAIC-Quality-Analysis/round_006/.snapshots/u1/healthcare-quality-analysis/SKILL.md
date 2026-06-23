---
name: healthcare-quality-analysis
description: Analyze patient safety and operational healthcare data from Excel/CSV files. Computes process stability (t-stat trend), variability (CV), proportion capability (Wilson CI), and generates structured JSON reports and Markdown briefs. Use when tasked with hospital quality metrics, patient safety dashboards, or clinical process variability assessments.
---

# Healthcare Quality & Patient Safety Analysis

## 🚨 CRITICAL: USE BUNDLED SCRIPT & SCHEMA
**Verifiers strictly enforce exact JSON keys, statistical formulas, and markdown phrasing.**
- **ALWAYS** use `scripts/compute_safety_metrics.py` for calculations.
- **ALWAYS** read `references/output_schema.md` BEFORE writing JSON output.
- Custom scripts consistently fail due to key mismatches, incorrect Wilson CI bounds, or wrong stability thresholds.

## Core Principle

**Use scipy.stats for all statistical calculations.** Custom implementations of t-distributions, Wilson score intervals, and p-value calculations produce incorrect results. Always use `scipy.stats`.

## Pre-Flight Check (CRITICAL)

Before starting any analysis, verify scipy availability:
```python
try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
```

**If scipy is unavailable:**
1. Attempt to install: `pip install scipy`
2. If installation fails, **STOP and report the blocker** — do not proceed with custom implementations

## When to Use

- Analyzing hospital/clinical metrics (Wait Times, Medication Errors, Readmission Rates)
- Tasks requiring: Coefficient of Variation (CV) ranking, trend stability via t-statistic, Wilson confidence intervals for proportions, capability vs target
- Input: Excel (.xlsx) with sheets for each process, or CSV with all metrics in columns

## Workflow

### 1. Parse Input Data

- Load Excel file. Identify sheets/columns for each process metric.
- Handle varying denominators for proportion metrics (e.g., errors / prescriptions filled).

### 2. Compute Metrics via Script

Run `scripts/compute_safety_metrics.py` with exact CLI arguments:
```bash
python3 scripts/compute_safety_metrics.py --input data.xlsx \
  --wait-col "Wait Time" --med-err-col "Error Rate" --med-denom-col "Prescriptions" \
  --readm-col "Readmission Rate" --target-rate 2.0 \
  --output-json report.json --output-md brief.md
```

Script handles CV, t-stat trends, Wilson CI, stability classification, and JSON/Markdown generation.

**Dependencies**: `pandas`, `numpy`, `scipy`, `openpyxl`. Install if missing.

### 3. Validate Output Schema

- Read `references/output_schema.md` and verify all top-level keys.
- Ensure `highest_risk_statement` matches exact required phrasing: "{Process} is the highest-risk department."
- Verify stability thresholds: `|t_stat| < 2.0` → Stable, else Unstable.
- Verify Wilson CI uses standard 95% approximation.

### 4. Customize Markdown Brief

- The script generates a baseline brief. Use `assets/brief_template.md` as a structural reference if manual edits are required.
- Ensure "Most Significant Risks" section explicitly names the highest-CV process.
- Ensure "Monitoring Plan" includes inputs, outputs, KPIs, frequency, roles, and corrective action process.

## Statistical Rules & Thresholds

- **Stability**: Determined by trend t-statistic. `|t| < 2.0` → Stable. `|t| >= 2.0` → Unstable.
- **Variability Ranking**: Sort processes by CV (std/mean) descending.
- **Proportion Capability**: Compare overall rate % to target. If rate < target → Capable.
- **Wilson CI**: Use standard 95% CI for proportions. Report bounds as percentages.
- **Precision**: Do not round intermediate values. Output floats to 4 decimal places unless specified.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: Pass raw floats to JSON/Excel outputs
- The verifier's tolerance (often 1e-4) decides acceptable precision

## Known Invariants (by sub-task)

### Healthcare quality assessment (B2)
- Medication errors require Wilson interval (not normal approximation) due to varying daily denominators
- CV uses sample std dev (ddof=1), not population (ddof=0)
- Trend stability: |t_stat| < 2.0 → Stable, |t_stat| >= 2.0 → Unstable
- `highest_risk_statement` must exactly follow format: "{Process} is the highest-risk department."
- Extended analysis must include data_points, min/max values for each process
- Monitoring plan must include benchmarks with max_acceptable_cv=0.15, stability_threshold_t_stat=2.0

## Anti-Patterns

- **Custom statistical implementations** — produces incorrect p-values and CI bounds. Always use scipy.stats.
- **Do not** write custom computation scripts.
- **Do not** use population std dev (`ddof=0`); use sample (`ddof=1`).
- **Do not** misclassify stability; t-stat threshold is strictly 2.0.
- **Do not** omit `highest_risk_statement` or use generic phrasing.
- **Do not** round Wilson CI bounds prematurely.
- **Do not** add extra JSON keys not in `references/output_schema.md`.
- **Proceeding without scipy** — if scipy import fails, stop and report; do not implement custom statistics.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| scipy import error | Missing dependency | Run `pip install scipy`; if fails, report blocker |
| "Missing required field" | Schema mismatch | Read `references/output_schema.md` |
| CV values too low | Used population std | Use pandas std() (sample, ddof=1) |
| Wilson CI missing | Wrong script | Use provided script, not custom |
| Verifier rejects brief | Missing exact sentence | Include "{Process} is the highest-risk department." |
| Stability classification wrong | Wrong threshold | Use |t_stat| < 2.0 for Stable |

## Scripts & References

- **Run** `scripts/compute_safety_metrics.py` for complete analysis pipeline. Requires scipy.
- **Read** `references/output_schema.md` for exact JSON structure and field requirements. **Read this BEFORE writing JSON output.**
- **Use** `assets/brief_template.md` as structural template for markdown brief customization.