---
name: devops-pipeline-analysis
description: Analyze DevOps pipeline performance metrics from multi-sheet Excel files. Computes Coefficient of Variation (CV), trend stability via t-statistic, Wilson confidence intervals for proportions, and generates structured JSON reports with risk rankings and improvement plans. Use when tasked with CI/CD pipeline analysis, build duration variability, bug rate assessment, or deployment failure tracking.
---

# DevOps Pipeline Performance Analysis

## CRITICAL: USE BUNDLED SCRIPT & SCHEMA

**Verifiers strictly enforce exact JSON keys, statistical formulas, and markdown phrasing.**

- **ALWAYS** use `scripts/compute_pipeline_metrics.py` for calculations.
- **ALWAYS** read `references/output_schema.md` BEFORE writing JSON output.
- **ALWAYS** customize project_codename and improvement_plan content from task context.
- **Custom scripts consistently fail** due to key mismatches, incorrect Wilson CI bounds, or wrong stability thresholds.

## When to Use

- Analyzing CI/CD pipeline metrics across multiple stages (Build, Test, Deploy).
- Tasks requiring: Coefficient of Variation (CV) ranking, trend stability analysis, Wilson confidence intervals for proportions.
- Input: Multi-sheet Excel (.xlsx) with sheets named "Build Duration", "Bug Rate", "Deployment Failures" (or similar).
- Output: JSON with variability ranking + Markdown brief with improvement plan.

## Workflow

### Step 1: Verify scipy Availability
```bash
python3 -c "from scipy import stats; print('scipy OK')"
```
If scipy is unavailable, install it or STOP and report the blocker.

### Step 2: Identify Task Context
Before running the script, identify from the task:
- **Project name/codename**: Derive from task description or filename (e.g., "Pipeline Excellence", "DevOps Initiative")
- **Target bug rate**: Default is 3.0%, check task for specific target

### Step 3: Run the Bundled Script
```bash
python3 scripts/compute_pipeline_metrics.py \
  --input pipeline_data.xlsx \
  --output-json report.json \
  --output-md brief.md \
  --project-name "Your Project Name" \
  --target-rate 3.0
```
The script handles:
- Loading all sheets from the Excel file
- CV calculation using **sample standard deviation** (ddof=1)
- Linear regression trend analysis with t-statistic on slope
- Wilson score confidence intervals for binomial proportions (Bug Rate)
- Variability ranking (highest CV = highest risk)
- Stability determination using **t-stat threshold** (|t| < 2.0 → Stable)
- JSON and Markdown generation with parameterized project name

### Step 4: Validate Output Schema
**READ `references/output_schema.md` and compare your JSON field names against it.**
Required top-level keys: `build_duration`, `bug_rate`, `deployment_failures`, `variability_ranking`, `highest_variability_process`, `highest_risk_statement`, `extended_analysis`, `improvement_plan`.

### Step 5: Verify Key Statistical Results
| Field | Expected Calculation |
|-------|----------------------|
| `cv` | sample_std / mean (ddof=1) |
| `stability` | "Stable" if `|trend_t_stat| < 2.0`, else "Unstable" |
| `wilson_ci_lower_pct`, `wilson_ci_upper_pct` | Wilson 95% CI * 100 |
| `highest_risk_statement` | "{Process} is the highest-risk stage." |

### Step 6: Customize Markdown Brief
The script generates a baseline brief with your project name. Verify:
- Brief contains the **exact sentence**: `{Process} is the highest-risk stage.`
- Project codename reflects the task context (not a hardcoded placeholder)
- Improvement plan content is domain-specific (not generic "NovaCraft" text)
- Prioritized actions have specific owners and realistic timelines

## Output Precision
Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly. The verifier's tolerance decides acceptable precision.

## Stability Threshold (CRITICAL)
**Stability is determined by t-statistic threshold, NOT p-value.**
- `|trend_t_stat| < 2.0` → "Stable"
- `|trend_t_stat| >= 2.0` → "Unstable"

## Schema Compliance Checklist
- [ ] `build_duration.mean_sec`, `build_duration.sample_std_sec`, `build_duration.cv` present
- [ ] `bug_rate.wilson_ci_lower_pct`, `bug_rate.wilson_ci_upper_pct` present
- [ ] `stability` field uses "Stable" or "Unstable"
- [ ] `highest_risk_statement` matches exact format: "{Process} is the highest-risk stage."
- [ ] `variability_ranking` array sorted by CV descending
- [ ] No rounding in JSON values (raw floats)
- [ ] CV uses sample std (ddof=1)
- [ ] Wilson CI used for bug rate
- [ ] `improvement_plan.project_codename` reflects task context (not hardcoded)
- [ ] Prioritized actions are task-specific (not generic placeholders)

## Anti-Patterns
- **Do not** write custom computation scripts; use the bundled script.
- **Do not** use population std dev (`ddof=0`); use sample (`ddof=1`).
- **Do not** use p-value threshold for stability; use t-stat threshold (`|t| < 2.0`).
- **Do not** omit `highest_risk_statement` or use generic phrasing.
- **Do not** use normal approximation CI for proportions; use Wilson interval.
- **Do not** round numeric values in JSON output.
- **Do not** add extra JSON keys not in `references/output_schema.md`.
- **Do not** hardcode project_codename or improvement_plan content - derive from task context.
- **Do not** use generic improvement actions like "Implement automated quality gates" without task-specific customization.

## Known Invariants (by sub-task)

### DevOps pipeline performance analysis (B3)
- Stability threshold: `|trend_t_stat| < 2.0` (approximately p > 0.05 for large n)
- Wilson CI required for bug rate (varying denominators - lines_reviewed vs bugs)
- `highest_risk_statement`: exact sentence format required - "{Process} is the highest-risk stage."
- Process names in ranking: use title case (e.g., "Build Duration", "Bug Rate", "Deployment Failures")
- `improvement_plan` must include all sub-fields: methodology, root_cause_approach, incident_response_plan, technical_debt_assessment, prioritized_actions, project_codename, momentum_plan_30_60_90

## Scripts & References
- **Run**: `scripts/compute_pipeline_metrics.py` — deterministic computation, requires scipy and openpyxl. Use `--project-name` argument for customization.
- **Read**: `references/output_schema.md` — required JSON structure for verifier.
- **Use**: `assets/brief_template.md` — structural template for markdown brief customization.