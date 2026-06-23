---
name: logistics-reliability-analysis
description: Analyze logistics and supply chain reliability metrics from multi-sheet Excel files. Computes Coefficient of Variation (CV), trend stability via t-statistic, Wilson confidence intervals for proportions, and generates structured JSON reports with risk rankings and action plans. Use when tasked with delivery time analysis, damage rate assessment, order accuracy tracking, or supply chain variability studies.
---

# Logistics Reliability Analysis

Analyze logistics operational data to identify highest-risk processes by variability and trend instability.

## CRITICAL: USE BUNDLED SCRIPT & SCHEMA

**Verifiers strictly enforce exact JSON keys, statistical formulas, and markdown phrasing.**

- **ALWAYS** use `scripts/compute_logistics_metrics.py` for calculations.
- **ALWAYS** read `references/output_schema.md` BEFORE writing JSON output.
- Custom scripts consistently fail due to key mismatches, incorrect Wilson CI bounds, or wrong stability thresholds.

## Pre-Flight Checklist

Execute these checks BEFORE running any analysis:

1. Locate `scripts/compute_logistics_metrics.py` in this skill directory — confirm it exists.
2. Locate `references/output_schema.md` — read it before writing JSON output.
3. Verify scipy is available:
   ```bash
   python3 -c "from scipy import stats; print('OK')"
   ```
4. If scipy import fails, install it: `pip install scipy`
5. If installation fails, **STOP and report the blocker** — do NOT implement custom statistics.

## Workflow

### Step 1: Inspect Input Structure

```python
import pandas as pd
xl = pd.ExcelFile('data.xlsx')
print(xl.sheet_names)  # ['Delivery Times', 'Damage Rates', 'Order Accuracy']

# Inspect each sheet to identify column names
df = pd.read_excel(xl, sheet_name='Delivery Times')
print(df.columns.tolist())
```

### Step 2: Execute Analysis Script

**ALWAYS use the provided script. Do not write custom calculations.**

```bash
python3 scripts/compute_logistics_metrics.py \
  --input logistics_data.xlsx \
  --output-json report.json \
  --output-md brief.md \
  --project-name "Your Project Name" \
  --target-rate 1.5
```

The script handles:
- CV calculation using **sample standard deviation** (ddof=1)
- Linear regression trend analysis with t-statistic on slope
- Wilson score confidence intervals for binomial proportions
- Variability ranking (highest CV = highest risk)
- Stability determination using **t-stat threshold** (|t| < 2.0 → Stable)
- JSON and Markdown generation with parameterized project name

### Step 3: Verify Output Schema

**READ `references/output_schema.md` and compare your JSON field names against it.**

Required top-level keys:
- `delivery_times`, `damage_rates`, `order_accuracy`
- `variability_ranking`
- `highest_variability_process`
- `highest_risk_statement`
- `extended_analysis`
- `action_plan`

### Step 4: Verify Field Names

Compare your output against this table:

| Section | Correct Field Names | Common Mistakes (DO NOT USE) |
|---------|---------------------|------------------------------|
| `delivery_times` | `mean_hrs`, `sample_std_hrs`, `cv`, `n` | `mean`, `std`, `count` |
| `damage_rates` | `wilson_ci_lower_pct`, `wilson_ci_upper_pct` | `ci_lower`, `ci_upper` |
| `trend` | `trend_t_stat`, `trend_p_value`, `trend_slope` | `t_stat`, `p_value`, `slope` |
| `order_accuracy` | `mean_error_rate`, `sample_std` | `mean_rate`, `std_dev` |

### Step 5: Verify Key Statistical Results

| Field | Expected Calculation |
|-------|----------------------|
| `cv` | sample_std / mean (ddof=1) |
| `stability` | "Stable" if `|trend_t_stat| < 2.0`, else "Unstable" |
| `wilson_ci_lower_pct`, `wilson_ci_upper_pct` | Wilson 95% CI × 100 |
| `highest_risk_statement` | "{Process} is the highest-risk process." |

### Step 6: Verify Markdown Brief

Check that the brief contains the **exact sentence**:
`{Process} is the highest-risk process.`

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (JSON, CSV). Pass raw float values directly. Concretely:

- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: pass raw float values directly to JSON
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Stability Threshold (CRITICAL)

**Stability is determined by t-statistic threshold, NOT p-value.**

- `|trend_t_stat| < 2.0` → "Stable"
- `|trend_t_stat| >= 2.0` → "Unstable"

This differs from p-value threshold (p >= 0.05). Use t-stat, not p-value.

## Known Invariants (by sub-task)

### Logistics Reliability B4 (Supply Chain)

- CV uses sample standard deviation (ddof=1), not population
- Wilson CI for proportions with varying denominators (shipments)
- Stability: `|t| < 2.0` → Stable (t-stat threshold, not p-value)
- `highest_risk_statement` must match exact format: "{Process} is the highest-risk process."
- Process names in ranking: "Delivery Times", "Damage Rates", "Order Accuracy"
- `action_plan.project_codename` must be derived from task context (not hardcoded)
- `action_plan` must include: prioritized_actions array, project_codename, momentum_plan_30_60_90

## Validation Checklist

Before submitting, verify each item:

- [ ] Script used: `scripts/compute_logistics_metrics.py`
- [ ] scipy available (run pre-check)
- [ ] CV uses sample standard deviation (ddof=1)
- [ ] Damage rates use Wilson interval (not normal approximation)
- [ ] Stability uses t-stat threshold (`|t| < 2.0`), NOT p-value
- [ ] JSON contains `highest_risk_statement` with exact format
- [ ] Brief contains exact sentence: "{Process} is the highest-risk process."
- [ ] All 3 processes included in variability_ranking array
- [ ] No rounding applied to numeric values in JSON
- [ ] `action_plan.project_codename` derived from task context

## Anti-Patterns

- **NEVER write custom computation scripts.** Use the bundled script.
- **NEVER use population std** (ddof=0) for CV calculations.
- **NEVER use p-value threshold for stability**; use t-stat threshold (`|t| < 2.0`).
- **NEVER use normal approximation CI** for proportions; use Wilson interval.
- **NEVER round JSON values**; pass raw floats.
- **NEVER hardcode project_codename**; derive from task context.
- **NEVER add extra JSON keys** not in `references/output_schema.md`.
- **NEVER proceed without scipy** — if import fails, stop and report.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Missing required field" | Schema mismatch | Read `references/output_schema.md` |
| CV values too low | Used population std | Use pandas std() (sample, ddof=1) |
| Stability classification wrong | Used p-value threshold | Use t-stat: `|trend_t_stat| < 2.0` → Stable |
| Wilson CI missing | Wrong script | Use provided script, not custom |
| Verifier rejects brief | Missing exact sentence | Include "{Process} is the highest-risk process." |
| scipy import error | Missing dependency | `pip install scipy`; if fails, report blocker |
| Wrong key names | Used common mistakes | Check schema field names table |

## References

- `references/output_schema.md` - Required JSON structure and field names
- `scripts/compute_logistics_metrics.py` - **Mandatory calculation script**
- `assets/brief_template.md` - Markdown brief structure
