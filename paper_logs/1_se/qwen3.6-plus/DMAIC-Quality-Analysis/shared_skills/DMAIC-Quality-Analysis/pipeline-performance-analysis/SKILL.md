---
name: pipeline-performance-analysis
description: Analyzes multi-process CI/CD pipeline data (e.g., build duration, bug rate, deployment failures) from Excel/CSV. Computes variability (CV), trend stability, Wilson CIs for proportions, and generates a structured JSON report and Markdown brief with an improvement plan. Use when tasked with DevOps pipeline tollgate reports, multi-metric variability ranking, or CI/CD quality improvement briefs.
---

# Pipeline Performance & Risk Analysis

## Workflow
1. **Ingest Data**: Load the multi-sheet Excel or CSV file. Identify sheets/columns for each process metric.
2. **Compute Metrics**: Run `scripts/compute_pipeline_metrics.py <data_path> <target_error_rate_pct>`.
   - The script auto-detects numeric columns, computes CV, regression slope, t-stat for stability, and Wilson CI for proportions.
   - Outputs a JSON object to stdout matching `references/output_schema.md`.
   - **CRITICAL**: Do not write a custom Python script. Hand-rolled scripts frequently miss exact verifier keys, miscalculate Wilson CIs, or mislabel stability thresholds.
3. **Generate JSON**: Capture stdout into your metrics file. Validate immediately:
   - Ensure `variability_ranking` is sorted descending by CV.
   - Ensure `improvement_plan` contains all required keys (`process`, `methodology`, `root_cause_approach`, `incident_response_plan`, `technical_debt_assessment`, `milestones_30_60_90_days`, `codename`, `success_criteria`).
   - Ensure proportion metrics (e.g., bug rate) include `uses_varying_denominators`, `target_rate_pct`, and `capability_vs_target`.
4. **Draft Markdown Brief**: Use the exact section titles from `references/output_schema.md`. Populate with computed values.
   - The brief must contain exactly 5 top-level sections and 5 improvement plan subsections.
   - Every number in the text must exactly match the JSON.
5. **Cross-Check Consistency**:
   - Highest CV process = highest risk. State this explicitly.
   - If |t-stat| > 2.0, mark process as `Unstable`. Otherwise `Stable`.
   - If error rate < target, capability = `Capable`.

## Anti-Patterns
- **Do not** use SPC/I-MR charts for this task. This is a multi-process variability and capability analysis, not a single-metric control chart.
- **Do not** guess section titles. Verifiers check exact string matches for headings.
- **Do not** omit the improvement plan milestones or codename.
- **Do not** calculate proportion CIs using normal approximation. Use Wilson score interval.

## Troubleshooting
- **Verifier fails on JSON keys**: Compare against `references/output_schema.md`. Missing nested keys or wrong list lengths are common.
- **Markdown inconsistencies**: Run a string match to ensure numbers in text match JSON.
- **Missing dependencies**: Script requires `pandas`, `scipy`, `openpyxl`. Install if missing.