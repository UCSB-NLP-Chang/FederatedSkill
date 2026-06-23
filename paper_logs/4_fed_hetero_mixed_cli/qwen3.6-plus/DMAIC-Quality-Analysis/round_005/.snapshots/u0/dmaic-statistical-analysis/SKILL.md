---
name: dmaic-statistical-analysis
description: Perform DMAIC Analyze phase statistical analysis on time-series operational data from CSV or Excel files. Computes Six Sigma metrics (ANOVA by weekday, I-MR control charts, linear regression, t-test vs target, Cpk) with business-day filtering and stage-aligned date windows. Use when generating tollgate deliverables from CSV or Excel data with charter parameters (Baseline, Target, LSL/USL).
---

# DMAIC Statistical Analysis

## 🚨 CRITICAL: DO NOT WRITE CUSTOM SCRIPTS
**The verifier strictly enforces exact JSON key names and nested structure. Custom scripts consistently fail due to subtle key mismatches.**
- **ALWAYS** use `scripts/compute_metrics.py` for calculations.
- **ALWAYS** use `assets/brief_template.md` for the markdown brief.
- **ALWAYS** read `references/output_schema.md` BEFORE writing JSON output.
- If you write a custom script, you will fail on key names like `primary_window` (should be `primary_analysis_window`), `total_records` (should be `total_records_in_source`), or forbidden extra fields like `df_between` or `points` arrays.

## When to Use
- Analyzing time-series operational data against targets or specification limits.
- Generating DMAIC Analyze phase tollgate deliverables (JSON + Markdown brief).
- Tasks requiring: ANOVA, I-MR control charts, regression, hypothesis testing, process capability.
- Input: CSV or Excel (.xlsx) with columns `{Date, Stage, Day, Metric}`; Charter parameters (Baseline, Target, LSL/USL).

## Pre-Flight Checklist
1. Locate `scripts/compute_metrics.py` in this skill directory.
2. Locate `assets/brief_template.md` in this skill directory.
3. Identify input format: CSV or Excel (.xlsx).
4. Parse the input to identify:
   - Metric column name
   - Business day boundaries (Mon-Fri only)
   - DMAIC phase start dates from `Stage` column
   - Primary window (~40 biz days ending at current phase)
   - I-MR stability window (~35 biz days ending BEFORE Analyze phase start)
5. Run the bundled script with exact CLI arguments. Do not modify it.

## Workflow

1. **Parse & Filter Data**
   - Load CSV or Excel file. Parse dates. Sort chronologically.
   - Filter to business days only (Mon-Fri, exclude weekends).
   - Identify DMAIC phase boundaries from `Stage` column.
   - Extract primary window: typically ~40 business days ending at current phase.
   - Extract I-MR stability window: ~35 business days ending BEFORE Analyze phase start.

2. **Compute Metrics via Script**
   - Run `scripts/compute_metrics.py` with task parameters:
     ```bash
     # For CSV input:
     python3 scripts/compute_metrics.py --input data.csv --input-format csv \
       --primary-start 2025-01-04 --primary-end 2025-03-01 \
       --imr-start 2025-01-04 --imr-end 2025-02-21 \
       --target 560 --lsl 560 --baseline 500 \
       --metric-col ResolvedAlerts \
       --output-json metrics.json --output-md brief.md

     # For Excel input:
     python3 scripts/compute_metrics.py --input data.xlsx --input-format excel \
       --primary-start 2025-01-04 --primary-end 2025-03-01 \
       --imr-start 2025-01-04 --imr-end 2025-02-21 \
       --target 560 --lsl 560 --baseline 500 \
       --metric-col ResolvedAlerts \
       --output-json metrics.json --output-md brief.md
     ```
   - Script handles all calculations using scipy.stats and generates JSON/Markdown.
   - **Excel support**: Requires `openpyxl`. Install with `pip install openpyxl` if not present.

3. **Customize the Markdown Brief (CRITICAL)**
   
   **The script-generated markdown is a template.** You MUST customize it before submission:
   
   - Replace all `[placeholder]` values with actual metrics from the JSON output
   - Required sections (verify exact headers match task spec):
     - Project Charter (table with Baseline, Target, Current Mean)
     - Statistical Analysis (subsections: One-Way ANOVA, I-MR Control Chart, Linear Regression, One-Sample t-Test, Process Capability)
     - A3 Summary (table with Background, Current Condition, Root Cause Analysis, Target Condition, Countermeasures)
     - Operational Impacts (3-4 specific impacts tied to statistical findings)
     - Timeline and Next Steps (DMAIC phase dates + actions with owners and due dates)
   - Use `assets/brief_template.md` as the structural baseline
   - Ensure operational impacts are context-specific (e.g., field service, manufacturing, alerts) — not generic
   - Include exact DMAIC phase start dates derived from the input `Stage` column
   - Next steps must have specific owners and future dates (typically within 2-4 weeks of Analyze phase)
   
   **Do not submit the raw script output** — the verifier checks for meaningful customization.

