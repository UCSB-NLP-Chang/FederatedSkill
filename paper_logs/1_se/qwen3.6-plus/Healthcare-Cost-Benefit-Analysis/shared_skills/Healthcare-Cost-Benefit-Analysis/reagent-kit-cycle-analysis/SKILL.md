---
name: reagent-kit-cycle-analysis
description: Compares 24-run small-kit vs 12-run bulk-kit diagnostic assay cycles. Use when given an assay manifest JSON, carrier cost CSV, billing CSV, lab overrides CSV, and report template JSON to compute annual margins, resolve active labs and latest billing, and output structured JSON/Markdown analysis with a threshold-based decision.
---

# Reagent Kit Cycle Margin Analysis

## When to Use
- Task provides `assay_manifest.json`, `carrier_cost.csv`, `billing.csv`, `lab_overrides.csv`, and `report_template.json`.
- Goal is to compare annual financial margins between small-kit (24 runs/year) and bulk-kit (12 runs/year) cadences.
- Output must fill the provided JSON template and generate a Markdown summary with a threshold-based decision.

## Workflow
1. **Verify Inputs**: Ensure all five files are present. Check that `assay_manifest.json` contains `in_scope` flags.
2. **Run Computation**: Execute `scripts/compute_reagent_margin.py` with the input paths.
   ```bash
   python3 scripts/compute_reagent_margin.py --manifest assay_manifest.json --carrier carrier_cost.csv --billing billing.csv --overrides lab_overrides.csv --template report_template.json --threshold 7000
   ```
3. **Validate Outputs**: Check that `reagent_policy_report.json` and `reagent_policy_summary.md` are generated. Verify JSON structure matches `references/formulas_and_schema.md`.
4. **Review Decision**: The script determines `keep_small_kit` or `switch_to_bulk_kit` based on whether the absolute margin difference exceeds the threshold.

## Key Formulas & Assumptions
- **Runs/year**: 24 (small-kit), 12 (bulk-kit)
- **Annual Reagent Cost**: Identical for both cycles (same total annual tests). `(price_per_1000 / 1000) * tests_per_lab_per_run * runs_per_year * active_labs`
- **Annual Carrier Cost**: `carrier_cost * runs_per_year * active_labs`
- **Annual Revenue**: `payment_per_run_per_lab * runs_per_year * active_labs`
- **Annual Margin**: `Revenue - Reagent Cost - Carrier Cost`
- See `references/formulas_and_schema.md` for detailed derivations, override resolution, and exact JSON schema.

## Anti-Patterns & Troubleshooting
- **Lab Override Resolution**: Do not use the first row. Filter `status == 'approved'` and pick the highest `revision` per `assay_id`. Fallback to `default_active_labs` if no approved override exists.
- **Billing Resolution**: Map `assay_label` from `billing.csv` to `assay_id` using the `aliases` array in the manifest. Filter `is_active == true` and pick the latest `effective_month`.
- **In-Scope Filter**: Only process assays where `in_scope` is `true`.
- **Reagent Cost Invariance**: Total annual reagent cost is identical for both cycles. Only carrier costs and revenue scale with run frequency.
- **Threshold Logic**: Decision triggers only if `abs(margin_bulk - margin_small) > threshold`. If triggered, pick the higher margin cycle. Otherwise, default to `keep_small_kit`.
- **CSV Parsing**: Inputs may be tab or comma separated. The bundled script uses `csv.Sniffer` to handle both automatically.