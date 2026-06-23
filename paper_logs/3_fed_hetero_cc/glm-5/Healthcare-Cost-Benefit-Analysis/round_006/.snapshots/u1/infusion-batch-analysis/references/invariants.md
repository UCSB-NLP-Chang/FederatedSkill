# Known Invariants by Sub-Task

## harbor_infusionbatch_7v14 (Variant A: 7-day vs 14-day infusion batching)
- Decision strings: `keep_7_day` or `move_to_14_day`
- Margin difference field: `annual_margin_difference_14_minus_7_usd`
- Deliveries per year: 7-day=`365.0/7=52.142857...`, 14-day=`365.0/14=26.071428...`
- Treatment days per year: 365 (drug costs are equal between models)
- Patient override rule: highest approved revision per therapy_code
- Entity matching: therapy_label in delivery_payment.csv matches aliases[] or therapy_name in catalog (case-insensitive)
- In-scope filter: `include_in_review: true` in therapy catalog
- Revenue field naming: `annual_revenue` (not `annual_reimbursement`)

## onco_cooler_dispatch_10v20 (Variant B: 10-day vs 20-day cooler dispatch)
- Decision strings: `keep_10_day` or `switch_to_20_day`
- Margin difference field: `annual_margin_difference_20_minus_10_usd`
- Dispatches per year: 10-day=`days_per_year/10`, 20-day=`days_per_year/20`
- **Days per year**: Commonly 360 (NOT 365) — verify task parameter `days_per_year`
- Drug cost formula: `(price_per_1000 / 1000) × units_per_day × days_per_year × active_sites`
- **Cooler cost formula**: `cooler_cost × dispatches_per_year` — NOT multiplied by sites
- Annual revenue formula: `payment_per_dispatch_per_site × dispatches_per_year × active_sites`
- Site override rule: highest approved version_no per program_code
- **Default fallback**: If no approved override exists, use `default_active_sites` from catalog
- Entity matching: program_label in contract_payment.csv matches known_labels[] or program_name (case-insensitive)
- In-scope filter: `review_flag == "review"` (string comparison, exact match)
- Override columns: `program_code`, `version_no`, `approval_state`, `active_sites`
- Payment columns: `program_label`, `payment_per_dispatch_per_site_usd`
- Cooler cost columns: `cooler_type`, `cooler_cost_usd`
- Output files: `cooler_dispatch_analysis.json`, `cooler_dispatch_summary.md`

## Common Errors by Variant

### Variant A (Infusion) Common Errors
- Integer deliveries: Using `52` instead of `365.0/7`
- Missing alias normalization: Case-sensitive matching fails
- Wrong patient count: Using highest revision overall instead of highest approved

### Variant B (Cooler Dispatch) Common Errors
- **Cooler cost × sites**: Most common error — cooler cost is per-dispatch, NOT per-site
- Days/year assumption: Using 365 when task specifies 360
- Missing default fallback: Forgetting to use default_active_sites when no approved override
- Wrong filter flag: Using `include_in_review` instead of `review_flag: "review"`
- Case-sensitive label matching: Payment labels need case-insensitive matching