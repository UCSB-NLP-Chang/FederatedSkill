---
name: patient-safety-analysis
description: Analyzes multi-process hospital safety data (e.g., wait times, medication errors, readmission rates) from Excel/CSV. Computes variability (CV), trend stability, Wilson CIs for proportions, and generates a structured JSON report and Markdown executive brief with a 12-key monitoring plan. Use when tasked with patient safety tollgate reports, multi-metric variability ranking, or hospital quality improvement briefs.
---

# Patient Safety Analysis & Reporting

## Workflow
1. **Ingest Data**: Load the multi-sheet Excel or CSV file. Identify sheets/columns for each process metric.
2. **Compute Metrics**: Run `scripts/compute_safety_metrics.py <data_path> <target_error_rate_pct>`.
   - The script auto-detects numeric columns, computes CV, regression slope, t-stat for stability, and Wilson CI for proportions.
   - Outputs a JSON object to stdout matching `references/schema_and_sections.md`.
   - **CRITICAL**: Do not write a custom Python script. Hand-rolled scripts frequently miss exact verifier keys, miscalculate Wilson CIs, or mislabel stability thresholds.
3. **Generate JSON**: Capture stdout into your metrics file. Validate immediately:
   - Ensure `variability_ranking` is sorted descending by CV.
   - Ensure `monitoring_plan` contains exactly 12 keys, including a 9-item `checklist` and 3-item `prioritized_actions`.
   - Ensure `medication_errors` includes `uses_varying_denominators`, `target_rate_pct`, and `capability`.
4. **Draft Markdown Brief**: Use the exact section titles from `references/schema_and_sections.md`. Populate with computed values.
   - The brief must contain exactly 4 top-level sections and 10 monitoring plan subsections.
   - Every number in the text must exactly match the JSON.
5. **Cross-Check Consistency**:
   - Highest CV process = highest risk. State this explicitly.
   - If |t-stat| > 2.0, mark process as `Unstable`. Otherwise `Stable`.
   - If medication error rate < target, capability = `Capable`.

## Anti-Patterns
- **Do not** use SPC/I-MR charts for this task. This is a multi-process variability and capability analysis, not a single-metric control chart.
- **Do not** guess section titles. Verifiers check exact string matches for headings.
- **Do not** omit the 9-item checklist or 3 prioritized actions in the monitoring plan.
- **Do not** calculate proportion CIs using normal approximation. Use Wilson score interval for medication errors.

## Troubleshooting
- **Verifier fails on JSON keys**: Compare against `references/schema_and_sections.md`. Missing nested keys or wrong list lengths are common.
- **Markdown inconsistencies**: Run a string match to ensure numbers in text match JSON.
- **Missing dependencies**: Script requires `pandas`, `scipy`, `openpyxl`. Install if missing.