---
name: infusion-batch-analysis
description: Computes and compares annual margin/revenue between two delivery/dispatch cycle lengths using a JSON catalog with review flags, CSV overrides with version/revision control, and cost/payment CSVs. Covers home infusion delivery batching (7-day vs 14-day), oncology supportive-care cooler dispatch (10-day vs 20-day), and vaccination crate dispatch (6-day vs 12-day). Use when tasked with evaluating delivery frequency economics, margin optimization, or dispatch/batching decisions. Distinct from cycle-margin-analysis: uses per-entity patient/site/clinic counts, per-day drug costing, per-delivery/dispatch payments, and alias/label-based entity matching.
---

# Infusion Batch Analysis

## When to Use
- Task involves comparing financial impact of two delivery/dispatch cycle frequencies.
- **Home infusion batching (B3)**: JSON therapy catalog with dose rates, CSV patient overrides with revision/status, per-patient delivery payment CSV, bag supply cost CSV.
- **Oncology cooler dispatch (B4)**: JSON program catalog with review_flag, CSV site overrides with version_no/approval_state, cooler cost CSV, contract payment CSV.
- **Vaccination crate dispatch (B6)**: JSON campaign manifest with analysis_flag and suspension_status, CSV clinic overrides with revision/state, crate cost CSV, billing CSV with cycle_tag.
- Output requires JSON breakdown and Markdown summary with a move/keep/switch decision against a threshold.

## Pre-Flight Checklist

Extract from task:
- [ ] Cycle lengths to compare in DAYS (e.g., 7-day vs 14-day, 3-day vs 7-day)
- [ ] **Deliveries per year: use exact floating-point values, NOT integers**
  - 7-day cycle: `365.0/7 = 52.142857...`
  - 14-day cycle: `365.0/14 = 26.071428...`
  - Do NOT round to 52 or 26
- [ ] Decision threshold in USD
- [ ] Decision output format (e.g., `move_to_14_day`, `keep_7_day`)

**Critical precision rule**: Always use `365.0 / cycle_days`. Never use integer approximations.

## Input Data Structure

### Therapy Catalog (JSON)
- Nested by `service_lines` → `therapies` array
- Each therapy has: `therapy_code`, `therapy_name`, `aliases[]`, `drug_cost_per_1000_mg_usd`, `dose_mg_per_day`, `bag_size_ml`, `include_in_review`
- Filter to `include_in_review: true` only

### Patient Overrides (CSV)
- Columns: `therapy_code`, `revision`, `status`, `active_patients`
- **Critical**: Select only the highest revision where `status == "approved"` per therapy_code
- Ignore `draft` and `rejected` revisions entirely

### Delivery Payment (CSV)
- Columns: `therapy_label`, `payment_per_delivery_per_patient_usd`
- `therapy_label` matches `aliases[]` or `therapy_name` from catalog — NOT `therapy_code`
- Case-insensitive matching

### Bag Supply Cost (CSV)
- Columns: `bag_size_ml`, `bag_supply_cost_usd`
- Join key: `bag_size_ml` from therapy catalog

## Workflow

### For B3 (Home Infusion) and B4 (Cooler Dispatch)
1. **Parse therapy catalog**: Load JSON, flatten therapies, filter `include_in_review: true`.
2. **Build alias map**: Map each alias (case-insensitive) to `therapy_code` for payment matching.
3. **Resolve patient counts**: From overrides CSV, for each therapy_code, select the row with highest revision where status=approved.
4. **Join supply costs**: Match `bag_size_ml` from catalog to supply cost CSV.
5. **Join payments**: Match `therapy_label` from payment CSV via alias map.
6. **Run computation**: Execute `scripts/compute_infusion_batch.py` with appropriate arguments.
   ```bash
   python3 scripts/compute_infusion_batch.py \
     --catalog therapy_catalog.json \
     --supply bag_supply_cost.csv \
     --payments delivery_payment.csv \
     --overrides patient_overrides.csv \
     --cycle-a 7 --cycle-b 14 \
     --threshold 15000 \
     --output-dir .
   ```
7. **Verify outputs**: Check that `infusion_batch_analysis.json` and `infusion_batch_summary.md` are generated.
8. **Review decision**: Script outputs `move_to_X` or `keep_X` based on margin comparison AND threshold check.

