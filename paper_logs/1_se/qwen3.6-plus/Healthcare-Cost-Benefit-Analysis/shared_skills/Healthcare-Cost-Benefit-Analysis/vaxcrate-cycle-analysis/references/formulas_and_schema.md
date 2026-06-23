# Formulas & JSON Schema

## Fixed Parameters
- **Dispatches per year**: 60 (6-day cycle), 30 (12-day cycle)
- **Days covered per year**: 360 (6 x 60 = 12 x 30)
- **Decision threshold**: $11,000 USD (configurable)

## Cost & Revenue Formulas
All calculations are annualized per campaign.

### Annual Drug Cost
Identical for both cycles because total annual covered days remain constant.
`annual_drug_cost = (drug_cost_per_1000_doses / 1000) * doses_per_day * 360 * active_clinics`

### Annual Crate Cost
Scales linearly with dispatch frequency.
`annual_crate_cost = crate_cost * dispatches_per_year * active_clinics`

### Annual Revenue
Scales linearly with dispatch frequency.
`annual_revenue = payment_per_dispatch_per_clinic * dispatches_per_year * active_clinics`

### Annual Margin
`annual_margin = annual_revenue - annual_drug_cost - annual_crate_cost`

## Data Resolution Rules
1. **In-Scope Filter**: Only process campaigns where `analysis_flag` is `"review"` in the manifest. Exclude `"archive"` or others.
2. **Suspension Filter**: Exclude campaigns where `suspension_status` is `"hold"` in `suspensions.csv`.
3. **Location Overrides**: Group `location_overrides.csv` by `campaign_id`. Filter rows where `state == 'approved'`. Select the row with the highest `revision`. Use its `active_clinics` value. If no approved override exists, fallback to `default_active_clinics` from the manifest.
4. **Billing Resolution**: Map `campaign_label` from `billing.csv` to `campaign_id` using the `alias_labels` array in the manifest. Filter rows where `status == 'active'`. Select the row with the latest `cycle_tag` per campaign.

## Expected JSON Schema
```json
{
  "assumptions": {
    "dispatches_per_year_6_day": 60,
    "dispatches_per_year_12_day": 30,
    "days_per_dispatch_6_day": 6,
    "days_per_dispatch_12_day": 12,
    "switch_threshold_usd": 11000,
    "override_rule": "highest numeric approved revision per campaign_id",
    "suspension_rule": "exclude campaigns with suspension_status == 'hold'"
  },
  "campaigns": [
    {
      "campaign_id": "string",
      "campaign_name": "string",
      "active_clinics": "number",
      "drug_cost_per_1000_doses_usd": "number",
      "doses_per_day": "number",
      "crate_tier": "string",
      "crate_cost_usd": "number",
      "payment_per_dispatch_per_clinic_usd": "number",
      "annual_drug_cost_6_day_usd": "number",
      "annual_drug_cost_12_day_usd": "number",
      "annual_crate_cost_6_day_usd": "number",
      "annual_crate_cost_12_day_usd": "number",
      "annual_revenue_6_day_usd": "number",
      "annual_revenue_12_day_usd": "number",
      "annual_margin_6_day_usd": "number",
      "annual_margin_12_day_usd": "number",
      "annual_margin_difference_12_minus_6_usd": "number"
    }
  ],
  "totals": {
    "total_annual_margin_6_day_usd": "number",
    "total_annual_margin_12_day_usd": "number",
    "absolute_difference_usd": "number",
    "decision": "string"
  }
}
```
