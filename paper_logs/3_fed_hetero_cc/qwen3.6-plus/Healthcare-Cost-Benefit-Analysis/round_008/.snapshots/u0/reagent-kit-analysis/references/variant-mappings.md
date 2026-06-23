# Reagent Kit Analysis Variant Mappings

This reference documents known sub-task variants with specific field names and decision strings.

## harbor_reagentkit_bulk (Standard Variant)

- Decision strings: `adopt_bulk_kit`, `keep_small_kit`
- Margin difference field: `annual_margin_difference_bulk_minus_small_usd`
- Runs per year: small=24, bulk=12
- Lab override rule: highest approved revision per assay_id
- Billing rule: latest active effective_month per assay
- In-scope filter: `in_scope: true` in assay manifest
- Entity matching: assay_label in billing.csv matches assay_name or aliases[] (exact case-sensitive match)

## Common Field Name Variants

| Concept | Standard | Possible Variants |
|---------|----------|-------------------|
| Entity ID | `assay_id` | `test_id`, `panel_id` |
| Entity name | `assay_name` | `test_name`, `panel_name` |
| Count type | `active_labs` | `active_sites`, `active_clinics` |
| Price | `reagent_price_per_1000_tests_usd` | `reagent_cost_per_1000_usd` |
| Carrier | `carrier_type` | `shipper_type`, `container_type` |
| Tests small | `tests_per_run_small` | `tests_per_batch_small` |
| Tests bulk | `tests_per_run_bulk` | `tests_per_batch_bulk` |
| Override revision | `revision` | `version`, `rev_no` |
| Override status | `status` | `approval_state`, `review_status` |
| Billing date | `effective_month` | `effective_date`, `valid_from` |
| Billing active | `is_active` | `active`, `enabled` |

## Decision String Patterns

| Pattern | When Used |
|---------|-----------|
| `adopt_bulk_kit` / `keep_small_kit` | Standard bulk vs small comparison |
| `switch_to_bulk` / `retain_small` | Alternative phrasing |
| `convert_to_X` / `maintain_Y` | Generic pattern for policy changes |

Always verify exact decision strings from task specification.
