---
name: statistical-process-analysis
description: Analyzes time-series CSV data using statistical process control (SPC) and hypothesis testing. Use when tasked with computing ANOVA, I-MR charts, regression trends, t-tests against targets, or process capability (Cpk) from daily operational data.
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
3. **Verify JSON**: Check that all keys match the expected schema. Ensure `p_value` fields are numeric and `decision` fields are populated.
4. **Generate Brief**: Use `spc_metrics.json` to populate the Markdown tollgate brief. Include charter, statistical results, A3 summary, and next steps.

## Validation & Troubleshooting
- **Missing `scipy`**: The script requires `scipy` for accurate p-values. Install via `pip install scipy` before running.
- **Weekday ANOVA**: Ensure only Monday–Friday are included. Weekends must be filtered out before grouping.
- **I-MR Limits**: Use `2.66 * MR_bar` for individual limits and `3.267 * MR_bar` for moving range limits. Do not use standard deviation-based limits for I-MR.
- **Cpk Interpretation**: Negative Cpk indicates the process mean is outside the specification limit. Report as-is.

## Anti-Patterns
- Do not manually compute control limits or p-values; use the bundled script to avoid arithmetic drift.
- Do not include weekends in business-day analyses unless explicitly requested.
- Do not treat the regression R² as a measure of statistical significance; rely on the slope p-value.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### time-series-spc-tollgate
- Business-day filter: only Monday–Friday included; weekends excluded.
- I-MR limits use MR-based constants (2.66, 3.267), NOT standard deviation.
- 95% CI uses t-distribution (`stats.t.interval`), NOT z=1.96.
- p-values from scipy must be reported as-is; p=0.0 or p=1.0 indicates error.

## Fallback
If the script fails due to environment constraints, compute metrics using `pandas` and `scipy.stats` directly, following the formulas in `references/spc_formulas.md`.
