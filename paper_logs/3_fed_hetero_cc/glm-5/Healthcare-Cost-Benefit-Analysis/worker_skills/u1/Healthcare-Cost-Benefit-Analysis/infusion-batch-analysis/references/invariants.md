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

## harbor_vaxcrate_6v12 (Variant C: 6-day vs 12-day vaccination crate dispatch)
- Decision strings: `keep_6_day` or `switch_to_12_day`
- Margin difference field: `annual_margin_difference_12_minus_6_usd`
- Dispatches per year: 6-day=`360.0/6=60.0`, 12-day=`360.0/12=30.0`
- **Days per year**: 360 (NOT 365)
- Drug cost formula: `doses_per_day × 360 × clinics × (price_per_1000 / 1000)`
- **Crate cost formula**: `crate_cost × dispatches_per_year` — NOT multiplied by clinics
- Annual revenue formula: `payment_per_dispatch_per_clinic × dispatches_per_year × clinics`
- Clinic override rule: highest numeric approved revision with non-empty active_clinics per campaign_id
- **Default fallback**: If no approved override with valid clinics exists, use `default_active_clinics` from manifest
- **Suspension filter**: Exclude campaigns where `suspension_status == "hold"` (check suspensions CSV)
- **Analysis filter**: Exclude campaigns where `analysis_flag == "archive"`
- Entity matching: campaign_label in billing.csv matches alias_labels[] or campaign_name (case-insensitive)
- Billing selection: latest `cycle_tag` among `status == "active"` per campaign — do NOT sum multiple records
- Override columns: `campaign_id`, `revision`, `state`, `active_clinics`
- Payment columns: `campaign_label`, `status`, `cycle_tag`, `payment_per_dispatch_per_clinic_usd`
- Crate cost columns: `crate_tier`, `crate_cost_usd`
- Output files: `vaxcrate_analysis.json`, `vaxcrate_summary.md`

### Variant C (Vaxcrate Dispatch) Common Errors
- **Crate cost × clinics**: Most common error — crate cost is per-dispatch, NOT per-clinic
- Days/year assumption: Using 365 when B6 always uses 360
- Missing suspension filter: Forgetting to check suspensions CSV for "hold" status
- Missing analysis filter: Including "archive" campaigns in scope
- Billing sum instead of latest: Summing multiple billing records instead of picking latest active cycle_tag
- Blank revision handling: Using blank or non-numeric revisions instead of skipping them