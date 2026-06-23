# Formulas & JSON Schema

## Fixed Parameters
- **Runs per year**: 26 (14-day cycle), 13 (28-day cycle)
- **Decision threshold**: $6,000 USD (configurable)

## Cost & Revenue Formulas
All calculations are annualized per panel.

### Annual Reagent Cost
Identical for both cycles because total annual tests remain constant.
`annual_reagent_cost = (reagent_cost_per_1000 / 1000) * tests_per_lab_per_run * runs_per_year * active_labs`

### Annual Shipper Cost
Scales linearly with run frequency and active labs.
`annual_shipper_cost = shipper_cost * runs_per_year * active_labs`

### Annual Revenue
Scales linearly with run frequency and active labs. Payment includes base contract rate plus network tier adjustment.
`annual_revenue = (base_payment + network_adjustment) * runs_per_year * active_labs`

### Annual Margin
`annual_margin = annual_revenue - annual_reagent_cost - annual_shipper_cost`

## Data Resolution Rules
1. **In-Scope Filter**: Only process panels where `analysis_mode` is `"review"` in the manifest.
2. **Holdout Filter**: Exclude panels where `holdout_state` is `"exclude"` in `holdouts.json`.
3. **Lab Overrides**: Group `lab_capacity_overrides.csv` by `panel_code`. Filter rows where `approval == 'approved'`. Select the row with the highest `rev` that has a non-blank `active_labs`. Use its `active_labs` value. Fallback to `default_active_labs` from the manifest if no valid override exists.
4. **Contract Resolution**: Map `alias_labels` from the manifest to `panel_ref` in `contract_terms.csv`. Filter rows where `status_flag == 'current'`. Select the row with the latest `effective_week` per panel.
5. **Network Adjustments**: Join `network_adjustments.csv` by `network_tier`. Default to `0.0` if the tier is missing from the adjustments file.

## Expected JSON Schema
The output JSON must preserve the `metadata` and `audit_notes` from `report_template.json` and populate the `analysis` object:
```json
{
  "metadata": { ... },
  "audit_notes": [ ... ],
  "analysis": {
    "assumptions": {
      "runs_per_year_14_day": 26,
      "runs_per_year_28_day": 13,
      "switch_threshold_usd": 6000,
      "override_rule": "highest numeric approved rev with non-empty active_labs, else default_active_labs",
      "holdout_rule": "exclude holdout_state=exclude",
      "adjustment_rule": "missing network_tier adjustment defaults to 0.0"
    },
    "panels": [
      {
        "panel_code": "string",
        "panel_name": "string",
        "active_labs": "number",
        "reagent_cost_per_1000_tests_usd": "number",
        "network_tier": "string",
        "network_adjustment_per_run_per_lab_usd": "number",
        "shipper_class": "string",
        "shipper_cost_usd": "number",
        "base_payment_per_run_per_lab_usd": "number",
        "total_payment_per_run_per_lab_usd": "number",
        "tests_per_lab_per_run_14_day": "number",
        "tests_per_lab_per_run_28_day": "number",
        "annual_reagent_cost_14_day_usd": "number",
        "annual_reagent_cost_28_day_usd": "number",
        "annual_shipper_cost_14_day_usd": "number",
        "annual_shipper_cost_28_day_usd": "number",
        "annual_revenue_14_day_usd": "number",
        "annual_revenue_28_day_usd": "number",
        "annual_margin_14_day_usd": "number",
        "annual_margin_28_day_usd": "number",
        "annual_margin_difference_28_minus_14_usd": "number"
      }
    ],
    "totals": {
      "total_annual_margin_14_day_usd": "number",
      "total_annual_margin_28_day_usd": "number",
      "total_annual_margin_difference_28_minus_14_usd": "number",
      "absolute_total_margin_difference_usd": "number"
    },
    "recommendation": {
      "decision": "string",
      "reasoning": "string"
    }
  }
}
```
