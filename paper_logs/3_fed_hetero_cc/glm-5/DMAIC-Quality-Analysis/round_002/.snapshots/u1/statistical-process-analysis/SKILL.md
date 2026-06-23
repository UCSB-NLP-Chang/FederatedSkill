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

### Step 1: Run the Computation Script (REQUIRED)
**This step is mandatory. Do not proceed without running the script.**

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

### Step 2: Validate JSON Output
Read `spc_metrics.json` and verify:
1. File exists and was created by the script
2. Contains all expected top-level keys (see `references/schema.md`)
3. All `p_value` fields are in (0, 1) exclusive range
   - `p_value: 0.0` or `p_value: 1.0` indicates script failure

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

## Validation & Troubleshooting
- **Script fails**: Ensure `scipy` is installed (`pip install scipy`)
- **Verifier rejects JSON keys**: Check against `references/schema.md` — keys must match exactly (e.g., `primary_date_range` not `date_range_primary`)
- **p-value is 0.0 or 1.0**: Script internal error; re-run with valid data
- **Weekend data in analysis**: Script automatically filters Mon-Fri only

## Known Invariants (by Sub-Task)

### B1-spc-tollgate
- Filter to business days (Mon-Fri) before any computation
- I-MR limits: UCL/LCL = mean ± 2.66 × MR_bar (NOT standard deviation)
- 95% CI uses t-distribution, NOT z=1.96
- JSON keys: source_file, filters, record_counts, charter_metrics, anova_by_weekday, imr_summary, regression_day_index, ttest_vs_target, capability_against_lsl
