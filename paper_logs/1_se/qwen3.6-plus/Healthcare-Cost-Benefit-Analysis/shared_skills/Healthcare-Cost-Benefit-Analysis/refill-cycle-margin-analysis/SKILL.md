---
name: refill-cycle-margin-analysis
description: Analyzes and compares 30-day vs 90-day medication refill cycles for healthcare clinics. Use when given acquisition cost, packaging cost, and reimbursement CSVs to compute annual margins, apply a financial threshold, and output a structured JSON analysis and Markdown summary.
---

# Refill Cycle Margin Analysis

## When to Use
- Task provides three CSVs: `acquisition_cost.csv`, `packaging_cost.csv`, `reimbursement.csv`.
- Goal is to compare annual financial margins between 30-day and 90-day refill cycles.
- Output must include per-therapy breakdowns, total margins, absolute difference, and a threshold-based decision.

## Workflow
1. **Verify Inputs**: Ensure all three CSVs are present and contain the expected columns.
2. **Run Computation**: Execute `scripts/compute_margin.py` with the input CSV paths and the decision threshold (default: 12000).
   ```bash
   python3 scripts/compute_margin.py --acq acquisition_cost.csv --pkg packaging_cost.csv --reim reimbursement.csv --threshold 12000
   ```
3. **Validate Outputs**: Check that `cycle_margin_analysis.json` and `cycle_margin_summary.md` are generated. Verify JSON structure matches the expected schema.
4. **Review Decision**: The script automatically determines `keep_30_day` or `switch_to_90_day` based on whether the absolute margin difference exceeds the threshold and which cycle yields a higher total margin.

## Key Formulas & Assumptions
- **Patients per therapy**: 240
- **Fills/year**: 12 (30-day), 4 (90-day)
- **Doses/fill**: 60 (30-day), 180 (90-day)
- **Annual Drug Cost**: `(price_per_1000 / 1000) * doses_per_fill * fills_per_year * 240`
- **Annual Packaging Cost**: `packaging_cost * fills_per_year * 240`
- **Annual Reimbursement**: `reimbursement_per_fill * fills_per_year`
- **Annual Margin**: `Reimbursement - Drug Cost - Packaging Cost`
- See `references/math_and_assumptions.md` for detailed derivations, edge cases, and decision logic.

## Anti-Patterns & Troubleshooting
- **Do not hardcode totals**: Always compute per-therapy first, then aggregate. Rounding errors compound if aggregated prematurely.
- **Reimbursement scaling**: Reimbursement is given per fill for 240 patients. Multiply only by `fills_per_year`, not by patients again.
- **Drug cost invariance**: Total annual drug cost is identical for both cycles (same total doses/year). Only packaging and reimbursement change.
- **Threshold logic**: Decision triggers only if `abs(margin_90 - margin_30) > threshold`. If triggered, pick the higher margin cycle. Otherwise, default to `keep_30_day`.
