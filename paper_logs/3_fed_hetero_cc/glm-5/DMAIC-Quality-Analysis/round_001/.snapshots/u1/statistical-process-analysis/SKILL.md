---
name: statistical-process-analysis
description: Analyzes time-series CSV data using statistical process control (SPC) and hypothesis testing. Use when tasked with computing ANOVA, I-MR charts, regression trends, t-tests against targets, or process capability (Cpk) from daily operational data. Trigger phrases include 'statistical analysis', 'ANOVA', 't-test', 'regression', 'control chart', 'I-MR', 'capability', 'Cpk', 'p-value', 'tollgate', 'DMAIC'.
---

# Statistical Process Analysis Workflow

## When to Use
- Input is a CSV with dates and a numeric metric.
- Task requires SPC charts (I-MR), trend analysis, weekday effects, or capability indices.
- Output must include structured JSON metrics and a Markdown brief.

## Execution Steps
1. **Inspect CSV**: Identify date column, value column, and date range. Confirm business-day filtering requirement.
2. **Run Computation Script**:
   ```bash
   python3 scripts/compute_spc.py \
     --input <csv_path> \
     --date-col <date_column> \
     --value-col <metric_column> \
     --target <target_value> \
     --baseline <baseline_value> \
     --start <YYYY-MM-DD> \
     --end <YYYY-MM-DD> \
     --imr-end <YYYY-MM-DD> \
     --output spc_metrics.json
   ```
3. **Verify JSON**: Read `spc_metrics.json` and confirm all expected keys are present. P-values must be in (0, 1] — if you see `p_value: 0.0` or `p_value: 1.0`, the script had an error.
4. **Generate Brief**: Use the JSON to populate the Markdown tollgate brief. Include charter, statistical results, A3 summary, and next steps.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-Patterns
- Do not manually compute ANOVA, t-tests, or regression — the script uses scipy for all hypothesis tests.
- Do not include weekends in business-day analyses unless explicitly requested.
- Do not use z=1.96 for confidence intervals on small samples — use t-distribution via `stats.t.interval()`.
- Do not treat the regression R² as a measure of statistical significance; rely on the slope p-value.
- A p-value of exactly 0.0 or 1.0 is always a computation error, never a real result.

## Fallback
If the script fails due to environment constraints, compute metrics using `scipy.stats` directly:
- `scipy.stats.f_oneway()` for ANOVA
- `scipy.stats.ttest_1samp()` for t-tests
- `scipy.stats.linregress()` for regression
- `scipy.stats.t.interval()` for confidence intervals
See `references/spc_formulas.md` for formula reference.

## Known invariants (by sub-task)

### B1-spc-tollgate
- Filter to business days (Mon-Fri) before any computation.
- I-MR limits use constants 2.66 and 3.267 multiplied by MR_bar, NOT standard deviation.
- 95% CI for t-test uses t-distribution, NOT z=1.96.
- JSON must contain keys: source_file, filters, record_counts, charter_metrics, anova_by_weekday, imr_summary, regression_day_index, ttest_vs_target, capability_against_lsl.
