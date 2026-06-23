# Formulas & JSON Schema

## Fixed Parameters
- **Patients per medication**: 150
- **Fills per year**: 8 (45-day cycle), 4 (90-day cycle)
- **Doses per fill**: Equals cycle days (45 or 90)
- **Decision threshold**: $8,500 USD (configurable)

## Cost & Revenue Formulas
All calculations are annualized per medication.

### Annual Drug Cost
Identical for both cycles because total annual doses remain constant.
`annual_drug_cost = (price_per_1000_doses / 1000) * doses_per_fill * fills_per_year * patients`

### Annual Mailer Cost
Scales linearly with fill frequency and patient cohort.
`annual_mailer_cost = mailer_cost_per_fill * fills_per_year * patients`

### Annual Payment
Scales linearly with fill frequency. The input CSVs provide base payment and service fee per fill for the full cohort (150 patients).
`annual_payment = (base_payment_per_fill + service_fee_per_fill) * fills_per_year`

### Annual Margin
`annual_margin = annual_payment - annual_drug_cost - annual_mailer_cost`

## Decision Logic
1. Sum `annual_margin_45_day` and `annual_margin_90_day` across all medications.
2. Calculate `absolute_difference = abs(total_90 - total_45)`.
3. If `absolute_difference > threshold`:
   - Choose the cycle with the higher total margin.
   - Decision: `switch_to_90_day` or `keep_45_day`.
4. If `absolute_difference <= threshold`:
   - Default to `keep_45_day` (no financial justification to switch).

## Expected JSON Schema
```json
{
  "assumptions": {
    "patients_per_medication": 150,
    "fills_per_year_45_day": 8,
    "fills_per_year_90_day": 4,
    "cycle_45_days": 45,
    "cycle_90_days": 90,
    "switch_threshold_usd": 8500
  },
  "medications": [
    {
      "medication": "string",
      "price_per_1000_doses_usd": "number",
      "mailer_format": "string",
      "mailer_cost_usd": "number",
      "base_payment_per_fill_usd": "number",
      "service_fee_per_fill_usd": "number",
      "annual_drug_cost_45_day_usd": "number",
      "annual_drug_cost_90_day_usd": "number",
      "annual_mailer_cost_45_day_usd": "number",
      "annual_mailer_cost_90_day_usd": "number",
      "annual_payment_45_day_usd": "number",
      "annual_payment_90_day_usd": "number",
      "annual_margin_45_day_usd": "number",
      "annual_margin_90_day_usd": "number",
      "annual_margin_difference_90_minus_45_usd": "number"
    }
  ],
  "totals": {
    "total_annual_margin_45_day_usd": "number",
    "total_annual_margin_90_day_usd": "number",
    "absolute_difference_usd": "number",
    "decision": "string"
  }
}
```
