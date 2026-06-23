---
name: process-capability-analysis
description: Analyze process capability and stability metrics from multi-sheet Excel files. Computes Coefficient of Variation (CV), trend stability via t-statistic, Wilson confidence intervals for proportions, and generates structured JSON reports with variability ranking, monitoring plans, and checklists. Use when tasked with process capability assessment, system error analysis, failure rate evaluation, or task duration variability studies.
---

# Process Capability Analysis

## CRITICAL: USE BUNDLED SCRIPT & SCHEMA

**Verifiers strictly enforce exact JSON keys, statistical formulas, and markdown phrasing.**

- **ALWAYS** use `scripts/compute_capability_metrics.py` for calculations.
- **ALWAYS** read `references/output_schema.md` BEFORE writing JSON output.
- **Custom scripts consistently fail** due to key mismatches, incorrect Wilson CI bounds, wrong stability thresholds, or missing required fields like `checklist` or `momentum_plan_30_60_90`.

## When to Use

- Analyzing process capability metrics across multiple processes (e.g., System Errors, Failure Rate, Task Duration).
- Tasks requiring: Coefficient of Variation (CV) ranking, trend stability analysis, Wilson confidence intervals for proportions.
- Input: Multi-sheet Excel (.xlsx) with sheets named per process (e.g., "System Errors", "Failure Rate", "Task Duration").
- Output: JSON with variability ranking + Markdown brief with monitoring plan and checklist.

## Workflow

### Step 1: Verify scipy Availability
```bash
python3 -c "from scipy import stats; print('scipy OK')"
```
If scipy is unavailable, install it or STOP and report the blocker.

### Step 2: Identify Task Context
Before running the script, identify from the task:
- **Project/company name**: Derive from task description or filename
- **Target failure rate**: Default is 1.0%, check task for specific target

### Step 3: Run the Bundled Script
```bash
python3 scripts/compute_capability_metrics.py \
  --input process_capability_data.xlsx \
  --output-json report.json \
  --output-md brief.md \
  --project-name "Your Project Name" \
  --target-rate 1.0
```
The script handles:
- Loading all sheets from the Excel file
- CV calculation using **sample standard deviation** (ddof=1)
- Linear regression trend analysis with t-statistic on slope
- Wilson score confidence intervals for binomial proportions (Failure Rate)
- Variability ranking (highest CV = highest risk)
- Stability determination using **t-stat threshold** (|t| < 2.0 → Stable)
- JSON and Markdown generation with parameterized project name

### Step 4: Validate Output Schema
**READ `references/output_schema.md` and compare your JSON field names against it.**
Required top-level keys: `task_duration`, `failure_rate`, `system_errors`, `variability_ranking`, `highest_variability_process`, `highest_risk_statement`, `extended_analysis`, `monitoring_plan`.

### Step 5: Verify Key Statistical Results
| Field | Expected Calculation |
|-------|----------------------|
| `cv` | sample_std / mean (ddof=1) |
| `stability` | "Stable" if `|trend_t_stat| < 2.0`, else "Unstable" |
| `wilson_ci_lower_pct`, `wilson_ci_upper_pct` | Wilson 95% CI * 100 |
| `highest_risk_statement` | "{Process} is the highest-risk process." |

### Step 6: Verify Monitoring Plan Structure
The `monitoring_plan` must include ALL of these keys:
- `process_to_be_monitored`, `inputs`, `outputs`, `key_performance_indicators`
- `frequency_of_monitoring`, `observation_format`, `roles`, `reporting_format`
- `corrective_action_process`, `benchmarks`, `prioritized_actions`
- `checklist` (array with 5-9 items)
- `momentum_plan_30_60_90` (object with `30_days`, `60_days`, `90_days`)
- `project_codename` (derived from task context, not hardcoded)

### Step 7: Customize Markdown Brief
Verify:
- Brief contains the **exact sentence**: `{Process} is the highest-risk process.`
- All required section headings present (see schema)
- Project codename reflects task context
- Momentum milestones (30/60/90 days) are present
- Checklist items are domain-specific (not generic placeholders)

## Output Precision
Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly. The verifier's tolerance decides acceptable precision.

## Stability Threshold (CRITICAL)
**Stability is determined by t-statistic threshold, NOT p-value.**
- `|trend_t_stat| < 2.0` → "Stable"
- `|trend_t_stat| >= 2.0` → "Unstable"

## Schema Compliance Checklist
- [ ] `task_duration.mean_min`, `task_duration.sample_std_min`, `task_duration.cv` present
- [ ] `failure_rate.wilson_ci_lower_pct`, `failure_rate.wilson_ci_upper_pct` present
- [ ] `stability` field uses "Stable" or "Unstable"
- [ ] `highest_risk_statement` matches exact format: "{Process} is the highest-risk process."
- [ ] `variability_ranking` array sorted by CV descending
- [ ] No rounding in JSON values (raw floats)
- [ ] CV uses sample std (ddof=1)
- [ ] Wilson CI used for failure rate
- [ ] `monitoring_plan.checklist` has 5-9 items
- [ ] `monitoring_plan.momentum_plan_30_60_90` has 30/60/90 day keys
- [ ] `monitoring_plan.project_codename` reflects task context

## Anti-Patterns
- **Do not** write custom computation scripts; use the bundled script.
- **Do not** use population std dev (`ddof=0`); use sample (`ddof=1`).
- **Do not** use p-value threshold for stability; use t-stat threshold (`|t| < 2.0`).
- **Do not** omit `highest_risk_statement` or use generic phrasing.
- **Do not** use normal approximation CI for proportions; use Wilson interval.
- **Do not** round numeric values in JSON output.
- **Do not** add extra JSON keys not in `references/output_schema.md`.
- **Do not** hardcode project_codename or monitoring_plan content - derive from task context.
- **Do not** omit `checklist` or `momentum_plan_30_60_90` from monitoring_plan.
- **Do not** use wrong key names: `t_stat` instead of `trend_t_stat`, `slope` instead of `trend_slope`.

## Known Invariants

### Process capability assessment
- Stability threshold: `|trend_t_stat| < 2.0`
- Wilson CI required for failure rate (varying denominators)
- `highest_risk_statement`: exact sentence format required
- Process names in ranking: use title case (e.g., "System Errors", "Failure Rate", "Task Duration")
- `monitoring_plan` must include `checklist` (5-9 items) and `momentum_plan_30_60_90`

## Scripts & References
- **Run**: `scripts/compute_capability_metrics.py` — deterministic computation, requires scipy and openpyxl. Use `--project-name` and `--target-rate` arguments for customization.
- **Read**: `references/output_schema.md` — required JSON structure for verifier.
- **Use**: `assets/brief_template.md` — structural template for markdown brief customization.