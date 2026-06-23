---
name: dmaic-statistical-analysis
description: Perform DMAIC Analyze phase statistical analysis on time-series operational data. Computes ANOVA by weekday, I-MR control charts, linear regression, t-tests vs target, and process capability (Cpk) with strict schema compliance. Trigger phrases: Six Sigma, ANOVA, p-value, control chart, I-MR, regression, Cpk, capability, tollgate, DMAIC.
---

# DMAIC Statistical Analysis

Execute statistical process control analysis for DMAIC Analyze phase tollgate deliverables.

## Core Principle

**Never implement statistical distributions from scratch.** Custom implementations of F-distributions, t-distributions, and p-value calculations produce wildly incorrect results. Always use `scipy.stats`.

## When to Use

- Analyzing time-series operational data against targets or specification limits
- Generating Six Sigma tollgate briefs with ANOVA, control charts, regression, and capability
- Tasks specify business-day filtering and specific date windows
- Output must match strict JSON schema

## Workflow

### 1. Data Preparation

- Parse dates and filter to **business days only** (exclude Saturday, Sunday)
- Identify DMAIC phase boundaries from `Stage` column
- Extract **primary window**: typically ~40 business days ending at current phase
- Extract **I-MR stability window**: ~35 business days ending **before Analyze phase start** (critical alignment)

### 2. Use the Template Script (Preferred)

**Run the helper script first** — it produces schema-compliant output:
```bash
python3 scripts/analysis_template.py --input data.csv --baseline 500 --target 560 --lsl 560 --output-prefix tollgate
```

The template handles all schema requirements correctly. Only write custom code if the template cannot accommodate your task.

### 3. If Writing Custom Code

**Required imports:**
```python
from scipy import stats
import numpy as np
import pandas as pd
```

**One-Way ANOVA (by Weekday):**
```python
groups = [monday_vals, tuesday_vals, wednesday_vals, thursday_vals, friday_vals]
f_stat, p_value = stats.f_oneway(*groups)
```

**I-MR Control Chart:**
```python
mr = np.abs(np.diff(data_points))
mr_bar = np.mean(mr)
center = np.mean(data_points)
ucl = center + 3 * mr_bar / 1.128  # d2 = 1.128 for n=2
lcl = center - 3 * mr_bar / 1.128
mr_ucl = 3.267 * mr_bar
```

**Linear Regression:**
```python
x = np.arange(len(data))  # Day index: 0, 1, 2...
slope, intercept, r_value, p_value, std_err = stats.linregress(x, data)
```

**One-Sample t-Test:**
```python
t_stat, p_value = stats.ttest_1samp(data, target_value)
ci_low, ci_high = stats.t.interval(0.95, n-1, loc=mean, scale=stats.sem(data))
```

**Process Capability (Cpk):**
```python
sigma = np.std(data, ddof=1)  # MUST use sample std dev
cpk = (mean - lsl) / (3 * sigma)
```

### 4. Schema Compliance (Critical)

**Read `references/output_schema.md` before writing JSON.** Common failures:

| Wrong | Correct |
|-------|--------|
| `primary_window` | `primary_analysis_window` |
| `imr_window` | `imr_analysis_window` |
| `start` / `end` | `start_date` / `end_date` |
| `total_records` | `total_records_in_source` |
| `primary_window_business_days` | `primary_window_records` |

**Do NOT add extra fields** to JSON output. The schema is strict:
- No `points` array in `imr_summary`
- No `moving_ranges` array in `imr_summary`
- No `df_between` / `df_within` in `anova_by_weekday` unless specified

### 5. Output Generation

Generate two files:
1. `*_metrics.json`: Structured results matching schema in `references/output_schema.md`
2. `*_brief.md`: Executive tollgate brief

## Validation Checklist

Before submitting, verify:
- [ ] Business day count matches specification (exclude weekends)
- [ ] I-MR window ends **before** Analyze phase start date
- [ ] ANOVA includes all 5 weekdays with data
- [ ] Control limits use MR-bar/1.128, not raw sigma
- [ ] Cpk uses sample std dev (`ddof=1`), not population
- [ ] JSON field names match schema **exactly** (read `references/output_schema.md`)
- [ ] No extra fields added beyond schema specification
- [ ] All p-values in valid range [0, 1]

## Output Precision

Never round, truncate, or fixed-format numeric values in JSON outputs. Pass raw float values:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: Store full precision values; verifier decides acceptable tolerance
- Exception: Highly significant p-values (< 1e-10) may show as `1e-15` to avoid JSON `0.0`

## Anti-Patterns

- **Custom p-value implementations** — produces values > 1 or < 0. Always use scipy.stats.
- **Including weekends** when "business days only" specified
- **Population std dev** (`ddof=0`) instead of sample (`ddof=1`) for Cpk
- **Raw sigma for I-MR** instead of MR-bar/1.128
- **Hardcoded phase dates** — derive from Stage column
- **I-MR window overlapping Analyze data** — must end before Analyze phase
- **Writing custom code instead of using template script** — template is schema-compliant
- **Adding extra JSON fields** — schema is strict, no extensions
- **Wrong field names** — verify against schema before submission

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| p-value > 1 or < 0 | Custom implementation | Use scipy.stats |
| Verifier rejects JSON | Missing field or wrong precision | Check schema in references/ |
| Verifier rejects JSON | Wrong field names | Compare field names to schema exactly |
| Verifier rejects JSON | Extra fields added | Remove fields not in schema |
| Wrong record count | Weekend inclusion | Filter weekday < 5 |
| Negative Cpk unexpectedly | LSL direction or mean below target | Verify spec limit direction |

## Known Invariants (by Sub-task)

### DMAIC Analyze Phase (B1)
- I-MR window must end **before** Analyze phase data begins
- `business_days_only: true` must be explicit in JSON filters
- ANOVA weekday means: 3 decimal precision
- Regression slope: 6 decimal precision

## Scripts & References

- **Run** `scripts/analysis_template.py` for complete analysis pipeline (produces schema-compliant output)
- **Read** `references/output_schema.md` for exact JSON structure and field requirements **before writing output**
