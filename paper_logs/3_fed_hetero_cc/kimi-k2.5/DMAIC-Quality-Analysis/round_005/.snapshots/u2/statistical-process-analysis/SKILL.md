---
name: statistical-process-analysis
description: Analyzes time-series CSV data using SPC and hypothesis testing for DMAIC projects. Computes ANOVA, I-MR charts, regression, t-tests, and Cpk. Outputs JSON metrics and Markdown brief. Use for DMAIC Analyze phase tollgate tasks with CSV or Excel inputs containing date columns and numeric metrics.
---

# Statistical Process Analysis

## When to Use
- CSV or Excel with date column + numeric metric column
- DMAIC Analyze phase: SPC, ANOVA, capability indices, trend analysis
- Task patterns matching `*_analyze_*` or tollgate brief requirements

## Execution

### Step 0: Convert Excel to CSV (if input is .xlsx/.xls)
```bash
python3 -c "import pandas as pd; pd.read_excel('input.xlsx').to_csv('input.csv', index=False)"
```
Use the CSV file in subsequent steps.

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
Output must include: `Schema validation passed`

### Step 3: Output Files
1. Copy `spc_metrics.json` to task-specified output path
2. Generate brief Markdown with sections: Project Charter, Statistical Analysis, A3 Summary, Timeline/Next Steps

Check task requirements for exact output filenames.

### Step 4: Verify Deliverables
```bash
python3 scripts/verify_deliverables.py --metrics <path> --brief <path>
```

## JSON Keys
- `filters.primary_date_range` (string, not array)
- `record_counts.primary_window_business_days`
- `record_counts.imr_window_business_days`
- `anova_by_weekday.p_value`, `regression_day_index.p_value`, `ttest_vs_target.p_value` (all in (0,1) exclusive)
- `charter_metrics.baseline_value` (NOT `baseline_upr` or task-specific names)

## Output Precision
Pass raw float values directly. Do not round or format.
