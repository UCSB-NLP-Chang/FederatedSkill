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

### 2. Statistical Calculations (write code using these exact patterns)

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

**Alternative:** The script `scripts/analysis_template.py` produces schema-compliant output:
```bash
python3 scripts/analysis_template.py --input data.csv --baseline 500 --target 560 --lsl 560 \
    --primary-start 2025-01-04 --primary-end 2025-03-01 --imr-end 2025-02-21 \
    --metric-col ResolvedAlerts --output-prefix tollgate
```

### 3. JSON Schema Compliance (CRITICAL — use these exact field names)

The verifier rejects JSON with wrong field names or extra fields. Use this table:

| Section | Correct Field Names | Common Mistakes |
|---------|---------------------|----------------|
| `filters` | `primary_analysis_window`, `imr_analysis_window` | `primary_window`, `imr_window`, `date_range` |
| Window objects | `start_date`, `end_date`, `record_count` | `start`, `end`, `n` |
| `record_counts` | `total_records_in_source`, `primary_window_records`, `imr_window_records` | `total_records`, `primary_window_business_days` |
| `anova_by_weekday` | Only `weekday_means`, `p_value`, `f_statistic`, `highest_mean_day`, `lowest_mean_day` | Adding `df_between`, `df_within` |
| `imr_summary` | Only `points`, `center_line`, `ucl`, `lcl`, `mr_bar`, `mr_ucl` | Adding `mr_lcl`, `sigma_estimate`, `points` as array |
| `regression_day_index` | `n_observations` | `n`, `standard_error` |
| `ttest_vs_target` | `std_dev`, `mean_value` | `std`, `mean` |
| `capability_against_lsl` | `mean`, `std_dev_sample` | `mean_value`, `std` |

**Top-level keys (all 9 required):** `source_file`, `filters`, `record_counts`, `charter_metrics`, `anova_by_weekday`, `imr_summary`, `regression_day_index`, `ttest_vs_target`, `capability_against_lsl`

**Do NOT add extra fields.** The schema is strict. Any field not listed above will cause validation failure.

### 4. Markdown Brief (must customize — do not submit generic template)

The script generates a generic brief with placeholders. **You MUST customize it.** Use `assets/brief_template.md` as the structural guide.

Required sections (exact headers):
- Project Charter (table with Baseline, Target, Current Mean)
- Statistical Analysis (subsections: One-Way ANOVA, I-MR Control Chart, Linear Regression, One-Sample t-Test, Process Capability)
- A3 Summary (table with Background, Current Condition, Root Cause Analysis, Target Condition, Countermeasures)
- Operational Impacts (3-4 specific impacts tied to statistical findings)
- Timeline and Next Steps (DMAIC phase dates + actions with owners and due dates)

Customization rules:
- Replace ALL `[placeholder]` values with specific metrics from JSON output
- Operational impacts must be domain-specific (e.g., "Wednesday backlog causes 12% SLA miss rate"), NOT generic like "[Impact 1 - TBD]"
- Derive DMAIC phase start dates from the CSV `Stage` column
- Next steps must have specific owners and dates (typically 2-4 weeks after Analyze phase)
- Do NOT submit the script's raw output — verifier checks for meaningful customization

### 5. Pre-Submission Validation

Before submitting, verify EVERY item:
- [ ] Field names match schema EXACTLY (compare against table in Step 3)
- [ ] No extra fields added beyond schema specification
- [ ] `filters` contains `primary_analysis_window` and `imr_analysis_window` objects
- [ ] Each window has `start_date`, `end_date`, `business_days_only`, `record_count`
- [ ] `record_counts` uses `total_records_in_source`, `primary_window_records`, `imr_window_records`
- [ ] I-MR window ends **before** Analyze phase start date
- [ ] ANOVA includes all 5 weekdays with data
- [ ] Control limits use MR-bar/1.128, not raw sigma
- [ ] Cpk uses sample std dev (`ddof=1`), not population
- [ ] All p-values in valid range [0, 1]
- [ ] Markdown brief has no remaining `[placeholder]` text
- [ ] Operational impacts are domain-specific, not generic

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.
- Exception: Highly significant p-values (< 1e-10) may show as `1e-15` to avoid JSON `0.0`

## Known Invariants (by sub-task)

### DMAIC Analyze tollgate (B1)
- I-MR window must end BEFORE Analyze phase data starts (stability window for baseline)
- `business_days_only: true` must be explicit in JSON filters
- Cpk uses sample std dev (ddof=1), not population (ddof=0)
- Control limits derived from MR-bar/d2, not raw population sigma
- ANOVA weekday means: 3 decimal precision
- Regression slope: 6 decimal precision

## Anti-Patterns

- **Custom p-value implementations** — produces values > 1 or < 0. Always use scipy.stats.
- **Wrong JSON field names** — the #1 cause of verifier failure. Use the table in Step 3.
- **Extra JSON fields** — schema is strict, no extensions. `df_between`, `mr_lcl`, `points` array are NOT valid.
- **Including weekends** when "business days only" specified.
- **Population std dev** (`ddof=0`) instead of sample (`ddof=1`) for Cpk.
- **Raw sigma for I-MR** instead of MR-bar/1.128.
- **Hardcoded phase dates** — derive from Stage column.
- **I-MR window overlapping Analyze data** — must end before Analyze phase.
- **Submitting generic markdown brief** — verifier checks for task-specific content, not placeholder text.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| p-value > 1 or < 0 | Custom implementation | Use scipy.stats |
| Verifier rejects JSON | Wrong field names | Compare to table in Step 3 |
| Verifier rejects JSON | Extra fields added | Remove fields not in schema |
| Verifier rejects JSON | Missing nested structure | `filters` must contain window objects |
| Verifier rejects brief | Generic placeholder text | Replace all `[placeholder]` with specific values |
| Verifier rejects brief | Impacts not tied to findings | Write domain-specific impacts |
| Wrong record count | Weekend inclusion | Filter weekday < 5 |
| Negative Cpk unexpectedly | LSL direction or mean below target | Verify spec limit direction |

## Scripts & References

- **Run** `scripts/analysis_template.py` for complete analysis pipeline (produces schema-compliant output). Supports `--primary-start`, `--primary-end`, `--imr-end`, `--metric-col` for phase-aware filtering.
- **Read** `references/output_schema.md` for exact JSON structure and field requirements.
- **Use** `assets/brief_template.md` as structural template for markdown brief customization.