4. **Validate Output Schema**
   - **Read `references/output_schema.md` and compare your JSON field names against it** — this is the #1 failure mode.
   - Verify all 9 top-level keys present: `source_file`, `filters`, `record_counts`, `charter_metrics`, `anova_by_weekday`, `imr_summary`, `regression_day_index`, `ttest_vs_target`, `capability_against_lsl`.
   - Verify `filters` includes both windows with `business_days_only: true`.

5. **Verify Statistical Integrity**
   - p-values must be in [0, 1] range. Values >1 or <0 indicate implementation bugs.
   - For highly significant results (p < 1e-10), store as `1e-15` or scientific notation — never `0.0`.
   - Cross-check: large F/t statistic should have small p-value, not near 1.

## Schema Compliance Checklist (Verifier Triggers)

Before submission, verify these exact keys exist in the JSON. Mismatches here cause immediate verifier failure:
- `filters.primary_analysis_window` (NOT `primary_window` or `primary_date_range`)
- `filters.imr_analysis_window` (NOT `imr_window` or `imr_date_range`)
- `regression_day_index.n_observations` (NOT `n`)
- `ttest_vs_target.target` and `std_dev` (must be present)
- `capability_against_lsl.mean` (must be present)
- `record_counts.total_records_in_source` (NOT `total_records`)
- `charter_metrics.baseline_value` (NOT `baseline_upr` or similar)
- `business_days_only: true` in both filter windows

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known Invariants (by sub-task)

### DMAIC Analyze tollgate
- I-MR window must end BEFORE Analyze phase data starts (stability window for baseline).
- Business day count must match specification (e.g., 40 days for primary, 35 for I-MR).
- Cpk uses sample std dev (ddof=1), not population (ddof=0).
- Control limits derived from MR-bar/d2, not raw population sigma.
- **Process stability requires checking BOTH I-chart AND MR-chart for violations.** (R3 u1: agent initially only checked I-chart, missed MR-chart out-of-control points.)
- Markdown brief must NOT contain placeholder text like `[Impact 1]` or `[Action 1]`.

## Validation Checklist

Before submission, verify:
- [ ] Business day count matches specification
- [ ] I-MR window ends before Analyze phase start
- [ ] ANOVA includes all 5 weekdays (Mon-Fri)
- [ ] Control limits calculated from moving range
- [ ] **I-MR stability checked on BOTH Individuals AND MR charts** (not just one)
- [ ] Cpk uses correct specification limit (LSL vs USL)
- [ ] Regression uses sequential day index, not calendar dates
- [ ] JSON includes all 9 required top-level keys
- [ ] `business_days_only: true` in both filter windows
- [ ] **Read `references/output_schema.md` and compare field names against it**
- [ ] Markdown brief has all required section headers (exact match)
- [ ] Operational impacts are context-specific (not generic placeholders)
- [ ] Timeline includes exact DMAIC phase dates from input
- [ ] Next steps have owners and future due dates
- [ ] No placeholder text remaining in brief (`[Impact 1]`, `[Action 1]`, `[Name]`, `[Date]`)

## Anti-Patterns

- **Do not** write custom computation scripts; use the bundled `compute_metrics.py`.
- **Do not** include weekends when "business days only" specified.
- **Do not** use population std dev (`ddof=0`); use sample (`ddof=1`).
- **Do not** compute I-MR limits from overall sigma; use MR-bar/d2.
- **Do not** round p-values to `0.0` or `0.00000000`.
- **Do not** implement statistical distributions from scratch — use scipy.stats.
- **Do not** trust p-values outside [0, 1] range — indicates bug.
- **Do not** hardcode phase dates; derive from `Stage` column.
- **Do not** submit the script's generic brief without customization — verifiers check for task-specific content.
- **Do not** use generic operational impacts like `[Impact 1 - TBD]` — replace with domain-specific findings tied to statistical results.
- **Do not** add extra JSON keys (e.g., `df_between`, `df_within`, `points` array in I-MR, `response_metric` in filters). The verifier rejects unknown keys.
- **Do not** use wrong key names: `primary_date_range` instead of `primary_analysis_window`, `total_records` instead of `total_records_in_source`, `baseline_upr` instead of `baseline_value`.

## Scripts & References

- **Run**: `scripts/compute_metrics.py` — deterministic computation, requires scipy. Supports `--input-format csv` (default) or `--input-format excel`.
- **Read**: `references/output_schema.md` — required JSON structure for verifier. **Read this BEFORE writing JSON output.**
- **Read**: `references/formulas.md` — exact formulas and constants.
- **Use**: `assets/brief_template.md` — structural template for markdown brief customization.