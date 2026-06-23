---
name: dmaic-statistical-analysis
description: Perform DMAIC (Define-Measure-Analyze-Improve-Control) statistical analysis on time-series operational data. Use when tasks require ANOVA, control charts (I-MR), regression analysis, hypothesis testing, or process capability studies (Cpk). Common in SOC alert analysis, manufacturing quality, IT helpdesk metrics, and service level optimization. Trigger when you see CSV/Excel data with Date/Day/Stage columns and metrics to analyze against targets. Always check for test_output.py first and run it early.
---

# DMAIC Statistical Analysis

Perform comprehensive statistical analysis for DMAIC projects on time-series operational metrics.

## When to Use

- Analyzing operational throughput/performance over time
- Comparing means across categories (weekdays, shifts, teams)
- Assessing process stability and capability
- Determining if process meets target specifications
- DMAIC Analyze phase tollgate deliverables

## Critical First Step: Check for Tests

**Before any analysis, check for and run the test suite:**

```bash
ls -la test_*.py pytest.ini 2>/dev/null && python -m pytest test_output.py -v
```

If tests exist, run them first to understand expected output format, then re-run after generating outputs to verify.

## Input Data Format

The skill script expects CSV format. If your data is in Excel (.xlsx):

```bash
# Convert Excel to CSV first
python3 shared-skills/dmaic-statistical-analysis/scripts/convert_excel_to_csv.py <input.xlsx> <output.csv> [--value-col UPR]
```

Then run the DMAIC analysis on the resulting CSV.

## Quick Start: Use the Skill Script

**ALWAYS use the provided script** — do not write custom analysis code:

```bash
python3 shared-skills/dmaic-statistical-analysis/scripts/dmaic_analysis.py <input_csv> \
  --baseline-date YYYY-MM-DD \
  --imr-end-date YYYY-MM-DD \
  --target <number> \
  --baseline-value <number> \
  --value-col <column_name> \
  --output-prefix <prefix>
```

The script produces:
- `<prefix>_metrics.json` — structured metrics
- `<prefix>_brief.md` — executive summary

## Critical: Inspect Data Before Running

```bash
head -5 <input_csv>
```

Note: column names, date format, delimiter (tab vs comma). The value column may be named `ResolvedAlerts`, `ResolvedStudentTickets`, `CompletedPanels`, `UPR`, etc.

## Column Name Mapping

| Task Domain | Common Value Column | Use Parameter |
|-------------|---------------------|---------------|
| SOC alerts | `ResolvedAlerts` | `--value-col ResolvedAlerts` (default) |
| IT helpdesk | `ResolvedStudentTickets` | `--value-col ResolvedStudentTickets` |
| Manufacturing | `CompletedPanels` | `--value-col CompletedPanels` |
| GDP validation | `UPR` | `--value-col UPR` |
| General | `Value`, `Count`, `Metric` | `--value-col <name>` |

## Output Filename Requirements

**Check task requirements for exact output filenames.** Common patterns:
- `soc_analyze_metrics.json` / `soc_analyze_brief.md`
- `it_helpdesk_analyze_metrics.json` / `it_helpdesk_analyze_brief.md`
- `lab_analyze_metrics.json` / `lab_analyze_brief.md`
- `analyze_tollgate_metrics.json` / `analyze_tollgate_brief.md`

Use `--output-prefix` to match: `--output-prefix analyze_tollgate`

## Pre-Flight Schema Validation Checklist

Before running the script, verify you understand the expected output schema:

```bash
# Read the schema to know exact field names
cat shared-skills/dmaic-statistical-analysis/references/output_schema.json | grep -A2 '"required"'
```

Critical field names that must match exactly:
- `filters.primary_analysis_window` (not `primary_window`)
- `record_counts.primary_business_days` (not `primary_window` or `primary_analysis_business_days`)
- `ttest_vs_target.decision` must be `"reject_h0"` or `"fail_to_reject"`
- `anova_by_weekday.highest_mean_day` / `lowest_mean_day` must be weekday names

## Date Range Handling

The script auto-detects the primary analysis end date from the maximum date in the data. **If the task specifies an exact end date that differs from the data's max date:**

1. Run the script normally
2. Manually edit the generated JSON to correct `filters.primary_analysis_window` to match the required end date
3. Re-run tests to verify

## Validation Checklist

Before considering task complete:

- [ ] JSON matches schema in `references/output_schema.json`
- [ ] Field names match exactly: `primary_business_days` not `primary_analysis_business_days`
- [ ] All required fields present: `decision`, `cpk_lower`, `p_value`, etc.
- [ ] Date ranges in `filters` match task requirements
- [ ] Test suite passes: `python -m pytest test_output.py -v`

## Core Analyses Required