### For B6 (Vaccination Crate Dispatch)
1. **Filter campaigns**: Load JSON manifest, flatten campaigns, exclude `analysis_flag == "archive"` AND `suspension_status == "hold"`.
2. **Build alias map**: Map each `alias_labels[]` and `campaign_name` (case-insensitive) to `campaign_id`.
3. **Resolve clinic counts**: From overrides CSV, for each `campaign_id`, select highest numeric approved revision with non-empty `active_clinics`. Fallback to `default_active_clinics`.
4. **Join crate costs**: Match `crate_tier` from manifest to crate cost CSV.
5. **Join billing**: Match `campaign_label` against alias map. Among active records, pick latest `cycle_tag`.
6. **Run computation**: Execute `scripts/compute_vaxcrate.py` with appropriate arguments.
   ```bash
   python3 scripts/compute_vaxcrate.py \
     --manifest campaign_manifest.json \
     --suspensions suspensions.csv \
     --overrides location_overrides.csv \
     --billing billing.csv \
     --crates crate_cost.csv \
     --cycle-a 6 --cycle-b 12 \
     --threshold 11000 \
     --output-dir .
   ```
7. **Verify outputs**: Check that `vaxcrate_analysis.json` and `vaxcrate_summary.md` are generated.
8. **Review decision**: Script outputs `switch_to_X_day` or `keep_X_day` based on margin comparison AND threshold check.

## Key Formulas

### Home Infusion Batching (B3)

| Metric | Formula |
|--------|---------|
| Annual drug cost | `dose_mg_per_day × 365 × patients × (price_per_1000 / 1000)` |
| Annual supply cost | `bag_cost_usd × (365.0 / cycle_days) × patients` |
| Annual revenue | `payment_per_delivery × (365.0 / cycle_days) × patients` |
| Annual margin | `revenue - drug_cost - supply_cost` |

**Note**: Drug cost is identical between cycles (annual dose fixed). Supply and revenue scale with delivery frequency.

### Oncology Cooler Dispatch (B4)

| Metric | Formula |
|--------|---------|
| Annual drug cost | `(price_per_1000 / 1000) × units_per_day × days_per_year × active_sites` |
| Annual cooler cost | `cooler_cost_usd × (days_per_year / cycle_days)` — NOT multiplied by sites |
| Annual revenue | `payment_per_dispatch_per_site × (days_per_year / cycle_days) × active_sites` |
| Annual margin | `revenue - drug_cost - cooler_cost` |

**Critical**: Cooler cost is per-dispatch (NOT per-site). Revenue IS per-site. Drug cost IS per-site.
**Days per year**: Commonly 360 for oncology programs; verify task spec.

### Vaccination Crate Dispatch (B6)

| Metric | Formula |
|--------|---------|
| Annual drug cost | `(price_per_1000 / 1000) × doses_per_day × 360 × active_clinics` |
| Annual crate cost | `crate_cost_usd × (360 / cycle_days)` — NOT multiplied by clinics |
| Annual revenue | `payment_per_dispatch × (360 / cycle_days) × active_clinics` |
| Annual margin | `revenue - drug_cost - crate_cost` |

**Critical**: Crate cost is per-dispatch (NOT per-clinic). Revenue IS per-clinic. Drug cost IS per-clinic.
**Days per year**: 360 for vaccination campaigns.
**Filters**: Exclude `analysis_flag == "archive"` AND `suspension_status == "hold"`.
**Billing**: Match `campaign_label` to `alias_labels[]` or `campaign_name`. Among active, pick latest `cycle_tag`.

## Decision Rule

```python
abs_diff = abs(margin_b - margin_a)
if margin_b > margin_a and abs_diff > threshold:
    decision = f"move_to_{label_b}"
else:
    decision = f"keep_{label_a}"
```

Switch only if the alternative is BOTH better AND exceeds threshold.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, CSV, Excel). Pass raw float values directly. Let the verifier's
tolerance decide acceptable precision.

