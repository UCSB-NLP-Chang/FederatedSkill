---
name: pharmacy-refill-cycle-analysis
description: Compares 90-day vs 100-day medication refill cycles for pharmacies. Use when given wholesale price, vial price, and reimbursement CSVs to compute annual revenue, apply a $16,000 threshold, and output a structured JSON analysis and Markdown summary.
---

# Pharmacy Refill Cycle Revenue Analysis

## When to Use
- Task provides three CSVs: `wholesale_price.csv`, `vial_price.csv`, `reimbursement.csv`.
- Goal is to compare annual financial revenue between 90-day and 100-day refill cycles.
- Output must include per-medication breakdowns, total revenues, absolute difference, and a threshold-based decision.

## Workflow
1. **Verify Inputs**: Ensure all three CSVs are present. Check column names match expected schema.
2. **Run Computation**: Execute `scripts/compute_refill_revenue.py` with the input CSV paths.
   ```bash
   python3 scripts/compute_refill_revenue.py --wholesale wholesale_price.csv --vial vial_price.csv --reim reimbursement.csv
   ```
3. **Validate Outputs**: Check that `refill_analysis.json` and `refill_summary.md` are generated. Verify JSON structure matches the expected schema in `references/formulas_and_schema.md`.
4. **Review Decision**: The script determines `keep_90_day` or `switch_to_100_day` based on whether the absolute revenue difference exceeds $16,000 and which cycle yields higher total revenue.

## Key Formulas & Assumptions
- **Patients per medication**: 300
- **Fills/year**: 4 (90-day), 3 (100-day)
- **Tablets/fill**: 90 (90-day), 100 (100-day)
- **Annual Drug Cost**: `(price_per_1000 / 1000) * tablets_per_fill * fills_per_year * 300`
- **Annual Supply Cost**: `vial_price * fills_per_year * 300`
- **Annual Reimbursement**: `reimbursement_per_fill * fills_per_year` (CSV already accounts for 300 patients)
- **Annual Revenue**: `Reimbursement - Drug Cost - Supply Cost`
- See `references/formulas_and_schema.md` for detailed derivations and exact JSON schema.

## Anti-Patterns & Troubleshooting
- **Do not hardcode totals**: Always compute per-medication first, then aggregate.
- **Reimbursement scaling**: The reimbursement CSV provides values per fill for the full 300-patient cohort. Multiply only by `fills_per_year`, not by patients again.
- **Drug cost variance**: Unlike 30/90-day comparisons, total annual drug cost differs between 90-day and 100-day cycles because total annual tablets differ (360 vs 300 per patient).
- **Threshold logic**: Decision triggers only if `abs(revenue_100 - revenue_90) > 16000`. If triggered, pick the higher revenue cycle. Otherwise, default to `keep_90_day`.
- **CSV Parsing**: Inputs may be tab or comma separated. The bundled script uses `csv.Sniffer` to handle both automatically.
