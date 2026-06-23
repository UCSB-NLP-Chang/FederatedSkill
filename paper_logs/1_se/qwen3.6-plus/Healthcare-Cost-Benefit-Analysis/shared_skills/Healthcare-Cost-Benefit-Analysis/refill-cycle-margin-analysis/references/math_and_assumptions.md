# Math & Assumptions

## Fixed Parameters
- **Patients per therapy**: 240
- **Fills per year**: 12 (30-day cycle), 4 (90-day cycle)
- **Doses per fill**: 60 (30-day cycle), 180 (90-day cycle)
- **Decision threshold**: $12,000 USD (configurable)

## Cost & Revenue Formulas
All calculations are annualized per therapy.

### Annual Drug Cost
Identical for both cycles because total annual doses remain constant.
`annual_drug_cost = (price_per_1000_doses / 1000) * doses_per_fill * fills_per_year * patients`

### Annual Packaging Cost
Scales linearly with fill frequency.
`annual_packaging_cost = packaging_cost_per_canister * fills_per_year * patients`

### Annual Reimbursement
Scales linearly with fill frequency. The input CSV provides reimbursement per fill for the full cohort (240 patients).
`annual_reimbursement = reimbursement_per_fill * fills_per_year`

### Annual Margin
`annual_margin = annual_reimbursement - annual_drug_cost - annual_packaging_cost`

## Decision Logic
1. Sum `annual_margin_30_day` and `annual_margin_90_day` across all therapies.
2. Calculate `absolute_difference = abs(total_90 - total_30)`.
3. If `absolute_difference > threshold`:
   - Choose the cycle with the higher total margin.
   - Decision: `switch_to_90_day` or `keep_30_day`.
4. If `absolute_difference <= threshold`:
   - Default to `keep_30_day` (no financial justification to switch).
