---
name: logistics-reliability-analysis
description: Analyzes multi-process logistics/supply chain data (e.g., delivery times, damage rates, order accuracy) from Excel/CSV. Computes variability (CV), trend stability, Wilson CIs for proportions, and generates a structured JSON report and Markdown executive brief with a variance diagnostic and 30/60/90-day action plan. Use when tasked with logistics reliability tollgate reports, multi-metric variability ranking, or supply chain quality improvement briefs.
---

# Logistics Reliability Analysis & Reporting

## Workflow
1. **Ingest Data**: Load the multi-sheet Excel or CSV file. Identify sheets for each process metric.
2. **Compute Metrics**: Run `scripts/compute_logistics_metrics.py <data_path> <target_error_rate_pct>`.
   - The script auto-detects numeric columns, computes CV, regression slope, t-stat for stability, and Wilson CI for proportions.
   - Outputs a JSON object to stdout matching `references/output_schema.md`.
   - **CRITICAL**: Do not write a custom Python script. Hand-rolled scripts frequently miss exact verifier keys, miscalculate Wilson CIs, or mislabel stability thresholds.
3. **Generate JSON**: Capture stdout into your metrics file. Validate immediately:
   - Ensure `variability_ranking` is sorted descending by CV.
   - Ensure `action_plan` contains `prioritized_actions`, `checklist` (exactly 8 items), `milestones_30_60_90_days`, and `codename`.
   - Ensure `variance_diagnostic` includes `process_analyzed`, `amplification_detected`, `severity`, `pattern_type`, `origin_layer`, `recommended_intervention`.
4. **Draft Markdown Brief**: Use the exact section titles from `references/output_schema.md`. Populate with computed values.
   - The brief must contain exactly 6 top-level sections.
   - Every number in the text must exactly match the JSON.
   - **CRITICAL**: The `highest_risk_statement` from JSON must appear verbatim in the Markdown (no bolding or extra punctuation around the process name).
5. **Cross-Check Consistency**:
   - Highest CV process = highest risk. State this explicitly.
   - If |t-stat| > 2.0, mark process as `Unstable`. Otherwise `Stable`.
   - If proportion rate < target, capability = `Capable`. Do not claim a rate "exceeds target" if it is numerically below it.

## Anti-Patterns
- **Do not** use SPC/I-MR charts for this task. This is a multi-process variability and capability analysis.
- **Do not** guess section titles. Verifiers check exact string matches for headings.
- **Do not** omit the 8-item checklist or 30/60/90-day milestones in the action plan.
- **Do not** calculate proportion CIs using normal approximation. Use Wilson score interval.
- **Do not** wrap the highest-risk process name in Markdown formatting (e.g., `**Order Accuracy**`) when stating the `highest_risk_statement`. Verifiers require exact plain-text matches.

## Troubleshooting
- **Verifier fails on JSON keys**: Compare against `references/output_schema.md`. Missing nested keys or wrong list lengths are common.
- **Markdown inconsistencies**: Run a string match to ensure numbers in text match JSON.
- **Missing dependencies**: Script requires `pandas`, `scipy`, `openpyxl`. Install if missing.