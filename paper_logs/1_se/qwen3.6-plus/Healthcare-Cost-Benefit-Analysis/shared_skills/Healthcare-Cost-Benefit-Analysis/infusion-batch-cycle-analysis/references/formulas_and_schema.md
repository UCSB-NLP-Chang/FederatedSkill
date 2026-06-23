# Formulas & JSON Schema

## Fixed Parameters
- **Deliveries per year**: 52 (7-day cycle), 26 (14-day cycle)
- **Days per year for dosing**: 364 (7 x 52 = 14 x 26)
- **Decision threshold**: $15,000 USD (configurable)

## Cost & Revenue Formulas
All calculations are annualized per therapy.

### Annual Drug Cost
Identical for both cycles because total annual dosing days remain constant.
`annual_drug_cost = (drug_cost_per_1000_mg / 1000) * dose_mg_per_day * 364 * active_patients`

### Annual Supply Cost
Scales linearly with delivery frequency.
`annual_supply_cost = bag_supply_cost * deliveries_per_year * active_patients`

### Annual Revenue
Scales linearly with delivery frequency.
`annual_revenue = payment_per_delivery_per_patient * deliveries_per_year * active_patients`

### Annual Margin
`annual_margin = annual_revenue - annual_drug_cost - annual_supply_cost`

## Data Resolution Rules
1. **In-Scope Filter**: Only process therapies where `include_in_review` is `true` in the catalog.
2. **Patient Overrides**: Group `patient_overrides.csv` by `therapy_code`. Filter rows where `status == 'approved'`. Select the row with the highest `revision` number. Use its `active_patients` value.
3. **Payment Aliases**: Map `therapy_label` from `delivery_payment.csv` to `therapy_code` using the `aliases` array in the catalog.

## Expected JSON Schema
```json
{
  "assumptions": {
    "deliveries_per_year_7_day": 52,
    "deliveries_per_year_14_day": 26,
    "days_per_delivery_7_day": 7,
    "days_per_delivery_14_day": 14,
    "switch_threshold_usd": 15000,
    "patient_override_rule": "highest approved revision per therapy_code"
  },
  "therapies": [
    {
      "therapy_code": "string",
      "therapy_name": "string",
      "active_patients": "number",
      "drug_cost_per_1000_mg_usd": "number",
      "dose_mg_per_day": "number",
      "bag_size_ml": "number",
      "bag_supply_cost_usd": "number",
      "payment_per_delivery_per_patient_usd": "number",
      "annual_drug_cost_7_day_usd": "number",
      "annual_drug_cost_14_day_usd": "number",
      "annual_supply_cost_7_day_usd": "number",
      "annual_supply_cost_14_day_usd": "number",
      "annual_revenue_7_day_usd": "number",
      "annual_revenue_14_day_usd": "number",
      "annual_margin_7_day_usd": "number",
      "annual_margin_14_day_usd": "number",
      "annual_margin_difference_14_minus_7_usd": "number"
    }
  ],
  "totals": {
    "total_annual_margin_7_day_usd": "number",
    "total_annual_margin_14_day_usd": "number",
    "absolute_difference_usd": "number",
    "decision": "string"
  }
}
```
