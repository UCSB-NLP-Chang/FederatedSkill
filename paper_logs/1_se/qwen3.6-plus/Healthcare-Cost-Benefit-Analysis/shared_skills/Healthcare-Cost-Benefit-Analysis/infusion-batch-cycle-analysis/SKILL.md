---
name: infusion-batch-cycle-analysis
description: Compares 7-day vs 14-day home infusion delivery cycles. Use when given a therapy catalog JSON, bag supply cost CSV, delivery payment CSV, and patient override CSV to compute annual margins, resolve approved patient counts, and output structured JSON/Markdown analysis.
---

# Infusion Batch Delivery Cycle Analysis

## When to Use
- Task provides `therapy_catalog.json`, `bag_supply_cost.csv`, `delivery_payment.csv`, and `patient_overrides.csv`.
- Goal is to compare annual financial margins between 7-day and 14-day delivery cycles.
- Output must include per-therapy breakdowns, total margins, absolute difference, and a threshold-based decision.

## Workflow
1. **Verify Inputs**: Ensure all four files are present. Check that `therapy_catalog.json` contains `include_in_review` flags.
2. **Run Computation**: Execute `scripts/compute_infusion_margin.py` with the input paths.
   ```bash
   python3 scripts/compute_infusion_margin.py --catalog therapy_catalog.json --bag-cost bag_supply_cost.csv --payment delivery_payment.csv --overrides patient_overrides.csv --threshold 15000
   ```
3. **Validate Outputs**: Check that `infusion_batch_analysis.json` and `infusion_batch_summary.md` are generated. Verify JSON structure matches `references/formulas_and_schema.md`.
4. **Review Decision**: The script determines `move_to_14_day` or `keep_7_day` based on whether the absolute margin difference exceeds the threshold.

## Key Formulas & Assumptions
- **Deliveries/year**: 52 (7-day), 26 (14-day)
- **Annual Drug Cost**: `(cost_per_1000_mg / 1000) * dose_mg_per_day * 364 * patients` (Identical for both cycles)
- **Annual Supply Cost**: `bag_supply_cost * deliveries_per_year * patients`
- **Annual Revenue**: `payment_per_delivery * deliveries_per_year * patients`
- **Annual Margin**: `Revenue - Drug Cost - Supply Cost`
- See `references/formulas_and_schema.md` for detailed derivations, patient override resolution, and exact JSON schema.

## Anti-Patterns & Troubleshooting
- **Patient Override Resolution**: Do not use the first row. Filter `status == 'approved'` and pick the highest `revision` per `therapy_code`.
- **Alias Matching**: Payments are keyed by therapy aliases, not codes. Map aliases from the catalog to therapy codes before joining.
- **In-Scope Filter**: Only process therapies where `include_in_review` is `true`.
- **Drug Cost Invariance**: Total annual drug cost is identical for both cycles (364 days/year). Only supply costs and revenue scale with delivery frequency.
- **Threshold Logic**: Decision triggers only if `abs(margin_14 - margin_7) > threshold`. If triggered, pick the higher margin cycle. Otherwise, default to `keep_7_day`. Verify prompt-specific rules if they differ.
- **CSV Parsing**: Inputs may be tab or comma separated. The bundled script uses `csv.Sniffer` to handle both automatically.
