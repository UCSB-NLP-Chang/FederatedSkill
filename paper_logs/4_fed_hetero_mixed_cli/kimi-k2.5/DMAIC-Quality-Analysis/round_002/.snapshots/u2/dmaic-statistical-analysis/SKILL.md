---
name: dmaic-statistical-analysis
description: Perform DMAIC Analyze phase statistical analysis on time-series operational data. Use when generating Six Sigma tollgate deliverables requiring ANOVA, I-MR control charts, linear regression, t-tests, and process capability (Cpk) from CSV data with business-day filtering and stage-aligned windows.
---

# DMAIC Statistical Analysis

Execute statistical process control analysis for DMAIC tollgate deliverables.

## Core Principle

**Always use `scipy.stats` for statistical tests.** Custom implementations of F-distributions, t-distributions, or beta functions produce incorrect p-values (values outside [0,1]). Never implement statistical distributions from scratch.

## Prerequisites

- Input CSV with columns: `Date`, `Stage` (DMAIC phase), `Day` (weekday), `Metric`
- Charter parameters: Baseline value, Target value, Specification limit (LSL/USL)
- Defined analysis windows aligned to DMAIC stages

## Workflow

### 1. Data Preparation
- Parse dates and filter to **business days only** (Monday-Friday only, exclude Saturday/Sunday)
- Identify DMAIC phase boundaries using `Stage` column
- Extract primary window: typically 40 business days ending at current phase
- **Critical for I-MR**: Extract I-MR stability window that ends BEFORE Analyze phase data begins (e.g., Baseline+Define+Measure phases only, ~35 business days)

### 2. Statistical Calculations

**Use `scripts/spc_calculations.py` rather than ad-hoc Python.** The script guarantees schema-compliant output. See Script Usage below.

**Charter Metrics**
- Current mean vs Baseline vs Target

**One-Way ANOVA (by Weekday)**
- Group by Monday-Friday
- Use `scipy.stats.f_oneway(*groups)` for F-statistic and p-value
- Identify highest/lowest mean days
- **Required output**: `f_statistic` field (commonly missed)

**I-MR Control Chart** (on stability window ending before Analyze)
- Individuals (X): CL = mean, UCL/LCL = mean ± 2.667 × MR-bar (E2 constant)
- Moving Range (MR): MR-bar = average of |Xi - Xi-1|, UCL = 3.267 × MR-bar
- sigma_est = MR-bar / 1.128 (d2 constant for n=2)

**Linear Regression**
- X: Day index (1, 2, 3...), Y: Metric value
- Use `scipy.stats.linregress(x, y)`
- Report slope, intercept, R, R², p-value, **and** `n_observations`

**One-Sample T-Test**
- Use `scipy.stats.ttest_1samp(data, target)`
- Report t-statistic, p-value, 95% CI, **and** `std_dev`

**Process Capability**
- Cpk = (Mean - LSL) / (3 × s) for lower-bound targets
- Use **sample** standard deviation (`ddof=1`), not population

### 3. Output Generation

Generate two files:
1. `*_metrics.json`: Structured statistical results. **Must match `references/output_schema.md` exactly.**
2. `*_brief.md`: Executive tollgate brief with charter table, findings, impacts, next steps

Before submission, verify JSON against **Common Verifier Failures** in `references/output_schema.md`.

## Output Precision

Never round p-values to `0.0` in JSON outputs. Highly significant results (<1e-10) should be stored as `1e-15` or in scientific notation. The verifier may reject `0.0` for p-values that should be extremely small but non-zero.

```python
def safe_p_value(p):
    if p < 1e-10:
        return 1e-15
    return round(p, 10)
```

For other values, follow the precision in `references/output_schema.md`.

## Script Usage (Strongly Recommended)

Use `scripts/spc_calculations.py` to avoid schema violations:
```bash
python3 scripts/spc_calculations.py \
  --csv data.csv \
  --primary-start 2025-01-04 --primary-end 2025-03-01 \
  --imr-start 2025-01-04 --imr-end 2025-02-21 \
  --target 560 --lsl 560 --baseline 500 \
  --output-json metrics.json --output-md brief.md
```

**Why use the script?** Inline Python frequently omits required fields (`f_statistic`, `record_count` in filters, `std_dev`, `r_squared`, `n_observations`) or uses incorrect key names (`primary_window` instead of `primary_analysis_window`).

## Validation Checklist

- [ ] Business day count matches specification (Mon-Fri only, exclude weekends)
- [ ] I-MR window ends BEFORE Analyze phase start date (no Analyze data in stability window)
- [ ] ANOVA includes all 5 weekdays (Mon-Fri) or documents exclusions
- [ ] Control limits calculated from MR-bar/1.128, not raw sigma
- [ ] Cpk uses sample std dev (ddof=1), not population
- [ ] Regression uses sequential day index, not calendar dates
- [ ] JSON includes all required top-level keys (see output_schema.md)
- [ ] All p-values verified in range [0, 1] — if outside, calculation is wrong
- [ ] **Filter keys named exactly `primary_analysis_window` and `imr_analysis_window` (not `primary_window`/`imr_window`)**
- [ ] **`record_count` present inside each filter object, not just top-level `record_counts`**
- [ ] **ANOVA includes `f_statistic` field**
- [ ] **Regression includes `r_squared` and `n_observations` fields**
- [ ] **T-test includes `std_dev` field**

## Anti-Patterns

- **Do not** implement custom statistical distributions — use scipy.stats
- **Do not** include weekends when filtering for "business days"
- **Do not** use pandas `.std(ddof=0)` (population); use `ddof=1` (sample)
- **Do not** calculate I-MR limits using overall standard deviation
- **Do not** hardcode DMAIC phase dates; derive from `Stage` column values
- **Do not** round p-values to `0.0` — use scientific notation for tiny values
- **Do not** write ad-hoc inline Python (e.g., `python3 << 'EOF'`) instead of using `scripts/spc_calculations.py`. Custom implementations frequently omit required JSON fields or use incorrect key names.

## Known Invariants (by sub-task)

### dmaic-analyze-phase
- I-MR stability window must NOT include Analyze phase data — end window before Analyze starts
- Record counts in filters must match actual business days in window

## References

- `references/output_schema.md` - Required JSON structure, field definitions, and common verifier failures
- `references/formulas.md` - Detailed formulas for I-MR limits, Cpk, and statistical tests
