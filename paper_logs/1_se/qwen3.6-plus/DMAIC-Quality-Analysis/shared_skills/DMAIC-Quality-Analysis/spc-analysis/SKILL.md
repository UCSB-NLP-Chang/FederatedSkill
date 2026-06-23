---
name: spc-analysis
description: Performs Statistical Process Control (SPC) and Six Sigma analysis on time-series CSV or Excel data. Use when tasked with computing control charts (I-MR), ANOVA by weekday, regression trends, t-tests against targets, and process capability (Cpk), then generating structured JSON metrics and a Markdown brief.
---

# Statistical Process Control (SPC) Analysis

## Workflow
1. **Ingest**: Identify the data file (`.csv` or `.xlsx`). The helper script handles both formats natively.
2. **Compute Metrics**: Run `scripts/compute_spc_metrics.py <data_path> <target_value> [metric_column]`. 
   - The script auto-detects the metric column if not provided.
   - It outputs a JSON object to stdout that strictly matches `references/output_schema.md`.
   - **CRITICAL: Do not write a custom Python script.** Hand-rolled scripts consistently fail schema validation, introduce syntax errors, and miscalculate degrees of freedom. Always use the provided helper.
3. **Generate JSON**: Capture the script's stdout directly into your metrics JSON file. 
   - **Validate Schema Immediately**: Run `python3 -c "import json,sys; d=json.load(sys.stdin); assert 'date_range_primary' in d['filters']; assert 'total_rows_in_file' in d['record_counts']; assert 'df_between' in d['anova_by_weekday']; assert 'decision' in d['ttest_vs_target']; print('Schema OK')" < metrics.json`.
   - **Common Pitfalls**: 
     - `filters.date_range_primary` (not `date_range_start`)
     - `record_counts.total_rows_in_file` (not `total_raw`)
     - `imr_summary.points` must be an `int`, not an array.
     - `anova_by_weekday` must include `df_between` and `df_within`.
     - `ttest_vs_target` must include `decision` ("reject_h0" or "fail_to_reject_h0").
     - `regression_day_index` must include `n`, not `r_squared` or `std_err`.
4. **Draft Brief**: Populate the Markdown brief using the exact computed values. Follow the section structure in `references/output_schema.md`.
5. **Cross-Check Consistency**: Before finalizing, verify that every narrative claim matches the computed statistics.
   - If ANOVA p < 0.05, state "significant weekday effect".
   - If I-MR has points outside UCL/LCL, explicitly note "special-cause variation detected" and count them.
   - If regression p > 0.05, state "no significant trend".
   - If Cpk < 1.0, state "process not capable".

## Anti-Patterns
- **Do not** write conclusions before verifying p-values and control limits. Contradictory narratives cause verifier failures.
- **Do not** ignore out-of-control points in I-MR charts. Always count and report them.
- **Do not** mix calendar days and business days in the same metric without explicit labeling.
- **Do not** bypass `scripts/compute_spc_metrics.py`. Custom scripts frequently miss required schema keys or miscalculate degrees of freedom.
- **Do not** flatten nested JSON keys. The verifier expects exact nesting (e.g., `filters.date_range_primary.start`).

## Troubleshooting
- **Verifier fails on JSON keys**: Compare your output against `references/output_schema.md`. Missing nested keys or wrong data types are common failure points.
- **Markdown inconsistencies**: Run a quick string match to ensure numbers in the text exactly match the JSON values.
- **Missing dependencies**: The helper script requires `pandas` and `scipy`. If unavailable, install via `pip install pandas scipy openpyxl`.
- **Excel read errors**: Ensure the Excel file has a header row. If `openpyxl` is missing, install it.