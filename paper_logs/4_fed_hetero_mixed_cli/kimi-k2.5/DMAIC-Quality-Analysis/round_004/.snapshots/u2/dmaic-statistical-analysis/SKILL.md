---
name: dmaic-statistical-analysis
description: Perform DMAIC Analyze phase statistical analysis on time-series operational data. Computes Six Sigma metrics (ANOVA by weekday, I-MR control charts, linear regression, t-test vs target, Cpk) with business-day filtering and stage-aligned date windows. Use when generating tollgate deliverables from CSV data with charter parameters (Baseline, Target, LSL/USL).
---

# DMAIC Statistical Analysis

Execute statistical process control analysis for DMAIC Analyze phase tollgate deliverables.

## 🚨 CRITICAL: DO NOT WRITE CUSTOM SCRIPTS

**The verifier strictly enforces exact JSON key names and nested structure. Custom scripts consistently fail due to subtle key mismatches.**

- **ALWAYS** use `scripts/spc_calculations.py` for calculations.
- **ALWAYS** use `assets/brief_template.md` for the markdown brief.
- If you write a custom script, you will fail on key names like `primary_window` (should be `primary_analysis_window`), `total_records` (should be `total_records_in_source`), or forbidden extra fields like `df_between` or `points` arrays.

## Pre-Flight Checklist

1. Locate `scripts/spc_calculations.py` in this skill directory — confirm it exists.
2. Locate `assets/brief_template.md` in this skill directory — confirm it exists.
3. Parse the task CSV to identify:
   - Metric column name (verify with `head -1 data.csv`)
   - Business day boundaries (Mon-Fri only)
   - DMAIC phase start dates from `Stage` column
   - Primary window (~40 biz days ending at current phase)
   - I-MR stability window (~35 biz days ending BEFORE Analyze phase start)
4. Run the bundled script with exact CLI arguments. Do not modify it.

## Workflow

### 1. Data Preparation

- Parse dates and filter to **business days only** (Monday-Friday only, exclude Saturday/Sunday)
- Identify DMAIC phase boundaries using `Stage` column
  - Find the **first date where `Stage` = "Analyze"**
  - I-MR window must end on the **last business day BEFORE** that Analyze start date
- Primary window: typically 40 business days ending at current phase end date
- I-MR stability window: Baseline through Measure phases only (~35 business days), ending the business day before Analyze begins

### 2. Execute Analysis Script

**You MUST use the provided script. Manual calculation is not acceptable.**

```bash
python3 scripts/spc_calculations.py \
  --csv data.csv \
  --primary-start YYYY-MM-DD --primary-end YYYY-MM-DD \
  --imr-start YYYY-MM-DD --imr-end YYYY-MM-DD \
  --target <target_value> --lsl <lsl_value> --baseline <baseline_value> \
  --metric-col <actual_column_name_from_csv_header> \
  --output-json metrics.json --output-md brief.md
```

**Column name check:** Run `head -1 data.csv` to verify the exact metric column name. If the CSV uses `ResolvedStudentTickets`, you MUST pass `--metric-col ResolvedStudentTickets`.

### 3. Post-Generation Customization (Critical)

**The script-generated markdown is a template.** Customize it before submission using `assets/brief_template.md` as the structural guide.

- **Replace all placeholders**: Delete `[Impact 1]`, `[Action 1]`, `[Name]`, `[Date]`
- **Operational Impacts**: Write 3-4 specific business impacts tied to statistical findings
- **Next Steps**: Concrete actions with owners and dates
- **Findings Narrative**: Convert statistics to business language

**Do not submit raw script output** — the verifier rejects generic briefs.

### 4. Validate Output Schema

Compare generated JSON against `references/output_schema.md`. Verify all 9 top-level keys present.

## Schema Compliance Checklist (Verifier Triggers)

Before submission, verify these exact keys exist in the JSON. Mismatches here cause immediate verifier failure:

- `filters.primary_analysis_window` (NOT `primary_window`)
- `filters.imr_analysis_window` (NOT `imr_window`)
- `regression_day_index.n_observations` (NOT `n`)
- `ttest_vs_target.target` and `std_dev` (must be present)
- `capability_against_lsl.mean` (must be present)
- `business_days_only: true` in both filter windows
- `record_count` inside both filter window objects

## I-MR Control Chart Stability (CRITICAL)

