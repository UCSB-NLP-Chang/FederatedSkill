---
name: diagpanel-cycle-analysis
description: Compares 14-day vs 28-day diagnostic panel dispatch cycles. Use when given a panel manifest JSON, shipper cost CSV, contract terms CSV, network adjustments CSV, lab capacity overrides CSV, holdouts JSON, and report template JSON to compute annual margins, resolve active labs and latest contract terms, and output structured JSON/Markdown analysis with a threshold-based decision.
---

# Diagnostic Panel Dispatch Cycle Analysis

## When to Use
- Task provides `panel_manifest.json`, `shipper_cost.csv`, `contract_terms.csv`, `network_adjustments.csv`, `lab_capacity_overrides.csv`, `holdouts.json`, and `report_template.json`.
- Goal is to compare annual financial margins between 14-day and 28-day dispatch cycles.
- Output must fill the provided JSON template and generate a Markdown summary with a threshold-based decision.

## Workflow
1. **Verify Inputs**: Ensure all seven files are present. Check that `panel_manifest.json` contains `analysis_mode` flags.
2. **Run Computation**: Execute `scripts/compute_diagpanel_margin.py` with the input paths.
   ```bash
   python3 scripts/compute_diagpanel_margin.py --manifest panel_manifest.json --shipper shipper_cost.csv --contract contract_terms.csv --adjustments network_adjustments.csv --overrides lab_capacity_overrides.csv --holdouts holdouts.json --template report_template.json --threshold 6000
   ```
3. **Validate Outputs**: Check that `diagpanel_policy_report.json` and `diagpanel_policy_summary.md` are generated. Verify JSON structure matches `references/formulas_and_schema.md`.
4. **Review Decision**: The script determines `keep_14_day` or `switch_to_28_day` based on whether the absolute margin difference exceeds the threshold.

## Key Formulas & Assumptions
- **Runs/year**: 26 (14-day), 13 (28-day)
- **Annual Reagent Cost**: Identical for both cycles (same total annual tests). `(reagent_cost_per_1000 / 1000) * tests_per_lab_per_run * runs_per_year * active_labs`
- **Annual Shipper Cost**: `shipper_cost * runs_per_year * active_labs`
- **Annual Revenue**: `(base_payment + network_adjustment) * runs_per_year * active_labs`
- **Annual Margin**: `Revenue - Reagent Cost - Shipper Cost`
- See `references/formulas_and_schema.md` for detailed derivations, override resolution, and exact JSON schema.

## Anti-Patterns & Troubleshooting
- **Holdout Filter**: Exclude panels where `holdout_state == 'exclude'` in `holdouts.json` before computing margins.
- **Override Resolution**: Do not use the first row. Filter `approval == 'approved'` and pick the highest `rev` with a non-blank `active_labs` per `panel_code`. Fallback to `default_active_labs` if no valid override exists.
- **Contract Resolution**: Map `alias_labels` from the manifest to `panel_ref` in `contract_terms.csv`. Filter `status_flag == 'current'` and pick the latest `effective_week`.
- **Network Adjustments**: Join `network_adjustments.csv` by `network_tier`. Default to `0.0` if tier is missing.
- **Reagent Cost Invariance**: Total annual reagent cost is identical for both cycles. Only shipper costs and revenue scale with run frequency.
- **Threshold Logic**: Decision triggers only if `abs(margin_28 - margin_14) > threshold`. If triggered, pick the higher margin cycle. Otherwise, default to `keep_14_day`.
- **CSV Parsing**: Inputs may be tab or comma separated. The bundled script uses `csv.Sniffer` to handle both automatically.
- **Template Preservation**: The output JSON must preserve `metadata` and `audit_notes` exactly from `report_template.json`.
