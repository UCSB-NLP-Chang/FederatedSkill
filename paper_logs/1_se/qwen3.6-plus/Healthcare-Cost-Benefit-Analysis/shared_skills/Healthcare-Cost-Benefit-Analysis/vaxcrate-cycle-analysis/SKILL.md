---
name: vaxcrate-cycle-analysis
description: Compares 6-day vs 12-day vaccination crate dispatch cycles. Use when given a campaign manifest JSON, crate cost CSV, billing CSV, location overrides CSV, and suspensions CSV to compute annual margins, resolve active clinics, filter held campaigns, and output structured JSON/Markdown analysis with a threshold-based decision.
---

# Vaccination Crate Dispatch Cycle Analysis

## When to Use
- Task provides `campaign_manifest.json`, `crate_cost.csv`, `billing.csv`, `location_overrides.csv`, and `suspensions.csv`.
- Goal is to compare annual financial margins between 6-day and 12-day dispatch cycles.
- Output must include per-campaign breakdowns, total margins, absolute difference, and a threshold-based decision.

## Workflow
1. **Verify Inputs**: Ensure all five files are present. Check that `campaign_manifest.json` contains `analysis_flag` fields.
2. **Run Computation**: Execute `scripts/compute_vaxcrate_margin.py` with the input paths.
   ```bash
   python3 scripts/compute_vaxcrate_margin.py --manifest campaign_manifest.json --crate crate_cost.csv --billing billing.csv --overrides location_overrides.csv --suspensions suspensions.csv --threshold 11000
   ```
3. **Validate Outputs**: Check that `vaxcrate_analysis.json` and `vaxcrate_summary.md` are generated. Verify JSON structure matches `references/formulas_and_schema.md`.
4. **Review Decision**: The script determines `keep_6_day` or `switch_to_12_day` based on whether the absolute margin difference exceeds the threshold.

## Key Formulas & Assumptions
- **Dispatches/year**: 60 (6-day), 30 (12-day)
- **Days covered/year**: 360 (Identical for both cycles)
- **Annual Drug Cost**: `(drug_cost_per_1000 / 1000) * doses_per_day * 360 * active_clinics`
- **Annual Crate Cost**: `crate_cost * dispatches_per_year * active_clinics`
- **Annual Revenue**: `payment_per_dispatch * dispatches_per_year * active_clinics`
- **Annual Margin**: `Revenue - Drug Cost - Crate Cost`
- See `references/formulas_and_schema.md` for detailed derivations, override resolution, and exact JSON schema.

## Anti-Patterns & Troubleshooting
- **Suspension Filter**: Exclude campaigns where `suspension_status == 'hold'` before computing margins.
- **Override Resolution**: Do not use the first row. Filter `state == 'approved'` and pick the highest `revision` per `campaign_id`. Fallback to `default_active_clinics` if no approved override exists. Handle empty revision strings as 0.
- **Alias Matching**: Payments are keyed by campaign labels, not IDs. Map `alias_labels` from the manifest to `campaign_label` in the billing CSV before joining.
- **Billing Resolution**: Filter `status == 'active'`. If multiple active rows exist, pick the latest `cycle_tag`.
- **In-Scope Filter**: Only process campaigns where `analysis_flag` is `"review"`. Exclude `"archive"` or other flags.
- **Drug Cost Invariance**: Total annual drug cost is identical for both cycles (360 days/year). Only crate costs and revenue scale with dispatch frequency.
- **Threshold Logic**: Decision triggers only if `abs(margin_12 - margin_6) > threshold`. If triggered, pick the higher margin cycle. Otherwise, default to `keep_6_day`.
- **CSV Parsing**: Inputs may be tab or comma separated. The bundled script uses `csv.Sniffer` to handle both automatically.