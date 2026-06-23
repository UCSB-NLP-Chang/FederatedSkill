---
name: statistical-process-analysis
description: Analyzes time-series CSV data using SPC and hypothesis testing for DMAIC projects. Computes ANOVA, I-MR charts, regression, t-tests, and Cpk. Outputs JSON metrics and Markdown brief. Use for DMAIC Analyze phase tollgate tasks with CSV inputs containing date columns and numeric metrics.
---

# Statistical Process Analysis

## When to Use
- CSV with date column + numeric metric column
- DMAIC Analyze phase tollgate brief requirements
- Task patterns matching `*_analyze_*`

## Execution (GATED WORKFLOW)

### Step 0: Convert Excel to CSV (if .xlsx input)
```bash
python3 -c "import pandas as pd; pd.read_excel('input.xlsx').to_csv('input.csv', index=False)"
```

### Step 1: Run compute_spc.py
```bash
python3 scripts/compute_spc.py \
  --input <csv_path> --date-col <col> --value-col <col> \
  --target <num> --baseline <num> \
  --start <YYYY-MM-DD> --end <YYYY-MM-DD> \
  --imr-end <YYYY-MM-DD> --output spc_metrics.json
```

### Step 2: Validate JSON
```bash
python3 scripts/validate_schema.py spc_metrics.json
```
Must output: `Schema validation passed`

### Step 3: Copy JSON and Generate Brief
1. Copy `spc_metrics.json` to task-specified output path
2. Generate tollgate brief with sections: Project Charter, Statistical Analysis, A3 Summary, Timeline/Next Steps

### Step 4: Verify Deliverables
```bash
python3 scripts/verify_deliverables.py --metrics <path> --brief <path>
```
Must output: `Deliverable verification passed.`

## Key Names (DO NOT RENAME)
| Correct Key | WRONG (common renames) |
|-------------|------------------------|
| `baseline_value` | `baseline_upr` |
| `target_value` | `target_upr` |
| `current_mean_value` | `mean_upr`, `current_mean_upr` |
| `mean_value` | `mean_upr` |
| `primary_date_range` | `date_range_primary` |

**JSON keys are fixed. Task-specific terminology goes in brief Markdown only.**

## Output Precision
Pass raw floats. DO NOT: `round()`, `format()`, `f"{x:.2f}"`.

## References
- `references/schema.md` — full schema
- `references/output-templates.md` — brief template
- `scripts/compute_spc.py` — computation
- `scripts/validate_schema.py` — validation
- `scripts/verify_deliverables.py` — verification
