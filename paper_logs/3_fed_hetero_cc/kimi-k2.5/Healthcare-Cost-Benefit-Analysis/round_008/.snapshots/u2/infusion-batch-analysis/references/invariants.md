# Known Invariants by Sub-Task

## harbor_infusionbatch_7v14 (7-day vs 14-day infusion batching)
- Decision strings: `keep_7_day` or `move_to_14_day`
- Margin difference field: `annual_margin_difference_14_minus_7_usd`
- Deliveries per year: 7-day=52.142857... (365.0/7), 14-day=26.071428... (365.0/14)
- Treatment days per year: drug costs are equal between models (same annual dose)
- Patient override rule: highest approved revision per therapy_code
- Entity matching: therapy_label in delivery_payment.csv matches aliases[] or therapy_name in catalog (case-insensitive)
- In-scope filter: `include_in_review: true` in therapy catalog
- Revenue field naming: `annual_revenue` (not `annual_reimbursement`)