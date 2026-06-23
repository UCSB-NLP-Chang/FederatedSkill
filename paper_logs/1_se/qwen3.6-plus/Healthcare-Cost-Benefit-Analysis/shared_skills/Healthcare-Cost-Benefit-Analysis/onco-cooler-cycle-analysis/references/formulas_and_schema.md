# Formulas & JSON Schema

## Fixed Parameters
- **Dispatches per year**: 36 (10-day cycle), 18 (20-day cycle)
- **Days covered per year**: 360 (10 x 36 = 20 x 18)
- **Decision threshold**: $10,000 USD (configurable)

## Cost & Revenue Formulas
All calculations are annualized per program.

### Annual Drug Cost
Identical for both cycles because total annual covered days remain constant.
`annual_drug_cost = (acquisition_cost_per_1000 / 1000) * units_per_day * 360 * active_sites`

### Annual Cooler Cost
Scales linearly with dispatch frequency.
`annual_cooler_cost = cooler_cost * dispatches_per_year * active_sites`

### Annual Revenue
Scales linearly with dispatch frequency.
`annual_revenue = payment_per_dispatch_per_site * dispatches_per_year * active_sites`

### Annual Margin
`annual_margin = annual_revenue - annual_drug_cost - annual_cooler_cost`

## Data Resolution Rules
1. **In-Scope Filter**: Only process programs where `review_flag` is `"review"` in the catalog. Exclude `"archive"` or others.
2. **Site Overrides**: Group `site_overrides.csv` by `program_code`. Filter rows where `approval_state == 'approved'`. Select the row with the highest `version_no`. Use its `active_sites` value. If no approved override exists, fallback to `default_active_sites` from the catalog.
3. **Payment Labels**: Map `program_label` from `contract_payment.csv` to `program_code` using the `known_labels` array in the catalog.

## Expected JSON Schema
```json
{
  "assumptions": {
    "dispatches_per_year_10_day": 36,
    "dispatches_per_year_20_day": 18,
    "days_covered_per_year": 360,
    "switch_threshold_usd": 10000,
    "site_override_rule": "highest approved version_no per program_code"
  },
  "programs": [
    {
      "program_code": "string",
      "program_name": "string",
      "active_sites": "number",
      "acquisition_cost_per_1000_units_usd": "number",
      "units_per_day": "number",
      "cooler_type": "string",
      "cooler_cost_usd": "number",
      "payment_per_dispatch_per_site_usd": "number",
      "annual_drug_cost_10_day_usd": "number",
      "annual_drug_cost_20_day_usd": "number",
      "annual_cooler_cost_10_day_usd": "number",
      "annual_cooler_cost_20_day_usd": "number",
      "annual_revenue_10_day_usd": "number",
      "annual_revenue_20_day_usd": "number",
      "annual_margin_10_day_usd": "number",
      "annual_margin_20_day_usd": "number",
      "annual_margin_difference_20_minus_10_usd": "number"
    }
  ],
  "totals": {
    "total_annual_margin_10_day_usd": "number",
    "total_annual_margin_20_day_usd": "number",
    "absolute_difference_usd": "number",
    "decision": "string"
  }
}
```
