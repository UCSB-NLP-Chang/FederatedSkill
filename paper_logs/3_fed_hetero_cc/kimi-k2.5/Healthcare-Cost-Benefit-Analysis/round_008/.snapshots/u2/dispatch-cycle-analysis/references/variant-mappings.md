# Dispatch Cycle Analysis Variant Mappings

This reference documents known sub-task variants with specific field names, decision strings, and formula differences.

## harbor_vaxcrate_6v12 (Vaccination Outreach)

- **Decision strings**: `keep_6_day`, `switch_to_12_day` (or `move_to_12_day` — verify task spec)
- **Margin difference field**: `annual_margin_difference_12_minus_6_usd`
- **Days per year**: 365 (or 360 for specific crate dispatch domains; verify task spec)
- **Dispatches/year**: 6-day = 60.0, 12-day = 30.0 (at 360 days)
- **Entity**: campaign
- **Catalog structure**: `regions` → `campaigns[]`
- **Key fields**:
  - `campaign_id`, `campaign_name`, `alias_labels[]`
  - `drug_cost_per_1000_doses_usd`, `doses_per_day`
  - `crate_tier`, `default_active_clinics`, `analysis_flag`
- **In-scope filter**: `analysis_flag == "review"`
- **Suspension exclusion**: `suspensions.csv` with `suspension_status == "hold"` → exclude
- **Overrides**: `location_overrides.csv` with `campaign_id,revision,state,active_clinics`
  - Rule: highest numeric approved revision with non-empty `active_clinics`, else `default_active_clinics`
- **Billing**: `billing.csv` with `campaign_label,status,cycle_tag,payment_per_dispatch_per_clinic_usd`
  - Match: `campaign_label` against `campaign_name` or `alias_labels[]` (case-insensitive)
  - Select: latest `cycle_tag` among `status == "active"`
- **Supply**: `crate_cost.csv` with `crate_tier,crate_cost_usd`
- **Supply cost formula**: `crate_cost × dispatches/year × clinics` (NOT per-dispatch alone)

## harbor_infusionbatch_7v14 (Home Infusion) — See infusion-batch-analysis skill

- **Decision strings**: `keep_7_day`, `move_to_14_day`
- **Days per year**: 365
- **Deliveries/year**: exact `365.0/7` and `365.0/14`, NOT integers
- **Entity**: therapy
- **Patient override**: highest approved revision per `therapy_code`
- **Billing match**: `therapy_label` matches `aliases[]` or `therapy_name` (case-insensitive)

## onco_cooler_dispatch (B4: Cooler Dispatch) — See infusion-batch-analysis/references/cooler-dispatch-invariants.md

- **Decision strings**: `keep_X_day`, `switch_to_Y_day`
- **Days per year**: 360 (commonly, verify task spec)
- **Critical formula difference**: Cooler cost is NOT multiplied by sites
  - `annual_cooler_cost = cooler_cost × dispatches_per_year` (per-dispatch, not per-site)
- **Entity mapping**: therapy→program, patients→sites, bags→coolers, dose→units

## harbor_reagentkit_bulk (Reagent Kit) — See reagent-kit-analysis skill

- **Decision strings**: `adopt_bulk_kit`, `keep_small_kit`
- **Runs per year**: small=24, bulk=12
- **Entity**: assay
- **Billing rule**: latest active `effective_month` per assay (alias match)
- **Lab override**: highest approved revision per `assay_id`

## Common Field Name Variants

| Concept | Common Names |
|---------|-------------|
| Entity ID | `campaign_id`, `therapy_code`, `program_code`, `assay_id`, `test_id` |
| Entity name | `campaign_name`, `therapy_name`, `program_name`, `assay_name`, `test_name` |
| Aliases | `alias_labels`, `aliases`, `known_labels` |
| Count type | `active_clinics`, `active_sites`, `active_patients`, `active_labs` |
| Default count | `default_active_clinics`, `default_active_sites`, `default_active_patients`, `default_active_labs` |
| Dose field | `doses_per_day`, `dose_mg_per_day`, `units_per_day` |
| Price field | `drug_cost_per_1000_doses_usd`, `drug_cost_per_1000_mg_usd`, `acquisition_cost_per_1000_units_usd`, `reagent_price_per_1000_tests_usd` |
| Supply key | `crate_tier`, `bag_size_ml`, `cooler_type`, `carrier_type` |
| Supply cost | `crate_cost_usd`, `bag_supply_cost_usd`, `cooler_cost_usd`, `carrier_cost_usd` |
| In-scope flag | `analysis_flag`, `include_in_review`, `review_flag` |
| Override revision | `revision`, `version`, `version_no`, `rev_no` |
| Override status | `status`, `state`, `approval_state` |
| Billing label | `campaign_label`, `therapy_label`, `program_label`, `assay_label` |
| Billing date | `cycle_tag`, `effective_month`, `effective_date` |
| Billing status | `status`, `is_active`, `active` |
| Payment | `payment_per_dispatch_per_clinic_usd`, `payment_per_delivery_per_patient_usd`, `payment_per_run_per_lab_usd` |

## Decision String Patterns

| Pattern | Context |
|---------|---------|
| `keep_X_day` / `switch_to_Y_day` | Generic dispatch cycle |
| `move_to_Y_day` | Infusion batch specific |
| `adopt_bulk_kit` / `keep_small_kit` | Reagent kit specific |
| `convert_to_X` / `maintain_Y` | Generic policy change |

Always verify exact decision strings from task specification.