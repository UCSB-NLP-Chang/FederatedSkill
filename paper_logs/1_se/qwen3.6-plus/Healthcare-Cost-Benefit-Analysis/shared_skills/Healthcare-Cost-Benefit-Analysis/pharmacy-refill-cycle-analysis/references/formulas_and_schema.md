# Formulas & JSON Schema

## Fixed Parameters
- **Patients per medication**: 300
- **Fills per year**: 4 (90-day cycle), 3 (100-day cycle)
- **Tablets per fill**: 90 (90-day cycle), 100 (100-day cycle)
- **Decision threshold**: $16,000 USD

## Cost & Revenue Formulas
All calculations are annualized per medication.

### Annual Drug Cost
Differs between cycles due to different total annual tablets.
`annual_drug_cost = (price_per_1000_tablets / 1000) * tablets_per_fill * fills_per_year * 300`

### Annual Supply Cost
Scales linearly with fill frequency.
`annual_supply_cost = vial_price * fills_per_year * 300`

### Annual Reimbursement
The input CSV provides reimbursement per fill for the full cohort (300 patients).
`annual_reimbursement = reimbursement_per_fill * fills_per_year`

### Annual Revenue
`annual_revenue = annual_reimbursement - annual_drug_cost - annual_supply_cost`

## Decision Logic
1. Sum `annual_revenue_90_day` and `annual_revenue_100_day` across all medications.
2. Calculate `absolute_difference = abs(total_100 - total_90)`.
3. If `absolute_difference > 16000`:
   - Choose the cycle with the higher total revenue.
   - Decision: `switch_to_100_day` or `keep_90_day`.
4. If `absolute_difference <= 16000`:
   - Default to `keep_90_day`.

## Expected JSON Schema
```json
{
  "assumptions": {
    "patients_per_medication": 300,
    "fills_per_year_90_day": 4,
    "fills_per_year_100_day": 3,
    "tablets_per_fill_90_day": 90,
    "tablets_per_fill_100_day": 100,
    "switch_threshold_usd": 16000
  },
  "medications": [
    {
      "medication": "string",
      "price_per_1000_tablets_usd": "number",
      "vial_size_drams": "number",
      "vial_price_usd": "number",
      "reimbursement_per_fill_300_patients_usd": "number",
      "annual_drug_cost_90_day_usd": "number",
      "annual_drug_cost_100_day_usd": "number",
      "annual_supply_cost_90_day_usd": "number",
      "annual_supply_cost_100_day_usd": "number",
      "annual_reimbursement_90_day_usd": "number",
      "annual_reimbursement_100_day_usd": "number",
      "annual_revenue_90_day_usd": "number",
      "annual_revenue_100_day_usd": "number",
      "annual_revenue_difference_100_minus_90_usd": "number"
    }
  ],
  "totals": {
    "total_annual_revenue_90_day_usd": "number",
    "total_annual_revenue_100_day_usd": "number",
    "absolute_difference_usd": "number",
    "decision": "string"
  }
}
```
