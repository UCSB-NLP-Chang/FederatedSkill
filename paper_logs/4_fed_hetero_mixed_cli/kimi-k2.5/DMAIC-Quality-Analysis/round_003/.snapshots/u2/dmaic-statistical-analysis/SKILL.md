---
name: dmaic-statistical-analysis
description: Perform DMAIC Analyze phase statistical analysis on time-series operational data. Use when generating Six Sigma tollgate deliverables requiring ANOVA, I-MR control charts, linear regression, t-tests, and process capability (Cpk) from CSV data with business-day filtering and stage-aligned windows.
---

# DMAIC Statistical Analysis

Execute statistical process control analysis for DMAIC tollgate deliverables.

## Core Principle

**Always use `scipy.stats` for statistical tests.** Custom implementations of F-distributions, t-distributions, or beta functions produce incorrect p-values (values outside [0,1]). Never implement statistical distributions from scratch.

## Prerequisites

- Input CSV with columns: `Date`, `Stage` (DMAIC phase), `Day` (weekday), `Metric`
- Charter parameters: Baseline value, Target value, Specification limit (LSL/USL)
- **Verify the metric column name** matches the CSV header (e.g., `ClosedWorkOrders`, `ResolvedAlerts`). The script defaults to `ResolvedAlerts`; override with `--metric-col` if different.
- Defined analysis windows aligned to DMAIC stages

## Workflow

### 1. Data Preparation
- Parse dates and filter to **business days only** (Monday-Friday only, exclude Saturday/Sunday)
- Identify DMAIC phase boundaries using `Stage` column
  - **Critical**: Find the first date where `Stage` = "Analyze"
  - I-MR window must end on the **last business day BEFORE** that Analyze start date
- Extract primary window: typically 40 business days ending at current phase end date
- Extract I-MR stability window: Baseline through Measure phases only (~35 business days), ending the business day before Analyze begins

### 2. Statistical Calculations

**Use `scripts/spc_calculations.py` rather than ad-hoc Python.** The script guarantees schema-compliant output.

**Script Parameters**
```bash
python3 scripts/spc_calculations.py \
  --csv data.csv \
  --primary-start YYYY-MM-DD --primary-end YYYY-MM-DD \
  --imr-start YYYY-MM-DD --imr-end YYYY-MM-DD \
  --target <target_value> --lsl <lsl_value> --baseline <baseline_value> \
  --metric-col <actual_column_name> \
  --output-json metrics.json --output-md brief.md
```

**Manual Calculations (if script cannot be used)**
- **ANOVA**: Use `scipy.stats.f_oneway(*groups)` — required output includes `f_statistic`
- **I-MR**: CL = mean, UCL/LCL = mean ± 2.667 × MR-bar (E2 constant)
- **Regression**: Use `scipy.stats.linregress(x, y)` — required: `r_squared`, `n_observations`
- **T-Test**: Use `scipy.stats.ttest_1samp(data, target)` — required: `std_dev`
- **Cpk**: Use sample standard deviation (`ddof=1`)

### 3. Output Generation

Generate two files:
1. `*_metrics.json`: Structured statistical results matching `references/output_schema.md`
2. `*_brief.md`: Executive tollgate brief

### 4. Post-Generation Customization (Critical)

**The script-generated markdown is a template.** You MUST customize it before submission. Use `assets/brief_template.md` as the structural baseline.

- **Replace all placeholders**: Delete `[Impact 1]`, `[Action 1]`, `[Name]`, `[Date]` and insert specific, contextual content
- **Operational Impacts**: Write 3-4 specific business impacts based on the statistical findings (e.g., "Wednesday backlog accumulation causes 12% SLA miss rate")
- **Next Steps**: Provide concrete actions with realistic owners and dates derived from the timeline
- **Findings Narrative**: Convert statistical results into business language (e.g., "Positive trend of +0.63 units/day indicates improvement momentum, but current mean remains 3.7% below target")

**Do not submit the raw script output** — the verifier checks for meaningful customization.

## Validation Checklist

- [ ] **Column verified**: `--metric-col` matches CSV header (not default `ResolvedAlerts` if data uses different name)
- [ ] **Date windows derived correctly**: I-MR end date is last business day before first "Analyze" stage date in CSV
- [ ] **JSON structure**: All required keys present per `references/output_schema.md`
- [ ] **JSON values**: p-values never `0.0` (use `1e-15` for highly significant), correct decimal precision
- [ ] **Filter keys**: Named exactly `primary_analysis_window` and `imr_analysis_window`
- [ ] **Markdown customized**: No placeholder text like "[Impact 1]" or "[Action 1]" remains
- [ ] **Business narrative**: Operational impacts and next steps are specific to the dataset context, not generic

## Troubleshooting

**Verifier fails despite correct JSON**
- Check markdown brief for placeholder text — this is the most common failure mode
- Ensure operational impacts reference specific numbers from the analysis (means, trends, capability indices)
- Verify next steps include owners and dates aligned with the DMAIC timeline in the data

**"Metric column not found" error**
- Inspect CSV header row — the metric column name varies (e.g., `ClosedWorkOrders`, `ResolvedAlerts`, `Throughput`)
- Override default with `--metric-col <name>`

**I-MR chart shows instability**
- Verify window ends BEFORE Analyze phase data begins
- Check that weekend dates weren't included in the count (use business days only)

**p-values out of range [0,1]**
- You implemented a distribution from scratch instead of using `scipy.stats`. Use the script or scipy functions.

## Anti-Patterns

- **Do not** submit the script's markdown template without customizing placeholders
- **Do not** guess date windows — derive them from the `Stage` column dates
- **Do not** implement custom statistical distributions — use scipy.stats
- **Do not** include weekends when filtering for "business days"
- **Do not** use pandas `.std(ddof=0)` (population); use `ddof=1` (sample)
- **Do not** round p-values to `0.0` — use scientific notation for tiny values

## Known Invariants (by sub-task)

### dmaic-analyze-phase
- I-MR stability window must NOT include Analyze phase data — end window before Analyze starts
- Record counts in filters must match actual business days in window
- **Markdown brief must NOT contain placeholder text**: `[Impact 1]`, `[Action 1]`, `[Name]`, `[Date]` — verifier explicitly rejects generic briefs (R2 u2 failure)

## References

- `references/output_schema.md` - Required JSON structure and common verifier failures
- `references/formulas.md` - I-MR limits, Cpk, and statistical test formulas
- `scripts/spc_calculations.py` - Executable script that generates schema-compliant outputs
- `assets/brief_template.md` - Structural template for markdown brief customization
