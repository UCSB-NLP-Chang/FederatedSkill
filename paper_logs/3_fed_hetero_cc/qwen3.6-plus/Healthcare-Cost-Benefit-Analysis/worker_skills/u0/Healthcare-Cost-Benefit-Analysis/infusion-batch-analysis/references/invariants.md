# Known Invariants by Sub-Task

## harbor_infusionbatch_7v14 (7-day vs 14-day infusion batching)
- Decision strings: `keep_7_day` or `move_to_14_day`
- Margin difference field: `annual_margin_difference_14_minus_7_usd`
- Deliveries per year: 7-day=52, 14-day=26
- Treatment days per year: 364 (7×52 = 14×26) — drug costs are equal between models
- Patient override rule: highest approved revision per therapy_code
- Entity matching: therapy_label in delivery_payment.csv matches aliases[] or therapy_name in catalog
- In-scope filter: `include_in_review: true` in therapy catalog
- Revenue field naming: `annual_revenue` (not `annual_reimbursement`)

## onco_cooler_dispatch (10-day vs 20-day oncology supportive-care cooler dispatch)
- Decision strings: `keep_10_day` or `switch_to_20_day`
- Margin difference field: `annual_margin_difference_20_minus_10_usd`
- In-scope filter: `review_flag == "review"` in program catalog
- Catalog structure: `service_groups → programs` (not `service_lines → therapies`)
- Program fields: `program_code`, `program_name`, `known_labels[]`, `acquisition_cost_per_1000_units_usd`, `units_per_day`, `cooler_type`, `default_active_sites`
- Site override columns: `program_code`, `version_no`, `approval_state`, `active_sites`
- Site override rule: highest approved `version_no` per `program_code`, fallback to `default_active_sites`
- Cooler cost join: `cooler_type` matches `cooler_cost.csv`
- Payment join: `contract_payment.csv` `program_label` matches `known_labels[]` or `program_name` (case-insensitive)
- Days per year: commonly 360 (verify task spec)
- **CRITICAL**: Cooler cost formula: `cooler_cost_usd × (days_per_year / cycle_days)` — NO site multiplier
- Revenue formula: `payment_per_dispatch_per_site × (days_per_year / cycle_days) × active_sites` — sites ARE multiplied
- Drug cost formula: `(price_per_1000 / 1000) × units_per_day × days_per_year × active_sites` — sites ARE multiplied
- Output files: `oncocooler_analysis.json`, `oncocooler_summary.md`

## harbor_vaxcrate_6v12 (6-day vs 12-day vaccination crate dispatch)
- Decision strings: `keep_6_day` or `switch_to_12_day` (verify task spec for exact format)
- Margin difference field: `annual_margin_difference_12_minus_6_usd`
- Days per year: **360** (NOT 365)
- Dispatches/year: 6-day = 60.0, 12-day = 30.0
- Entity: campaign
- Catalog structure: `regions` → `campaigns[]`
- Campaign fields: `campaign_id`, `campaign_name`, `alias_labels[]`, `drug_cost_per_1000_doses_usd`, `doses_per_day`, `crate_tier`, `default_active_clinics`, `analysis_flag`, `suspension_status`
- In-scope filter: `analysis_flag != "archive"` — exclude archived campaigns
- Suspension filter: Load `suspensions.csv` and exclude campaigns where `suspension_status == "hold"`
- Overrides: `location_overrides.csv` with columns `campaign_id`, `revision`, `state`, `active_clinics`
  - Rule: highest numeric approved revision with non-empty `active_clinics`, else `default_active_clinics`
  - Skip blank revisions entirely (don't treat as 0)
- Billing: `billing.csv` with columns `campaign_label`, `status`, `cycle_tag`, `payment_per_dispatch_per_clinic_usd`
  - Match: `campaign_label` against `campaign_name` or `alias_labels[]` (case-insensitive)
  - Select: latest `cycle_tag` among `status == "active"` records
  - Do NOT sum multiple billing records
- Supply: `crate_cost.csv` with `crate_tier`, `crate_cost_usd`
- **CRITICAL**: Crate cost formula: `crate_cost_usd × (360 / cycle_days)` — NO clinic multiplier
- Revenue formula: `payment_per_dispatch × (360 / cycle_days) × active_clinics` — clinics ARE multiplied
- Drug cost formula: `(price_per_1000 / 1000) × doses_per_day × 360 × active_clinics` — clinics ARE multiplied
- Output files: `vaxcrate_analysis.json`, `vaxcrate_summary.md`

## harbor_diagpanel_14v28 (14-day vs 28-day diagnostic panel dispatch)
- Decision strings: `keep_14_day` or `switch_to_28_day`
- Margin difference field: `annual_margin_difference_28_minus_14_usd`
- Runs per year: `365.0/14 = 26.071...`, `365.0/28 = 13.035...` (exact float, NOT integers 26/13)
- Entity: panel
- Catalog structure: `service_clusters` → `panels[]`
- Panel fields: `panel_code`, `panel_name`, `alias_labels[]`, `reagent_cost_per_1000_tests_usd`, `tests_per_lab_per_run_14_day`, `tests_per_lab_per_run_28_day`, `network_tier`, `shipper_class`, `default_active_labs`, `analysis_mode`
- In-scope filter: `analysis_mode == "review"` — exclude archive/other
- Holdout exclusions: Load `holdouts.json`, exclude panels where `holdout_state == "exclude"`
- Overrides: `lab_capacity_overrides.csv` with columns `panel_code`, `rev`, `approval`, `active_labs`
  - Rule: highest numeric approved `rev` with non-empty `active_labs`, else `default_active_labs`
  - Skip blank `rev` or blank `active_labs` rows
- Contracts: `contract_terms.csv` with columns `panel_ref`, `status_flag`, `effective_week`, `base_payment_per_run_per_lab_usd`
  - Match: `panel_ref` against `panel_name` or `alias_labels[]` (case-insensitive)
  - Select: latest `effective_week` among `status_flag == "current"` records (descending sort by week)
  - Do NOT sum multiple contract records
- Network: `network_adjustments.csv` with `network_tier`, `network_adjustment_per_run_per_lab_usd`
  - Total payment = base_payment + network_adjustment
  - Default to 0.0 if network_tier not found
- Shipper: `shipper_cost.csv` with `shipper_class`, `shipper_cost_usd`
- **CRITICAL**: Shipper cost formula: `shipper_cost_usd × runs_per_year` — NO lab multiplier (per-dispatch)
- Revenue formula: `(base_payment + network_adjustment) × runs × labs` — labs ARE multiplied
- Reagent cost formula: `tests_per_run × runs × labs × (price_per_1000 / 1000)` — labs ARE multiplied
- Output files: `diagpanel_policy_report.json`, `diagpanel_policy_summary.md`
