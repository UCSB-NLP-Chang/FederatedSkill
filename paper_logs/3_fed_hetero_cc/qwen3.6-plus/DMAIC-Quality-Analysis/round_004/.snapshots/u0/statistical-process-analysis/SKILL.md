---
name: statistical-process-analysis
description: Analyzes time-series CSV data using SPC and hypothesis testing for DMAIC projects. Computes ANOVA, I-MR charts, regression, t-tests, and Cpk. Outputs JSON metrics and Markdown brief. Use for DMAIC Analyze phase tollgate tasks with CSV inputs containing date columns and numeric metrics.
---

# Statistical Process Analysis

## When to Use
- CSV with date column + numeric metric column
- DMAIC Analyze phase: SPC charts, ANOVA, capability indices, trend analysis
- Task patterns matching `*_analyze_*` or tollgate brief requirements

## Execution (GATED WORKFLOW - each step is a hard checkpoint)

### Step 1: Run compute_spc.py - REQUIRED
```bash
python3 scripts/compute_spc.py \
  --input <csv_path> --date-col <col> --value-col <col> \
  --target <num> --baseline <num> \
  --start <YYYY-MM-DD> --end <YYYY-MM-DD> \
  --imr-end <YYYY-MM-DD> --output spc_metrics.json
```
**If this fails, the task fails. Do NOT write custom computation code.**
**Do NOT compute statistics manually - the script handles everything.**

### Step 2: Validate JSON - REQUIRED CHECKPOINT
```bash
python3 scripts/validate_schema.py spc_metrics.json
```
**Must output "Schema validation passed" before proceeding.**
See `references/schema.md` for complete schema reference.

### Step 3: Generate Deliverables
Read `spc_metrics.json` and create:

1. **Metrics JSON**: Copy `spc_metrics.json` to required output path
2. **Brief Markdown**: Generate tollgate brief with required sections

**CRITICAL**: Check task requirements for exact output filenames. Common patterns:
- `<project>_analyze_metrics.json` / `<project>_analyze_brief.md`
- `metrics.json` / `brief.md` in specified directory

**Brief Required Sections** (verify against task):
- Project Charter (baseline, target, current mean)
- Statistical Analysis (ANOVA, I-MR, Regression, t-test, Capability)
- A3 Summary (Problem, Current State, Root Causes)
- Timeline / Next Steps

See `references/output-templates.md` for brief structure templates.

### Step 4: Verify Deliverables (Final Checkpoint)
```bash
python3 scripts/verify_deliverables.py --metrics <path> --brief <path>
```
**Run before claiming completion. Catches missing sections and file errors.**

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: write `x` as a raw float without any formatting
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-Patterns
- Do NOT proceed without passing validation checkpoint
- Do NOT write custom ANOVA/t-test/regression code - use the script only
- Do NOT modify JSON structure - use exactly what the script produces
- Do NOT assume default output filenames - check task requirements

## Known invariants (by sub-task)

### time-series-spc-tollgate
- Business-day filter: only Monday-Friday included; weekends excluded before any computation
- All statistical calculations are done by the script; do not implement manually
- JSON keys must match schema exactly: `primary_date_range` (not `date_range_primary`), `primary_window_business_days` (not `business_days_primary`)
- p-values must be in (0, 1) exclusive range - if you see 0.0 or 1.0, re-run the script

### field-service-work-orders
See `references/field_service_example.md` for exact invocation and expected output structure for harbor field service DMAIC analysis.