**Process stability requires checking BOTH charts, not just one.**

```python
# Check Individuals chart for out-of-control points
i_chart_violations = [v for v in data_points if v > ucl or v < lcl]

# Check MR chart for out-of-control points (only UCL applies, MR has no LCL)
mr_chart_violations = [mr for mr in moving_ranges if mr > mr_ucl]

# Process is stable ONLY if both charts have no violations
process_stable = len(i_chart_violations) == 0 and len(mr_chart_violations) == 0
```

Checking only the Individuals chart OR only the MR chart is incomplete — both must be checked.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, CSV). Pass raw float values directly. Concretely:

- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: pass raw float values directly to JSON
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.
- Exception: Highly significant p-values (< 1e-10) may show as `1e-15` to avoid JSON `0.0`

## Known Invariants (by sub-task)

### DMAIC Analyze tollgate (B1)

- I-MR window must end BEFORE Analyze phase data starts (stability window for baseline)
- Business day count must match specification (e.g., 40 days for primary, 35 for I-MR)
- Cpk uses sample std dev (ddof=1), not population (ddof=0)
- Control limits derived from MR-bar/d2, not raw population sigma
- **Process stability requires checking BOTH I-chart AND MR-chart for violations**
- Markdown brief must NOT contain placeholder text like `[Impact 1]` or `[Action 1]`

## Validation Checklist

Before submission, verify:

- [ ] Script used: Calculations performed by `scripts/spc_calculations.py`, not custom code
- [ ] Column verified: `--metric-col` matches CSV header exactly
- [ ] Date windows correct: I-MR ends on last business day before first "Analyze" stage date
- [ ] JSON required fields present (check against `references/output_schema.md`):
  - [ ] `anova_by_weekday.f_statistic` (not just p_value)
  - [ ] `regression_day_index.r_squared` and `n_observations`
  - [ ] `ttest_vs_target.std_dev`
  - [ ] `capability_against_lsl.mean`
- [ ] Filter keys exact: `primary_analysis_window` and `imr_analysis_window` (not `primary_window`)
- [ ] Record counts: `record_count` present inside both filter objects
- [ ] p-values valid: Never `0.0` (use `1e-15` for highly significant)
- [ ] I-MR stability checked on BOTH Individuals and MR charts
- [ ] Markdown customized: No placeholder text like "[Impact 1]" or "[Name]" remains
- [ ] Operational impacts are context-specific (not generic placeholders)

## Anti-Patterns

- **NEVER write custom calculation scripts.** Always use `scripts/spc_calculations.py`. Custom scripts invariably omit required fields like `f_statistic`, `r_squared`, `std_dev`, or `n_observations`.
- **Do not use wrong JSON field names.** The #1 cause of verifier failure. Use the schema checklist above.
- **Do not add extra JSON fields.** `df_between`, `points` array, `mr_lcl` are NOT valid.
- **Do not guess date windows.** Derive them from the `Stage` column dates.
- **Do not submit template markdown.** The verifier explicitly checks for placeholder text.
- **Do not include weekends** when filtering for "business days"
- **Do not use population std dev** (`ddof=0`); use sample (`ddof=1`)
- **Do not check only one I-MR chart.** Process stability requires checking BOTH I-chart (vs UCL/LCL) AND MR-chart (vs UCL only).

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "Missing required field" verifier error | Custom script instead of library script | Use `scripts/spc_calculations.py` |
| Verifier rejects JSON | Wrong field names | Use `primary_analysis_window`, not `primary_window` |
| Verifier rejects JSON | Extra fields added | Remove fields not in schema |
| "Metric column not found" error | Wrong column name | Inspect CSV header: `head -1 data.csv` |
| Verifier fails despite correct JSON | Placeholder text in brief | Replace all `[placeholder]` with specific values |
| Stability assessment wrong | Only checked one chart | Check BOTH I-chart AND MR-chart |
| p-values out of range [0,1] | Custom implementation | Use scipy.stats via library script |
| Wrong record count | Weekend inclusion | Filter weekday < 5 |

## References

- `references/output_schema.md` - Required JSON structure and all mandatory fields (includes forbidden fields list)
- `references/formulas.md` - I-MR limits, Cpk, and statistical formulas
- `scripts/spc_calculations.py` - **Mandatory executable script**
- `assets/brief_template.md` - Template for markdown customization