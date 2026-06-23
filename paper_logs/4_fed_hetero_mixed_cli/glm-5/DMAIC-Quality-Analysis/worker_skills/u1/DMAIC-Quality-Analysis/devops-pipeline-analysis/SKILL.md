---
name: devops-pipeline-analysis
description: Analyze DevOps pipeline performance metrics from multi-sheet Excel files. Computes Coefficient of Variation (CV), trend stability via t-statistic, Wilson confidence intervals for proportions, and generates structured JSON reports with risk rankings and improvement plans. Use when tasked with CI/CD pipeline analysis, build duration variability, bug rate assessment, or deployment failure tracking. Trigger phrases: DevOps, CI/CD, pipeline, build duration, bug rate, deployment failures.
---

# DevOps Pipeline Performance Analysis

## CRITICAL: USE BUNDLED SCRIPT & SCHEMA

**Verifiers strictly enforce exact JSON keys, statistical formulas, and markdown phrasing.**

- **ALWAYS** use `scripts/compute_pipeline_metrics.py` for calculations.
- **ALWAYS** read `references/output_schema.md` BEFORE writing JSON output.
- **Custom scripts consistently fail** due to key mismatches, incorrect Wilson CI bounds, or wrong stability thresholds.

## Core Principle

**Use scipy.stats for all statistical calculations.** Custom implementations of t-distributions, Wilson score intervals, and p-value calculations produce incorrect results.

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
3. Custom p-value calculations are mathematically wrong without proper distribution functions

## When to Use

- Analyzing CI/CD pipeline metrics across multiple stages (Build, Test, Deploy)
- Tasks requiring: Coefficient of Variation (CV) ranking, trend stability analysis, Wilson confidence intervals for proportions
- Input: Multi-sheet Excel (.xlsx) with sheets named "Build Duration", "Bug Rate", "Deployment Failures" (or similar)
- Output: JSON with variability ranking + Markdown brief with improvement plan

## Workflow

### Step 1: Verify scipy Availability
```bash
python3 -c "from scipy import stats; print('scipy OK')"
```
If scipy is unavailable, install it or STOP and report the blocker.

### Step 2: Run the Bundled Script
```bash
python3 scripts/compute_pipeline_metrics.py \
  --input pipeline_data.xlsx \
  --output-json report.json \
  --output-md brief.md
```

The script handles:
- Loading all sheets from the Excel file
- CV calculation using **sample standard deviation** (ddof=1)
- Linear regression trend analysis with t-statistic on slope
- Wilson score confidence intervals for binomial proportions (Bug Rate)
- Variability ranking (highest CV = highest risk)
- Stability determination using **t-stat threshold** (`|t| < 2.0` → Stable)
- JSON and Markdown generation

**Dependencies**: `pandas`, `numpy`, `scipy`, `openpyxl`. Install if missing.

### Step 3: Validate Output Schema

**READ `references/output_schema.md` and compare your JSON field names against it.**

Required top-level keys (8 total):
1. `build_duration`
2. `bug_rate`
3. `deployment_failures`
4. `variability_ranking`
5. `highest_variability_process`
6. `highest_risk_statement`
7. `extended_analysis`
8. `improvement_plan`

### Step 4: Verify Key Statistical Results

| Field | Expected Calculation |
|-------|----------------------|
| `cv` | sample_std / mean (ddof=1) |
| `stability` | "Stable" if `abs(trend_t_stat) < 2.0`, else "Unstable" |
| `wilson_ci_lower_pct`, `wilson_ci_upper_pct` | Wilson 95% CI * 100 |
| `highest_risk_statement` | "{Process} is the highest-risk stage." |

### Step 5: Customize Markdown Brief

The script generates a baseline brief. Verify:
- Brief contains the **exact sentence**: `{Process} is the highest-risk stage.`
- All placeholder values replaced with actual metrics
- Improvement plan includes: process, methodology, root cause approach, incident response, technical debt, prioritized actions, project codename, 30/60/90 day momentum plan
- **project_codename is derived from task context** (e.g., file name, project name in prompt), NOT hardcoded

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: Pass raw floats to JSON outputs
- The verifier's tolerance (often 1e-4) decides acceptable precision

## Stability Threshold (CRITICAL)

**Stability is determined by t-statistic threshold, NOT p-value.**
- `abs(trend_t_stat) < 2.0` → "Stable"
- `abs(trend_t_stat) >= 2.0` → "Unstable"

## Known Invariants (by sub-task)

### DevOps pipeline performance (B3)
- Bug Rate sheet uses varying denominators (lines_reviewed) — Wilson interval required
- CV uses sample std dev (ddof=1), not population (ddof=0)
- Trend stability: `abs(trend_t_stat) < 2.0` → Stable
- `highest_risk_statement` must exactly follow format: "{Process} is the highest-risk stage."
- improvement_plan must include all 8 sub-fields: process, methodology, root_cause_approach, incident_response_plan, technical_debt_assessment, prioritized_actions, project_codename, momentum_plan_30_60_90
- project_codename is derived from task context, NOT hardcoded

## Schema Compliance Checklist

- [ ] `build_duration.mean_sec`, `build_duration.sample_std_sec`, `build_duration.cv` present
- [ ] `bug_rate.wilson_ci_lower_pct`, `bug_rate.wilson_ci_upper_pct` present
- [ ] `stability` field uses "Stable" or "Unstable"
- [ ] `highest_risk_statement` matches exact format: "{Process} is the highest-risk stage."
- [ ] `variability_ranking` array sorted by CV descending
- [ ] No rounding in JSON values (raw floats)
- [ ] CV uses sample std (ddof=1)
- [ ] Wilson CI used for bug rate
- [ ] improvement_plan.project_codename is task-specific, not hardcoded

## Anti-Patterns

- **Custom statistical implementations** — produces incorrect p-values and CI bounds. Always use scipy.stats.
- **Do not** write custom computation scripts; use the bundled script.
- **Do not** use population std dev (`ddof=0`); use sample (`ddof=1`).
- **Do not** use p-value threshold for stability; use t-stat threshold (`|t| < 2.0`).
- **Do not** omit `highest_risk_statement` or use generic phrasing.
- **Do not** use normal approximation CI for proportions; use Wilson interval.
- **Do not** round numeric values in JSON output.
- **Do not** add extra JSON keys not in `references/output_schema.md`.
- **Do not** hardcode `project_codename` — derive from task context (file name, prompt).
- **Proceeding without scipy** — if scipy import fails, stop and report; do not implement custom statistics.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| scipy import error | Missing dependency | Run `pip install scipy`; if fails, report blocker |
| "Missing required field" | Schema mismatch | Read `references/output_schema.md` |
| CV values too low | Used population std | Use pandas std() (sample, ddof=1) |
| Wilson CI missing | Wrong script | Use provided script, not custom |
| Verifier rejects brief | Missing exact sentence | Include "{Process} is the highest-risk stage." |
| Stability classification wrong | Wrong threshold | Use `abs(trend_t_stat) < 2.0` for Stable |
| project_codename wrong | Hardcoded value | Derive from task context (file name, prompt) |

## Scripts & References

- **Run**: `scripts/compute_pipeline_metrics.py` — deterministic computation, requires scipy and openpyxl.
- **Read**: `references/output_schema.md` — required JSON structure for verifier. **Read this BEFORE writing JSON output.**
- **Use**: `assets/brief_template.md` — structural template for markdown brief customization.
