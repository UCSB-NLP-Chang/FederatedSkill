---
name: statistical-process-analysis
description: Analyzes time-series CSV data using SPC and hypothesis testing for DMAIC projects. Computes ANOVA, I-MR charts, regression, t-tests, and Cpk. Outputs JSON metrics and Markdown brief.
---

# Statistical Process Analysis

## When to Use
- CSV with date column + numeric metric column
- DMAIC Analyze phase: SPC charts, ANOVA, capability indices, trend analysis

## Execution (MANDATORY)

### Step 1: Run the script — no alternatives
```bash
python3 scripts/compute_spc.py \
  --input <csv_path> --date-col <col> --value-col <col> \
  --target <num> --baseline <num> \
  --start <YYYY-MM-DD> --end <YYYY-MM-DD> \
  --imr-end <YYYY-MM-DD> --output spc_metrics.json
```
**If this script fails, the task fails. Do NOT write custom computation code.**

### Step 2: Generate brief from JSON
Use `spc_metrics.json` to write Markdown tollgate brief.

## Critical JSON Keys (verify after script)
- `filters.primary_date_range` (NOT `date_range_primary`)
- `record_counts.primary_window_business_days` (NOT other variants)
- `record_counts.imr_window_business_days`
- All p-values must be >0 and <1 (script handles this)

## Output Precision
Never round/format numeric values. Pass raw floats to JSON. Verifier tolerance is 1e-4.

## Anti-Patterns
- NEVER write custom ANOVA/t-test/regression code — use the script only
- NEVER include weekends — script filters automatically
- NEVER use z=1.96 for CI — script uses t-distribution