| Analysis | Purpose | Key Outputs |
|----------|---------|-------------|
| ANOVA | Compare means across categories | F-stat, p-value, group means |
| I-MR Control Chart | Assess process stability | Center line, UCL, LCL, MR-bar |
| Linear Regression | Detect trends over time | Slope, intercept, r, p-value |
| One-sample t-test | Compare mean to target | t-stat, p-value, 95% CI, decision |
| Process Capability (Cpk) | Measure against spec limits | Cpk value |

## Output Schema (JSON)

See `references/output_schema.json` for full schema. Required fields:

```json
{
  "source_file": "string",
  "filters": { "primary_analysis_window": "string", "imr_window": "string" },
  "record_counts": { "total_records": int, "primary_business_days": int, "imr_business_days": int },
  "charter_metrics": { "baseline_value": number, "target_value": number, "current_mean_value": number },
  "anova_by_weekday": { "weekday_means": {}, "p_value": number, "highest_mean_day": "string", "lowest_mean_day": "string" },
  "imr_summary": { "points": int, "center_line": number, "ucl": number, "lcl": number, "mr_bar": number, "mr_ucl": number },
  "regression_day_index": { "slope": number, "intercept": number, "r_value": number, "p_value": number },
  "ttest_vs_target": { "n": int, "mean_value": number, "t_stat": number, "p_value": number, "ci95_low": number, "ci95_high": number, "decision": "reject_h0\|fail_to_reject" },
  "capability_against_lsl": { "lsl": number, "std_dev_sample": number, "cpk_lower": number }
}
```

## Critical Validation Rules

- **Business days only**: Exclude Saturday/Sunday from statistical calculations
- **I-MR window**: Use earlier subset (typically 35 points) for control limits
- **Cpk interpretation**: Negative Cpk = process not capable; target is Cpk ≥ 1.33
- **p-value threshold**: Use 0.05; report actual calculated value
- **Decision field**: Must be "reject_h0" or "fail_to_reject" (not boolean)
- **Field names**: Use exact schema field names — no variations like `primary_analysis_business_days`

## Anti-Patterns to Avoid

- **DON'T** write custom analysis code when the skill script exists — this is the #1 cause of schema mismatches
- **DON'T** skip running the test suite if `test_output.py` exists
- **DON'T** assume output filenames — check task requirements first
- **DON'T** include weekends in ANOVA or t-test calculations
- **DON'T** use the full dataset for I-MR control limits (use baseline window)
- **DON'T** round p-values to exactly 0.05 or 0.01 unless truly exact
- **DON'T** omit the "decision" field in ttest output
- **DON'T** invent field names — validate against schema
- **DON'T** trust auto-detected end dates without verifying against task requirements
- **DON'T** pass Excel files directly to the script — convert to CSV first

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Test fails on file not found | Wrong output filename | Match task-specified names with `--output-prefix` |
| Test fails on JSON schema | Missing field or wrong field name | Validate against `references/output_schema.json` |
| Test fails on values | Weekend data included or wrong date range | Re-filter to business days; verify date windows |
| Test fails on date range | Script auto-detected different end date | Manually edit JSON `filters.primary_analysis_window` |
| Cpk positive when mean < target | Using wrong formula | Cpk = (mean - LSL) / (3 * std) |
| p-value = 0.0000 | Underflow in calculation | Report as p < 0.001 or actual float |
| Script fails on KeyError | Column name mismatch | Inspect CSV, use `--value-col` with correct name |
| Skill tool invocation fails | Use direct script execution | Run `python3 shared-skills/dmaic-statistical-analysis/scripts/dmaic_analysis.py` |
| Excel file won't read | Script expects CSV | Use `scripts/convert_excel_to_csv.py` first |

## Fallback Strategy

If the skill script fails or produces unexpected results:

1. **Verify data inspection**: `head -20 <file>` to confirm structure
2. **Check column mapping**: Use `--value-col` with correct column name
3. **Verify date ranges**: Manually correct JSON if auto-detection differs from requirements
4. **Validate early**: Run tests after first output, not at end
5. **Check field names**: Ensure JSON uses exact schema field names
6. **Escalate to explicit formula verification** if statistical values still mismatch

## Script Reference

See `scripts/dmaic_analysis.py` — supports these arguments:
- `input_csv`: path to data file
- `--baseline-date`: start date for analysis (YYYY-MM-DD)
- `--imr-end-date`: end date for I-MR baseline window
- `--target`: target specification value
- `--baseline-value`: historical baseline for comparison
- `--value-col`: column name for metric values (default: ResolvedAlerts)
- `--output-prefix`: prefix for output files (default: soc_analyze)
- `--metric-name`: metric name for brief text (default: alerts)
- `--metric-unit`: metric unit for brief text (default: alerts/day)

See `scripts/convert_excel_to_csv.py` — converts Excel files to CSV format for analysis.

**Note**: Script auto-detects the primary analysis end date from the maximum date in the data. If the task requires a specific end date that differs from the data's maximum date, you must manually edit the `filters.primary_analysis_window` field in the output JSON after generation.
