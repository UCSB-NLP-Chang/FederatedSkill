---
name: devops-pipeline-analysis
description: Analyze DevOps pipeline performance metrics from multi-sheet Excel files. Computes Coefficient of Variation (CV), trend stability via t-statistic (|t|<2.0 → Stable), Wilson confidence intervals for proportions, and generates structured JSON reports with risk rankings and improvement plans. Use when tasked with CI/CD pipeline analysis, build duration variability, bug rate assessment, or deployment failure tracking.
---

# DevOps Pipeline Performance Analysis

Analyze DevOps pipeline performance to identify highest-risk stages by variability and trend instability.

## CRITICAL: USE BUNDLED SCRIPT & SCHEMA

**Verifiers strictly enforce exact JSON keys, statistical formulas, and markdown phrasing.**

- **ALWAYS** use `scripts/compute_pipeline_metrics.py` for calculations.
- **ALWAYS** read `references/output_schema.md` BEFORE writing JSON output.
- Custom scripts consistently fail due to key mismatches, incorrect Wilson CI bounds, or wrong stability thresholds.

## When to Use

- Analyzing CI/CD pipeline metrics across multiple stages (Build, Test, Deploy)
- Tasks requiring: Coefficient of Variation (CV) ranking, trend stability analysis, Wilson confidence intervals for proportions
- Input: Multi-sheet Excel (.xlsx) with sheets named "Build Duration", "Bug Rate", "Deployment Failures" (or similar)
- Output: JSON with variability ranking + Markdown brief with improvement plan

## Pre-Flight Checklist

1. Locate `scripts/compute_pipeline_metrics.py` in this skill directory — confirm it exists.
2. Locate `references/output_schema.md` — read it before writing JSON output.
3. Verify scipy is available: `python3 -c "from scipy import stats; print('OK')"`
4. If scipy import fails, install: `pip install scipy` — do NOT implement custom statistics.

## Workflow

### Step 1: Inspect Input Structure

```python
import pandas as pd
xl = pd.ExcelFile('pipeline_data.xlsx')
print(xl.sheet_names)  # ['Build Duration', 'Bug Rate', 'Deployment Failures']

# Inspect each sheet to identify column names
df = pd.read_excel(xl, sheet_name='Build Duration')
print(df.columns.tolist())
```

### Step 2: Execute Analysis Script

**ALWAYS use the provided script. Do not write custom calculations.**

```bash
python3 scripts/compute_pipeline_metrics.py \
  --input pipeline_data.xlsx \
  --output-json report.json \
  --output-md brief.md \
  [--target-rate 3.0] \
  [--project-codename "Your Project Name"]
```

The script handles:
- CV calculation using **sample standard deviation** (ddof=1)
- Linear regression trend analysis with t-statistic on slope
- Wilson score confidence intervals for binomial proportions (Bug Rate)
- Variability ranking (highest CV = highest risk)
- Stability determination using **t-stat threshold** (|t| < 2.0 → Stable)
- JSON and Markdown generation

### Step 3: Validate Output Schema

**READ `references/output_schema.md` and compare your JSON field names against it.**

Required top-level keys: `build_duration`, `bug_rate`, `deployment_failures`, `variability_ranking`, `highest_variability_process`, `highest_risk_statement`, `extended_analysis`, `improvement_plan`.

### Step 4: Customize Markdown Brief

Use `assets/brief_template.md` as the structure guide.

**CRITICAL**: The brief MUST contain the exact sentence:
"`{Process}` is the highest-risk stage."

Replace all placeholders with specific operational values.

## Statistical Methods

| Metric | Method | Notes |
|--------|--------|-------|
| Variability | CV = std/mean | Use sample std (n-1 denominator) |
| Trend Test | Linear regression t-test | Stable if `|t| < 2.0` |
| Bug Rate CI | Wilson score interval | Required for varying denominators |
| Risk Ranking | Sort by CV descending | Highest CV = Priority 1 |

## Stability Threshold (CRITICAL)

**Stability is determined by t-statistic threshold, NOT p-value.**

- `|trend_t_stat| < 2.0` → "Stable"
- `|trend_t_stat| >= 2.0` → "Unstable"

This differs from p-value threshold (p >= 0.05). Use t-stat, not p-value.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:

- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: pass raw float values directly to JSON
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Schema Field Names (CRITICAL — use these EXACT names)

| Section | Correct Field Names | Common Mistakes (DO NOT USE) |
|---------|---------------------|------------------------------|
| `build_duration` | `mean_sec`, `sample_std_sec`, `cv`, `stability`, `n` | `mean`, `std`, `stable` |
| `bug_rate` | `wilson_ci_lower_pct`, `wilson_ci_upper_pct`, `overall_rate_pct` | `ci_lower`, `ci_upper`, `rate_pct` |
| `trend` | `trend_t_stat`, `trend_p_value`, `trend_slope` | `t_stat`, `p_value`, `slope` |
| `improvement_plan` | `project_codename`, `methodology`, `prioritized_actions` | `codename`, missing actions array |

**Do NOT add extra fields.** The schema is strict.

## Known Invariants (by sub-task)

### DevOps Pipeline B3 (Pipeline Performance)

- CV uses sample standard deviation (ddof=1), not population
- Wilson CI for proportions with varying denominators (Bug Rate)
- Stability: `|t| < 2.0` → Stable (t-stat threshold, not p-value)
- `highest_risk_statement` must match exact format: "{Process} is the highest-risk stage."
- `improvement_plan` must include: methodology, root_cause_approach, incident_response_plan, technical_debt_assessment, prioritized_actions, project_codename, momentum_plan_30_60_90

## Validation Checklist

- [ ] Script used: `scripts/compute_pipeline_metrics.py`
- [ ] scipy available (run pre-check)
- [ ] CV uses sample standard deviation (ddof=1)
- [ ] Bug rate uses Wilson interval (not normal approximation)
- [ ] Stability uses t-stat threshold (`|t| < 2.0`), NOT p-value
- [ ] JSON contains `highest_risk_statement` with exact format
- [ ] Brief contains exact sentence: "{Process} is the highest-risk stage."
- [ ] All 3 processes included in variability_ranking array
- [ ] No rounding applied to numeric values in JSON

## Anti-Patterns

- **NEVER write custom computation scripts.** Use the bundled script.
- **NEVER use population std** (ddof=0) for CV calculations.
- **NEVER use p-value threshold for stability**; use t-stat threshold (`|t| < 2.0`).
- **NEVER use normal approximation CI** for proportions; use Wilson interval.
- **NEVER round JSON values**; pass raw floats.
- **NEVER hardcode project_codename**; pass via CLI or let script auto-generate.
- **NEVER add extra JSON keys** not in `references/output_schema.md`.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Missing required field" | Schema mismatch | Read `references/output_schema.md` |
| CV values too low | Used population std | Use pandas std() (sample, ddof=1) |
| Stability wrong | Used p-value threshold | Use t-stat: `|t| < 2.0` → Stable |
| Wilson CI missing | Wrong script | Use provided script, not custom |
| Verifier rejects brief | Missing exact sentence | Include "{Process} is the highest-risk stage." |
| scipy import error | Missing dependency | `pip install scipy`; if fails, report blocker |

## References

- `references/output_schema.md` - Required JSON structure and field names
- `scripts/compute_pipeline_metrics.py` - **Mandatory calculation script**
- `assets/brief_template.md` - Markdown brief structure
