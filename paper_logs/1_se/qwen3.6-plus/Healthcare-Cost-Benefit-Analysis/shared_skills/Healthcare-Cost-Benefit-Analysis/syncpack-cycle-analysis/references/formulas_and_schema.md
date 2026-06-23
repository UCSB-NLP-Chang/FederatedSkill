# Formulas & JSON Schema

## Fixed Parameters
- **Patients per medication**: 180
- **Fills per year**: `365 / cycle_days` (e.g., ~13.0357 for 28-day, ~6.5179 for 56-day)
- **Capsules per fill**: Equals cycle days (1 capsule/day assumption)
- **Cards per fill**: `cycle_days / blister_card_count`
- **Decision threshold**: $9,000 USD (configurable)

## Cost & Revenue Formulas
All calculations are annualized per medication.

### Annual Drug Cost
Identical for both cycles because total annual capsules remain constant.
`annual_drug_cost = (price_per_1000_capsules / 1000) * cycle_days * (365 / cycle_days) * patients`

### Annual Card Cost
Scales linearly with fill frequency and card usage.
`annual_card_cost = card_cost * (cycle_days / blister_card_count) * (365 / cycle_days) * patients`

### Annual Reimbursement
Scales linearly with fill frequency. The input CSV provides reimbursement per fill for the full cohort (180 patients).
`annual_reimbursement = reimbursement_per_fill * (365 / cycle_days)`

### Annual Margin
`annual_margin = annual_reimbursement - annual_drug_cost - annual_card_cost`

## Decision Logic
1. Sum `annual_margin_28_day` and `annual_margin_56_day` across all medications.
2. Calculate `absolute_difference = abs(total_56 - total_28)`.
3. If `absolute_difference > threshold`:
   - Choose the cycle with the higher total margin.
   - Decision: `convert_to_56_day` or `keep_28_day`.
4. If `absolute_difference <= threshold`:
   - Default to `keep_28_day` (no financial justification to switch).

## Expected JSON Schema
```json
{
  "assumptions": {
    "patients_per_medication": 180,
    "fills_per_year_28_day": "number",
    "fills_per_year_56_day": "number",
    "cycle_28_days": 28,
    "cycle_56_days": 56,
    "switch_threshold_usd": 9000
  },
  "medications": [
    {
      "medication": "string",
      "price_per_1000_capsules_usd": "number",
      "blister_card_count": "number",
      "card_cost_usd": "number",
      "reimbursement_per_cycle_180_patients_usd": "number",
      "annual_drug_cost_28_day_usd": "number",
      "annual_drug_cost_56_day_usd": "number",
      "annual_card_cost_28_day_usd": "number",
      "annual_card_cost_56_day_usd": "number",
      "annual_reimbursement_28_day_usd": "number",
      "annual_reimbursement_56_day_usd": "number",
      "annual_margin_28_day_usd": "number",
      "annual_margin_56_day_usd": "number",
      "annual_margin_difference_56_minus_28_usd": "number"
    }
  ],
  "totals": {
    "total_annual_margin_28_day_usd": "number",
    "total_annual_margin_56_day_usd": "number",
    "absolute_difference_usd": "number",
    "decision": "string"
  }
}
```
