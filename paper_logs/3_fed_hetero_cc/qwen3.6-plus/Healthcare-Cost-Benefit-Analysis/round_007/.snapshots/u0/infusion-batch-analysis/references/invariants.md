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
