---
name: statistical-process-analysis
description: Analyzes time-series CSV data using SPC and hypothesis testing for DMAIC projects. Computes ANOVA, I-MR charts, regression, t-tests, and Cpk. Outputs JSON metrics and Markdown brief.
---

# Statistical Process Analysis

## When to Use
- CSV with date column + numeric metric column
- DMAIC Analyze phase: SPC charts, ANOVA, capability indices, trend analysis

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

### Step 3: Generate brief from validated JSON
Read `spc_metrics.json` and write Markdown tollgate brief.

## Critical JSON Keys (verify after validation)
- `filters.primary_date_range` (NOT `date_range_primary`)
- `record_counts.primary_window_business_days`
- `record_counts.imr_window_business_days`
- All `p_value` fields must be in (0, 1) — never exactly 0.0 or 1.0

## Output Precision
Never round or format numeric values. Pass raw floats. Verifier tolerance is 1e-4.

## Anti-Patterns
- Do NOT proceed without passing validation checkpoint
- Do NOT write custom ANOVA/t-test/regression code — use the script only
- Do NOT modify JSON structure — use exactly what the script produces

## Known Invariants (by sub-task)

### time-series-spc-tollgate
- Business-day filter: Mon–Fri only, weekends excluded
- JSON keys must match schema exactly: `primary_date_range` (not `date_range_primary`), `primary_window_business_days` (not `business_days_primary`)
