---
name: statistical-process-analysis
description: Analyzes time-series CSV data using SPC and hypothesis testing for DMAIC projects. Computes ANOVA, I-MR charts, regression, t-tests, and Cpk. Outputs JSON metrics and Markdown brief. Use for DMAIC Analyze phase tollgate tasks with CSV or Excel inputs containing date columns and numeric metrics.
---

# Statistical Process Analysis

## When to Use
- CSV or Excel file with date column + numeric metric column
- DMAIC Analyze phase tollgate brief generation

## Execution

### Step 0: Convert Excel to CSV (if input is .xlsx)
```bash
python3 -c "import pandas as pd; pd.read_excel('input.xlsx').to_csv('input.csv', index=False)"
```
Use the resulting CSV for all subsequent steps.

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
Must output "Schema validation passed" before proceeding.

### Step 3: Copy JSON to Output Path
Copy `spc_metrics.json` to the output path specified in the task.
Check task for exact filename (e.g., `<project>_analyze_metrics.json`).

### Step 4: Generate Brief Markdown
Create tollgate brief with sections:
- Project Charter
- Statistical Analysis
- A3 Summary
- Timeline / Next Steps

See `references/output-templates.md` for structure.

### Step 5: Verify Deliverables
```bash
python3 scripts/verify_deliverables.py --metrics <json_path> --brief <md_path>
```

## Output Precision
Write raw float values directly. Do NOT use `round()`, `format()`, or `f"{x:.Nf}"`.

## Known Invariants

### time-series-spc-tollgate
- Business days only: Monday-Friday
- JSON keys match schema exactly: `primary_date_range` (not `date_range_primary`)
- Brief must include A3 Summary and Timeline sections
