---
name: harbor-diagpanel-analysis
description: Analyzes diagnostic panel replenishment economics comparing 14-day versus 28-day cadences using panel manifest JSON, shipper cost CSV, contract payment CSV with ISO-week versioning, network adjustment CSV, lab overrides CSV with rev/approval states, holdouts JSON, and report template JSON. Use when tasked with computing annual margins, shipper savings, and making a cadence conversion decision based on a financial threshold.
---

# Harbor Diagnostic Panel Analysis

## Overview
Compute annual financial margins for 14-day (26 runs/year) versus 28-day (13 runs/year) diagnostic panel replenishment cycles across active labs per panel. Output a detailed JSON breakdown preserving template metadata and a concise Markdown summary.

## Execution
1. Place `panel_manifest.json`, `shipper_cost.csv`, `contract_payment.csv`, `network_adjustment.csv`, `lab_overrides.csv`, `holdouts.json`, and `report_template.json` in the working directory.
2. Run `python3 scripts/compute_diagpanel.py [base_dir] [threshold]` (defaults to `/root` and `$6000`).
3. Verify outputs match the schema and line-count constraints below.

## Key Formulas & Constants
- **14-day cycle**: 26 runs/year, 14 days/run (364 days/year baseline)
- **28-day cycle**: 13 runs/year, 28 days/run
- **Annual Reagent Cost**: `(tests_per_lab_per_run * runs_per_year * active_labs / 1000) * reagent_cost_per_1000` (identical total annual tests for both cycles)
- **Annual Shipper Cost**: `shipper_cost_usd * runs_per_year * active_labs`
- **Total Payment per Run**: `base_payment_per_run_per_lab_usd + network_adjustment_per_run_per_lab_usd`
- **Annual Revenue**: `total_payment_per_run * runs_per_year * active_labs`
- **Annual Margin**: `revenue - reagent_cost - shipper_cost`
- **Decision Rule**: If `abs(margin_28 - margin_14) < threshold`, recommend `adopt_28_day`, else `keep_14_day`.

## Data Resolution Rules
- **In-Scope Panels**: Only include panels where `analysis_mode: "review"` in manifest (exclude `"archive"`).
- **Holdout Exclusion**: Exclude any `panel_code` where `holdouts.json` contains `holdout_state: "exclude"`.
- **Lab Overrides**: For each `panel_code`, select the row with `approval: "approved"` and the highest numeric `rev` where `active_labs` is non-empty. Use its `active_labs` count. If no valid approved version exists, fall back to `default_active_labs` from the manifest.
- **Contract Resolution**: `contract_payment.csv` uses `panel_ref`. Match it to `panel_name` or any value in `alias_labels` from the manifest. For each panel, select the row with `status_flag: "current"` and the latest `effective_week` (lexicographic ISO-week comparison, e.g., "2026-W22" > "2026-W10"). Use its `base_payment_per_run_per_lab_usd`.
- **Network Adjustments**: Map `network_tier` from the manifest to `network_adjustment_per_run_per_lab_usd` in `network_adjustment.csv`. Default to `0.0` if tier not found.
- **Shipper Costs**: Map `shipper_class` from the manifest to `shipper_cost_usd` in `shipper_cost.csv`.

## Output Requirements
- **JSON (`diagpanel_policy_report.json`)**: Must preserve `metadata` and `audit_notes` exactly from `report_template.json`. Include `analysis.assumptions`, `analysis.panels` array (sorted by panel_code), `analysis.totals`, and `analysis.recommendation`. All currency values rounded to 2 decimals.
- **Markdown (`diagpanel_policy_summary.md`)**: Exactly 4-8 non-empty lines. Must state total margins for both cycles, absolute difference, threshold comparison, and final decision.

## Anti-Patterns
- Do not manually calculate values; use the provided script to avoid floating-point, date-parsing, or lexicographic sorting errors.
- Do not assume annual reagent costs differ between cycles; total annual tests are identical (balanced by tests_per_lab_per_run differences).
- Ensure contract resolution filters for `status_flag: "current"` before selecting the latest `effective_week`.
- Ensure `lab_overrides.csv` correctly filters for `approval: "approved"` and highest numeric `rev`, and treats empty `active_labs` as invalid (skip that row).
- Use `python3` explicitly; do not rely on `python` being available.
- Do not exceed 8 non-empty lines in the Markdown summary; verifier will reject longer summaries.

## Troubleshooting
- If the script fails due to missing contract data, verify `panel_ref` matches `panel_name` or `alias_labels` exactly, and that `status_flag` is "current".
- If totals mismatch, verify that `lab_overrides.csv` contains an approved revision with non-empty `active_labs` for every in-scope panel, or that defaults are correctly applied.
- If output validation fails for line count, ensure the Markdown summary contains no more than 8 non-empty lines (use `grep -c .` to count).
- If ISO-week sorting produces wrong results, verify weeks use zero-padding (e.g., "W09" not "W9") for lexicographic comparison.
