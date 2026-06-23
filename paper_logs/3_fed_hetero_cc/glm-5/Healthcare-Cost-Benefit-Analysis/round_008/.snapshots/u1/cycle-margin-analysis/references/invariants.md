# Known Invariants by Sub-Task

## pharmacy-refill-cycle-margin (30-day vs 90-day)
- Decision strings: `keep_30_day` or `switch_to_90_day`
- Margin difference field: `margin_difference_90_minus_30_usd`

## pharmacy-refill-cycle-margin (90-day vs 100-day)
- Decision strings: `keep_90_day` or `switch_to_100_day`
- Margin difference field: `margin_difference_100_minus_90_usd`
- All medications in acquisition/wholesale CSV must appear in output

## pharmacy-refill-cycle-margin (28-day vs 56-day)
- Decision strings: `keep_28_day` or `convert_to_56_day`
- Fills per year: Use task-specified values (common: 28-day=12 or 13, 56-day=6)
- Annual doses may differ: 12×56=672 vs 6×112=672 when fills=12/6, but verify per task

## harbor_mailerfill_45v90 (45-day vs 90-day with mailer formats)
- Decision strings: `keep_45_day` or `switch_to_90_day`
- Fills per year: 45-day=8, 90-day=4
- Annual doses: 8×45=360 vs 4×90=360 — drug costs ARE equal
- Packaging join: `mailer_format` (standard/buffered/secure) NOT container size
- Payment structure: base_payment + service_fee = total per-fill payment
- Patient count: Extract from column name suffix (e.g., `_150_patients`)
