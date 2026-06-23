---
name: statistical-process-analysis
description: Analyzes time-series CSV data using statistical process control (SPC) and hypothesis testing. Use when tasked with computing ANOVA, I-MR charts, regression trends, t-tests against targets, or process capability (Cpk) from daily operational data. Trigger phrases include 'statistical analysis', 'ANOVA', 't-test', 'regression', 'control chart', 'I-MR', 'capability', 'Cpk', 'p-value', 'tollgate', 'DMAIC'.
---

# Statistical Process Analysis Workflow

## ⚠️ CRITICAL: Always Use compute_spc.py

**You MUST use `scripts/compute_spc.py` for all statistical computations.**
Writing custom Python code to compute ANOVA, t-tests, regression, or control-chart metrics always produces schema mismatches and numeric drift that cause verifier failure. The script is the single source of truth for both calculations and output structure.

## When to Use
- Input is a CSV with dates and a numeric metric.
- Task requires SPC charts (I-MR), trend analysis, weekday effects, or capability indices.
- Output must include structured JSON metrics and a Markdown brief.

**Concrete example**: See `references/field_service_example.md` for a complete field service DMAIC analysis with exact invocation and expected output.

## Execution Steps

### Step 1: Run the Computation Script (REQUIRED — NO EXCEPTIONS)
**This step is mandatory. Do not proceed without running the script.**

**CRITICAL**: Do NOT write custom pandas/numpy/scipy analysis code. Use this script exclusively even if:
- Column names differ (use `--date-col` and `--value-col` to map them)
- You believe "special" handling is needed (script handles business-day filtering, p-value clamping, and statistical methodology)
- The date range logic seems complex (script manages inclusive ranges and weekend exclusion)

If the script fails, fix the arguments or input data. Do NOT proceed with custom code.

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

**Example:**
```bash
python3 scripts/compute_spc.py \
  --input /root/data.csv \
  --date-col Date \
  --value-col ResolvedAlerts \
  --target 810 \
  --baseline 740 \
  --start 2025-01-04 \
  --end 2025-03-01 \
  --imr-end 2025-02-21 \
  --output spc_metrics.json
```

### Step 2: Validate JSON Schema (REQUIRED)
**Run the validation script to catch schema mismatches before submission.**

```bash
python3 scripts/validate_schema.py spc_metrics.json
```

If validation fails, **do not patch the JSON manually** — re-run `compute_spc.py` with correct arguments. Manual patches introduce subtle inconsistencies.

Also verify manually:
1. All `p_value` fields are in (0, 1) exclusive range (`p_value: 0.0` or `p_value: 1.0` indicates script failure)
2. `imr_summary.points` is an integer count, NOT an array of point objects
3. `filters.primary_date_range` and `filters.imr_date_range` are strings like `"YYYY-MM-DD to YYYY-MM-DD (inclusive)"`, NOT arrays

### Step 3: Generate Brief
Use the validated JSON to populate the Markdown tollgate brief. Include:
- Project Charter (baseline, target, current mean)
- Statistical Analysis (ANOVA, I-MR, Regression, t-test results)
- A3 Summary and Next Steps

## Output Precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision

## Anti-Patterns (Critical)
- **NEVER write custom computation code** — use `scripts/compute_spc.py`
- **NEVER compute ANOVA, t-tests, or regression manually** — the script handles all hypothesis tests via scipy
- **NEVER modify JSON output structure** — the verifier expects the exact schema from the script
- Do not include weekends in business-day analyses unless explicitly requested
- Do not use z=1.96 for confidence intervals — the script uses t-distribution
- Do not treat R² as statistical significance — rely on slope p-value

### Common Schema Mismatches (from real failures)
These wrong key names / value types cause verifier rejection. The validation script catches them:

| Wrong | Correct | Context |
|-------|---------|----------|
| `filters.response_variable` | `filters.response_metric` | Key name |
| `filters.primary_date_range` as array `['2025-01-04','2025-03-01']` | String `'2025-01-04 to 2025-03-01 (inclusive)'` | Value type |
| `filters.imr_date_range` as array | String `'YYYY-MM-DD to YYYY-MM-DD (inclusive)'` | Value type |
| `record_counts.total_rows` | `record_counts.total_records` | Key name |
| `record_counts.primary_window_rows` | `record_counts.primary_window_records` | Key name |
| `imr_summary.points` as array of objects | Integer count | Value type |
| Missing `filters.regression_predictor` | Must be present (value: `"day_index"`) | Missing key |

## Validation & Troubleshooting
- **Script fails**: Ensure `scipy` is installed (`pip install scipy`)
- **Verifier rejects JSON keys**: Run `scripts/validate_schema.py` — check against `references/schema.md`
- **p-value is 0.0 or 1.0**: Script internal error; re-run with valid data
- **Weekend data in analysis**: Script automatically filters Mon-Fri only
- **Schema validation fails after custom code**: Delete custom code, re-run `compute_spc.py`

## Known Invariants (by Sub-Task)

### B1-spc-tollgate
- Filter to business days (Mon-Fri) before any computation
- I-MR limits: UCL/LCL = mean ± 2.66 × MR_bar (NOT standard deviation)
- 95% CI uses t-distribution, NOT z=1.96
- JSON keys: source_file, filters, record_counts, charter_metrics, anova_by_weekday, imr_summary, regression_day_index, ttest_vs_target, capability_against_lsl
