# Formulas & JSON Schema

## Fixed Parameters
- **Runs per year**: 24 (small-kit cycle), 12 (bulk-kit cycle)
- **Decision threshold**: $7,000 USD (configurable)

## Cost & Revenue Formulas
All calculations are annualized per assay.

### Annual Reagent Cost
Identical for both cycles because total annual tests remain constant.
`annual_reagent_cost = (reagent_price_per_1000 / 1000) * tests_per_lab_per_run * runs_per_year * active_labs`

### Annual Carrier Cost
Scales linearly with run frequency and active labs.
`annual_carrier_cost = carrier_cost * runs_per_year * active_labs`

### Annual Revenue
Scales linearly with run frequency and active labs.
`annual_revenue = payment_per_run_per_lab * runs_per_year * active_labs`

### Annual Margin
`annual_margin = annual_revenue - annual_reagent_cost - annual_carrier_cost`

## Data Resolution Rules
1. **In-Scope Filter**: Only process assays where `in_scope` is `true` in the manifest.
2. **Lab Overrides**: Group `lab_overrides.csv` by `assay_id`. Filter rows where `status == 'approved'`. Select the row with the highest `revision`. Use its `active_labs` value. Fallback to `default_active_labs` from the manifest if no approved override exists.
3. **Billing Resolution**: Map `assay_label` from `billing.csv` to `assay_id` using the `aliases` array in the manifest. Filter rows where `is_active == true`. Select the row with the latest `effective_month` per assay.

## Expected JSON Schema
The output JSON must preserve the `metadata` from `report_template.json` and populate the `analysis` object:
```json
{
  "metadata": { ... },
  "analysis": {
    "assumptions": {
      "runs_per_year_small_kit": 24,
      "runs_per_year_bulk_kit": 12,
      "switch_threshold_usd": 7000,
      "lab_override_rule": "highest approved revision per assay_id",
      "billing_rule": "latest active effective_month per assay"
    },
    "assays": [
      {
        "assay_id": "string",
        "assay_name": "string",
        "active_labs": "number",
        "reagent_price_per_1000_tests_usd": "number",
        "carrier_type": "string",
        "carrier_cost_usd": "number",
        "payment_per_run_per_lab_usd": "number",
        "annual_reagent_cost_usd": "number",
        "annual_carrier_cost_small_kit_usd": "number",
        "annual_carrier_cost_bulk_kit_usd": "number",
        "annual_revenue_small_kit_usd": "number",
        "annual_revenue_bulk_kit_usd": "number",
        "annual_margin_small_kit_usd": "number",
        "annual_margin_bulk_kit_usd": "number",
        "annual_margin_difference_bulk_minus_small_usd": "number"
      }
    ],
    "totals": {
      "total_annual_margin_small_kit_usd": "number",
      "total_annual_margin_bulk_kit_usd": "number",
      "total_annual_margin_difference_bulk_minus_small_usd": "number",
      "absolute_total_margin_difference_usd": "number"
    },
    "recommendation": {
      "decision": "string",
      "reasoning": "string"
    }
  }
}
```