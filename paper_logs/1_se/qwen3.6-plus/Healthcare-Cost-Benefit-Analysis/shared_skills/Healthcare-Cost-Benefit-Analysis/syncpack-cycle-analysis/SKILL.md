---
name: syncpack-cycle-analysis
description: Compares 28-day vs 56-day blister-pack refill cycles for pharmacies. Use when given ingredient cost, card cost, and reimbursement CSVs to compute annual margins, apply a financial threshold, and output structured JSON/Markdown analysis.
---

# SyncPack Cycle Margin Analysis

## When to Use
- Task provides three CSVs: `ingredient_cost.csv`, `card_cost.csv`, `reimbursement.csv`.
- Goal is to compare annual financial margins between two refill cycles (typically 28-day vs 56-day).
- Output must include per-medication breakdowns, total margins, absolute difference, and a threshold-based decision.

## Workflow
1. **Verify Inputs**: Ensure all three CSVs are present. Check column names match expected schema.
2. **Run Computation**: Execute `scripts/compute_syncpack_margin.py` with the input CSV paths.
   ```bash
   python3 scripts/compute_syncpack_margin.py --ingredient ingredient_cost.csv --card card_cost.csv --reim reimbursement.csv --threshold 9000
   ```
3. **Validate Outputs**: Check that `syncpack_analysis.json` and `syncpack_summary.md` are generated. Verify JSON structure matches the expected schema in `references/formulas_and_schema.md`.
4. **Review Decision**: The script determines `keep_28_day` or `convert_to_56_day` based on whether the absolute margin difference exceeds the threshold.

## Key Formulas & Assumptions
- **Patients per medication**: 180
- **Fills/year**: `365 / cycle_days` (e.g., ~13.0357 for 28-day, ~6.5179 for 56-day)
- **Capsules/fill**: Equals cycle days (1 capsule/day assumption)
- **Cards/fill**: `cycle_days / blister_card_count`
- **Annual Drug Cost**: `(price_per_1000 / 1000) * capsules_per_fill * fills_per_year * patients`
- **Annual Card Cost**: `card_cost * cards_per_fill * fills_per_year * patients`
- **Annual Reimbursement**: `reimbursement_per_fill * fills_per_year` (CSV already accounts for 180 patients)
- **Annual Margin**: `Reimbursement - Drug Cost - Card Cost`
- See `references/formulas_and_schema.md` for detailed derivations and exact JSON schema.

## Anti-Patterns & Troubleshooting
- **Do not invert threshold logic**: Decision triggers *only* if `abs(margin_B - margin_A) > threshold`. If triggered, pick the higher margin cycle. If `abs(diff) <= threshold`, default to `keep_A_day` (shorter cycle).
- **Do not hardcode totals**: Always compute per-medication first, then aggregate. Rounding errors compound if aggregated prematurely.
- **Reimbursement scaling**: The reimbursement CSV provides values per fill for the full 180-patient cohort. Multiply only by `fills_per_year`, not by patients again.
- **Drug cost invariance**: Total annual drug cost is identical for both cycles (same total capsules/year). Only card/packaging costs and reimbursement change.
- **CSV Parsing**: Inputs may be tab or comma separated. The bundled script uses `csv.Sniffer` to handle both automatically.
