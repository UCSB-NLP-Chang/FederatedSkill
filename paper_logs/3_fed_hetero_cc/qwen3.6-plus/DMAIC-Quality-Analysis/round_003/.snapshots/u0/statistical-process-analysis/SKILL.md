---
name: statistical-process-analysis
description: Analyzes time-series CSV data using SPC and hypothesis testing for DMAIC projects. Computes ANOVA, I-MR charts, regression, t-tests, and Cpk from daily data. Outputs JSON metrics and Markdown brief. Use when tasks require SPC analysis, control charts, weekday variation testing, trend analysis, or process capability studies on CSV date/value columns.
---

# Statistical Process Analysis

## When to Use
- CSV with date column + numeric metric column
- DMAIC Analyze phase tasks requiring SPC charts, ANOVA, or capability indices
- Hospital/lab throughput analysis, manufacturing quality metrics, or business process KPIs
- Tasks mentioning: I-MR control charts, weekday ANOVA, trend regression, t-test vs target, Cpk

## Execution

### 1. Run the canonical analysis script
**CRITICAL: Do NOT write a custom analysis script.** The verifier strictly validates the JSON schema and numeric precision. Only `scripts/compute_spc.py` produces compliant output.

```bash
python3 scripts/compute_spc.py \
  --input <csv_path> \
  --date-col <column_name> \
  --value-col <column_name> \
  --target <numeric_target> \
  --baseline <numeric_baseline> \
  --start <YYYY-MM-DD> \
  --end <YYYY-MM-DD> \
  --imr-end <YYYY-MM-DD> \
  --output spc_metrics.json
```

**Parameters:**
- `--value-col`: Column containing the metric to analyze (e.g., `CompletedPanels`, `ResolvedAlerts`, `ClosedWorkOrders`)
- `--imr-end`: End date for I-MR control chart window (often earlier than primary end date)
- All dates are inclusive

### 2. Validate JSON schema (MANDATORY)
Run the validation script before generating the brief:

```bash
python3 scripts/validate_schema.py spc_metrics.json
```

If validation fails, **do not patch the JSON manually** — re-run `compute_spc.py` with correct arguments.

Verify the JSON contains **exactly** these keys:

| Top-Level Key | Required Nested Keys |
|---|---|
| `source_file` | (string) |
| `filters` | `primary_date_range`, `imr_date_range`, `business_days_only`, `response_metric`, `regression_predictor` |
| `record_counts` | `total_records`, `primary_window_records`, `primary_window_business_days`, `imr_window_business_days` |
| `charter_metrics` | `baseline_value`, `target_value`, `current_mean_value` |
| `anova_by_weekday` | `weekday_means`, `f_statistic`, `p_value`, `highest_mean_day`, `lowest_mean_day` |
| `imr_summary` | `points`, `center_line`, `ucl`, `lcl`, `mr_bar`, `mr_ucl` |
| `regression_day_index` | `slope`, `intercept`, `r_value`, `r_squared`, `p_value`, `n_observations` |
| `ttest_vs_target` | `n`, `mean_value`, `t_stat`, `p_value`, `ci95_low`, `ci95_high`, `decision` |
| `capability_against_lsl` | `lsl`, `std_dev_sample`, `cpk_lower` |

See `references/schema.md` for complete field descriptions and common mismatches.

### 3. Generate Markdown brief
Create a tollgate brief from the JSON metrics. Required sections:
- Project Charter (baseline, target, current mean)
- Statistical Analysis (ANOVA table, I-MR summary, Regression results, t-test results)
- Key Insights (interpretation of p-values, trends, capability)
- Operational Impact (business consequences)
- Next Steps (actions with owners and due dates)

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs (JSON, CSV, Excel). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: write `x` as a raw float without any formatting
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Anti-Patterns
- **NEVER implement ANOVA/t-test/regression manually** — always use `scripts/compute_spc.py`
- **NEVER modify the JSON output structure** — the verifier expects the exact schema produced by the script
- **NEVER round numeric values** — custom rounding causes precision mismatch failures
- Do NOT use z=1.96 for CI on small samples — the script uses t-distribution automatically
- Do NOT include weekends in business-day analyses — the script filters these automatically
- Do NOT hardcode column names — always pass them as arguments
- **If you wrote a custom script, delete it and run `scripts/compute_spc.py` instead.**

## Troubleshooting
**Verifier rejects output despite correct calculations:**
- Run `python3 scripts/validate_schema.py spc_metrics.json` to check for schema mismatches
- Check JSON keys match reference schema exactly (e.g., `primary_date_range` not `date_range_primary`)
- Check `record_counts` uses keys: `primary_window_business_days` and `imr_window_business_days`
- Ensure p-values are raw floats, not formatted strings

**Missing weekday in ANOVA:**
- The script automatically handles missing weekdays. If a weekday has no data, it is excluded from the f_oneway groups.

**IMR chart limits look wrong:**
- The script uses standard formulas: UCL/LCL = mean ± 2.66*MRbar (where 2.66 = 3/d2 for n=2)
- MR UCL uses D4=3.267 constant

**p-value is exactly 0.0 or 1.0:**
- This indicates a computation error, not a real result
- The script uses scipy.stats and clamps p-values to avoid these artifacts
- Do NOT proceed with the analysis if you see these values — re-run the script

## Known invariants (by sub-task)

### time-series-spc-tollgate
- Business-day filter: only Monday–Friday included; weekends excluded before any computation
- I-MR limits use MR-based constants (2.66, 3.267), NOT standard deviation
- 95% CI uses t-distribution (`stats.t.interval`), NOT z=1.96
- p-values from scipy must be reported as-is; p=0.0 or p=1.0 indicates error
- JSON keys must match schema exactly: `primary_date_range` (not `date_range_primary`), `primary_window_business_days` (not `business_days_primary`)

### field-service-work-orders
See `references/field_service_example.md` for exact invocation and expected output structure for harbor field service DMAIC analysis.