## Anti-Patterns
- **Do NOT** use integer deliveries/year (`52`, `26`). Always use `365.0 / cycle_days`.
- **Do NOT** match payment CSV to therapy by code alone—use the alias map.
- **Do NOT** include therapies with `include_in_review: false`.
- **Do NOT** sum patient revisions—pick highest approved revision per therapy.
- **Do NOT** use draft or rejected patient override revisions — only approved.
- **Do NOT** use a single global patient count — each therapy has its own count.
- **Do NOT** forget to filter by `include_in_review: true`.
- **Do NOT** invert the decision: switch only if BETTER AND exceeds threshold.

### Cooler Dispatch Specific (B4)
- **Do NOT** multiply cooler cost by active sites — it is per-dispatch only.
- **Do NOT** assume 365 days/year — oncology programs commonly use 360.
- **Do NOT** match payments by `program_code` — use `known_labels[]` + `program_name` label map.
- **Do NOT** skip default fallback — use `default_active_sites` when no approved override exists.
- **Do NOT** ignore `review_flag` — only include programs where `review_flag == "review"`.

### Vaxcrate Dispatch Specific (B6)
- **Do NOT** multiply crate cost by active clinics — it is per-dispatch only.
- **Do NOT** use 365 days/year — vaccination campaigns use 360.
- **Do NOT** include campaigns with `analysis_flag == "archive"` or `suspension_status == "hold"`.
- **Do NOT** sum billing records — pick latest active `cycle_tag` only.
- **Do NOT** match billing by `campaign_id` — use `alias_labels[]` + `campaign_name` label map.
- **Do NOT** use draft/rejected overrides or blank revisions — pick highest numeric approved revision.

## Key Differences from Cycle Margin Analysis
- **Patient counts are per-therapy**, not a single global number
- **Drug cost uses dose_mg_per_day × 365 days**, not price_per_1000 × doses_per_fill × fills
- **Revenue is per-patient per-delivery**, multiplied by patients — NOT per-cohort
- **Entity matching uses aliases**, not direct key joins
- **Patient overrides have revision control** — must select highest approved revision
- **Supply cost is per bag per delivery**, not per container per fill

## Known invariants (by sub-task)

### harbor_infusionbatch_7v14 (7-day vs 14-day infusion batching)
- Decision strings: `keep_7_day` or `move_to_14_day`
- Margin difference field: `annual_margin_difference_14_minus_7_usd`
- Deliveries per year: use exact `365.0/7` and `365.0/14` (not integers)
- Treatment days per year: 365 (drug costs are equal between models)
- Patient override rule: highest approved revision per therapy_code
- Entity matching: therapy_label in delivery_payment.csv matches aliases[] or therapy_name in catalog
- In-scope filter: `include_in_review: true` in therapy catalog
- Revenue field naming: `annual_revenue` (not `annual_reimbursement`)

### onco-cooler-dispatch (10-day vs 20-day oncology supportive-care cooler)
- Decision strings: `keep_10_day` or `switch_to_20_day`
- In-scope filter: `review_flag == "review"` in program catalog
- Catalog structure: `service_groups → programs` (not `service_lines → therapies`)
- Site override rule: highest approved `version_no` per `program_code`, else `default_active_sites`
- Entity matching: payment CSV `program_label` matches `known_labels[]` or `program_name` (case-insensitive)
- Cooler cost join: `cooler_type` field in catalog matches `cooler_type` in cooler cost CSV
- **CRITICAL**: Cooler cost is per-dispatch, NOT per-site — formula: `cooler_cost × dispatches/year`
- Days per year: commonly 360 (verify task spec; NOT always 365)
- Output files: `oncocooler_analysis.json`, `oncocooler_summary.md`

## Troubleshooting
- **Missing payment match**: Check alias mapping is case-insensitive; verify CSV therapy_label against all aliases.
- **Wrong patient counts**: Ensure filtering for `status=approved` and max revision, not just latest row.
- **Precision mismatch**: Verify using `365.0` (float) not `365` (int) in division.
- **Negative margins**: Expected in infusion models; focus on difference between cycles.
- **Decision seems wrong**: Re-check threshold comparison — switch only if BOTH conditions met.

## Reference Files
- `references/invariants.md`: Sub-task specific field names and decision strings.
- `references/calculation-examples.md`: Worked examples with exact precision.
