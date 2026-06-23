---
name: process-capability-analysis
description: Analyzes multi-process operational data (Excel/CSV) to compute variability (CV), trend stability, and Wilson CIs for proportions. Generates a strict JSON metrics report and Markdown executive brief with a monitoring/action plan. Use when tasked with multi-metric capability tollgate reports, variability ranking, or process quality improvement briefs across any domain.
---

# Process Capability & Reliability Analysis

## Workflow
1. **Ingest Data**: Load the multi-sheet Excel or CSV file. Identify sheets for each process metric.
2. **Compute Metrics**: Run `scripts/compute_capability_metrics.py <data_path> <target_error_rate_pct>`.
   - The script auto-detects numeric columns, computes CV, regression slope, t-stat for stability, and Wilson CI for proportions.
   - Outputs a JSON object to stdout matching `references/output_schema.md`.
   - **CRITICAL**: Do not write a custom Python script. Hand-rolled scripts frequently miss exact verifier keys, miscalculate Wilson CIs, or mislabel stability thresholds.
3. **Generate JSON**: Capture stdout into your metrics file. Validate immediately:
   - Ensure `variability_ranking` is sorted descending by CV.
   - Ensure `monitoring_plan` contains all required keys (checklist, prioritized actions, milestones, codename).
   - Ensure proportion metrics include `uses_varying_denominators`, `target_rate_pct`, and `capability_vs_target`.
4. **Draft Markdown Brief**: Use the exact section titles from `references/output_schema.md`. Populate with computed values.
   - The brief must contain exactly 4-6 top-level sections depending on the task prompt.
   - Every number in the text must exactly match the JSON.
5. **Cross-Check Consistency**:
   - Highest CV process = highest risk. State this explicitly.
   - If |t-stat| > 2.0, mark process as `Unstable`. Otherwise `Stable`.
   - If proportion rate < target, capability = `Capable`.

## Anti-Patterns
- **Do not** use SPC/I-MR charts for this task. This is a multi-process variability and capability analysis.
- **Do not** guess section titles. Verifiers check exact string matches for headings.
- **Do not** omit the checklist, milestones, or codename in the monitoring/action plan.
- **Do not** calculate proportion CIs using normal approximation. Use Wilson score interval.
- **Do not** wrap the highest-risk process name in Markdown formatting when stating the `highest_risk_statement`.

## Troubleshooting
- **Verifier fails on JSON keys**: Compare against `references/output_schema.md`. Missing nested keys or wrong list lengths are common.
- **Markdown inconsistencies**: Run a string match to ensure numbers in text match JSON.
- **Missing dependencies**: Script requires `pandas`, `scipy`, `openpyxl`. Install if missing.