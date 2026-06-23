---
name: logistics-reliability-analysis
description: Analyze logistics and supply chain reliability metrics from multi-sheet Excel files. Computes Coefficient of Variation (CV), trend stability via t-statistic, Wilson confidence intervals for proportions, and generates structured JSON reports with risk rankings and action plans. Use when tasked with delivery time analysis, damage rate assessment, order accuracy tracking, or supply chain variability studies.
---

# Logistics Reliability Analysis

## CRITICAL: USE BUNDLED SCRIPT & SCHEMA

**Verifiers strictly enforce exact JSON keys, statistical formulas, and markdown phrasing.**

- **ALWAYS** use `scripts/compute_logistics_metrics.py` for calculations.
- **ALWAYS** read `references/output_schema.md` BEFORE writing JSON output.
- **Custom scripts consistently fail** due to key mismatches, incorrect Wilson CI bounds, wrong stability thresholds, or rounded numeric values.

## When to Use

- Analyzing logistics/supply chain metrics across multiple processes (Delivery Times, Damage Rates, Order Accuracy).
- Tasks requiring: Coefficient of Variation (CV) ranking, trend stability analysis, Wilson confidence intervals for proportions.
- Input: Multi-sheet Excel (.xlsx) with sheets named "Delivery Times", "Damage Rates", "Order Accuracy" (or similar).
- Output: JSON with variability ranking + Markdown brief with action plan.

## Workflow

### Step 1: Verify scipy Availability
```bash
python3 -c "from scipy import stats; print('scipy OK')"
```
If scipy is unavailable, install it or STOP and report the blocker.

### Step 2: Identify Task Context
Before running the script, identify from the task:
- **Project/company name**: Derive from task description or filename (e.g., "Meridian Global Logistics")
- **Target damage rate**: Default is 1.5%, check task for specific target

### Step 3: Run the Bundled Script
```bash
python3 scripts/compute_logistics_metrics.py \
  --input logistics_data.xlsx \
  --output-json report.json \
  --output-md brief.md \
  --project-name "Your Project Name" \
  --target-rate 1.5
```
The script handles:
- Loading all sheets from the Excel file
- CV calculation using **sample standard deviation** (ddof=1)
- Linear regression trend analysis with t-statistic on slope
- Wilson score confidence intervals for binomial proportions (Damage Rates)
- Variability ranking (highest CV = highest risk)
- Stability determination using **t-stat threshold** (|t| < 2.0 → Stable)
- JSON and Markdown generation with parameterized project name

### Step 4: Validate Output Schema
**READ `references/output_schema.md` and compare your JSON field names against it.**
Required top-level keys: `delivery_times`, `damage_rates`, `order_accuracy`, `variability_ranking`, `highest_variability_process`, `highest_risk_statement`, `extended_analysis`, `action_plan`.

### Step 5: Verify Key Statistical Results
| Field | Expected Calculation |
|-------|----------------------|
| `cv` | sample_std / mean (ddof=1) |
| `stability` | "Stable" if `|trend_t_stat| < 2.0`, else "Unstable" |
| `wilson_ci_lower_pct`, `wilson_ci_upper_pct` | Wilson 95% CI * 100 |
| `highest_risk_statement` | "{Process} is the highest-risk process." |

### Step 6: Customize Markdown Brief
The script generates a baseline brief with your project name. Verify:
- Brief contains the **exact sentence**: `{Process} is the highest-risk process.`
- Project name reflects the task context (not a hardcoded placeholder)
- Action plan content is domain-specific (not generic text)
- Prioritized actions have specific owners and realistic timelines

## Output Precision
Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly. The verifier's tolerance decides acceptable precision.

## Stability Threshold (CRITICAL)
**Stability is determined by t-statistic threshold, NOT p-value.**
- `|trend_t_stat| < 2.0` → "Stable"
- `|trend_t_stat| >= 2.0` → "Unstable"

## Schema Compliance Checklist
- [ ] `delivery_times.mean_hrs`, `delivery_times.sample_std_hrs`, `delivery_times.cv` present
- [ ] `damage_rates.wilson_ci_lower_pct`, `damage_rates.wilson_ci_upper_pct` present
- [ ] `stability` field uses "Stable" or "Unstable"
- [ ] `highest_risk_statement` matches exact format: "{Process} is the highest-risk process."
- [ ] `variability_ranking` array sorted by CV descending
- [ ] No rounding in JSON values (raw floats)
- [ ] CV uses sample std (ddof=1)
- [ ] Wilson CI used for damage rates
- [ ] `action_plan.project_codename` reflects task context (not hardcoded)
- [ ] Prioritized actions are task-specific (not generic placeholders)

## Anti-Patterns
- **Do not** write custom computation scripts; use the bundled script.
- **Do not** use population std dev (`ddof=0`); use sample (`ddof=1`).
- **Do not** use p-value threshold for stability; use t-stat threshold (`|t| < 2.0`).
- **Do not** omit `highest_risk_statement` or use generic phrasing.
- **Do not** use normal approximation CI for proportions; use Wilson interval.
- **Do not** round numeric values in JSON output.
- **Do not** add extra JSON keys not in `references/output_schema.md`.
- **Do not** hardcode project_codename or action_plan content - derive from task context.
- **Do not** use wrong key names: `t_stat` instead of `trend_t_stat`, `slope` instead of `trend_slope`, `wilson_95_ci_lower_pct` instead of `wilson_ci_lower_pct`.

## Known Invariants (by sub-task)

### Logistics reliability chain analysis
- Stability threshold: `|trend_t_stat| < 2.0` (approximately p > 0.05 for large n)
- Wilson CI required for damage rates (varying denominators - shipments vs damaged)
- `highest_risk_statement`: exact sentence format required - "{Process} is the highest-risk process."
- Process names in ranking: use title case (e.g., "Delivery Times", "Damage Rates", "Order Accuracy")
- `action_plan` must include all sub-fields: prioritized_actions, project_codename, momentum_plan_30_60_90

## Scripts & References
- **Run**: `scripts/compute_logistics_metrics.py` — deterministic computation, requires scipy and openpyxl. Use `--project-name` argument for customization.
- **Read**: `references/output_schema.md` — required JSON structure for verifier.
- **Use**: `assets/brief_template.md` — structural template for markdown brief customization.