---
name: statistical-process-analysis
description: Analyzes time-series CSV data using SPC and hypothesis testing for DMAIC projects. Computes ANOVA, I-MR charts, regression, t-tests, and Cpk. Outputs JSON metrics and Markdown brief. Use for DMAIC Analyze phase tollgate tasks with CSV inputs containing date columns and numeric metrics.
---

# Statistical Process Analysis

## When to Use
- CSV with date column + numeric metric column
- DMAIC Analyze phase: SPC charts, ANOVA, capability indices, trend analysis
- Task patterns matching `*_analyze_*` or tollgate brief requirements

## Execution (GATED WORKFLOW — each step is a hard checkpoint)

### Step 1: Run compute_spc.py — REQUIRED
```bash
python3 scripts/compute_spc.py \
  --input <csv_path> --date-col <col> --value-col <col> \
  --target <num> --baseline <num> \
  --start <YYYY-MM-DD> --end <YYYY-MM-DD> \
  --imr-end <YYYY-MM-DD> --output spc_metrics.json
```
**If this fails, the task fails. Do NOT write custom computation code.**

### Step 2: Validate JSON — REQUIRED CHECKPOINT
```bash
python3 scripts/validate_schema.py spc_metrics.json
```
**Must output "Schema validation passed" before proceeding.**

Verify key names match this table:

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

See `references/schema.md` for full field descriptions and common mismatches.

### Step 3: Generate Deliverables
Read `spc_metrics.json` and create:

1. **Metrics JSON**: Copy `spc_metrics.json` to the output path specified in the task
2. **Brief Markdown**: Generate tollgate brief using the template in `references/output-templates.md`

**CRITICAL**: Check task requirements for exact output filenames. Common patterns:
- `<project>_analyze_metrics.json` / `<project>_analyze_brief.md`
- `metrics.json` / `brief.md` in specified directory
- If task specifies exact paths, use them; otherwise derive from task name prefix

**Brief Required Sections** (verify against task):
- Project Charter (baseline, target, current mean)
- Statistical Analysis (ANOVA, I-MR, Regression, t-test, Capability)
- A3 Summary (Problem, Current State, Root Causes)
- Timeline / Next Steps

### Step 4: Verify Deliverables (Final Checkpoint)
```bash
python3 scripts/verify_deliverables.py --metrics <path> --brief <path>
```
**Run before claiming completion. Catches missing sections and file errors.**

## Output Precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision

## Anti-Patterns
- Do NOT proceed without passing validation checkpoint
- Do NOT write custom ANOVA/t-test/regression code — use the script only
- Do NOT modify JSON structure — use exactly what the script produces
- Do NOT assume default output filenames — check task requirements

## References
- `references/schema.md` — Complete JSON schema with common mismatches
- `references/output-templates.md` — Brief structure templates and file naming patterns
- `references/field_service_example.md` — Concrete invocation example
- `scripts/compute_spc.py` — Statistical computation (REQUIRED)
- `scripts/validate_schema.py` — JSON schema validation (REQUIRED)
- `scripts/verify_deliverables.py` — Final output verification (REQUIRED)

## Known Invariants (by Sub-Task)

### B1-spc-tollgate
- Business-day filter: Mon–Fri only; weekends excluded before any computation
- JSON keys must match schema exactly: `primary_date_range` (not `date_range_primary`), `primary_window_business_days` (not `business_days_primary`)
- All `p_value` fields must be in (0, 1) exclusive — p=0.0 or p=1.0 indicates script failure
- Output filenames must match task specification exactly
- Brief must include A3 Summary and Timeline/Next Steps sections
