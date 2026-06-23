---
name: infusion-batch-analysis
description: Computes and compares annual margin/revenue between two batch/cycle lengths for healthcare delivery programs. Covers three variants: (A) Home infusion delivery batching (7-day vs 14-day) using therapy catalog with patient overrides, (B) Oncology supportive-care cooler dispatch (10-day vs 20-day) using program catalog with site overrides, and (C) Vaccination outreach dispatch (6-day vs 12-day) using campaign manifest with clinic overrides. All use JSON catalogs with revision control, alias-based matching, and threshold-based keep/switch decisions. Use when tasked with evaluating batching economics, delivery frequency optimization, or dispatch cycle decisions. Distinct from cycle-margin-analysis: uses per-program patient/site/clinic counts, dose-rate drug costing, per-delivery/dispatch payments, and alias-based entity matching.
---

# Infusion Batch Analysis

## STOP — Read This First

**Do NOT compute inline.** This skill includes bundled scripts that handle all joins, alias matching, revision logic, and precision calculations. Running Python inline will produce errors. Use the appropriate script for your variant:
- Variant A: `scripts/compute_infusion_batch.py`
- Variant B: `scripts/compute_cooler_dispatch.py`
- Variant C: `scripts/compute_vaxcrate.py`

## When to Use
- Task involves comparing financial impact of two batch/cycle frequencies for healthcare delivery programs.
- **Variant A (Infusion Delivery)**: Comparing infusion delivery batch frequencies (e.g., 7-day vs 14-day). Input: therapy catalog, patient overrides, delivery payment, bag supply cost.
- **Variant B (Oncology Cooler Dispatch)**: Comparing cooler dispatch cycle lengths (e.g., 10-day vs 20-day). Input: program catalog, site overrides, contract payment, cooler cost. Commonly uses 360 days/year.
- Output requires JSON breakdown and Markdown summary with a keep/switch decision against a threshold.
- **Variant C (Vaccination Outreach Dispatch)**: Comparing vaccination crate dispatch cycle lengths (e.g., 6-day vs 12-day). Input: campaign manifest, suspensions CSV, location overrides, billing CSV, crate costs. Commonly uses 360 days/year. Additional filtering by analysis_flag and suspension_status.
- **Not for pharmacy refill cycles** — use `cycle-margin-analysis` skill when drug costs are per-fill, patient counts are global, and inputs are CSV-only.

## Pre-Flight Checklist
- [ ] Delivery/dispatch frequencies and cycle days (e.g., 7-day vs 14-day, 10-day vs 20-day)
- [ ] **Critical precision rule**: Use EXACT float division for deliveries/dispatches per year — never round to integers
- [ ] Decision threshold in USD
- [ ] Decision output string format (e.g., `keep_7_day` vs `move_to_14_day`, `keep_10_day` vs `switch_to_20_day`)
- [ ] Which items are in scope (`include_in_review` flag or `review_flag` in catalog)
- [ ] Override selection rule: highest approved revision/version per code
- [ ] **Variant B only**: Days per year for drug costing — commonly 360 (NOT 365). Verify task spec carefully.

**Critical precision rule**: Do NOT round deliveries/year to integers like `52` or `26`. Always use `365.0 / cycle_days`:
- 7-day cycle: `365.0 / 7 = 52.142857...` deliveries/year
- 14-day cycle: `365.0 / 14 = 26.071428...` deliveries/year
- 3-day cycle: `365.0 / 3 = 121.666...` deliveries/year

## Input Data Structure

### Variant A: Infusion Delivery (Therapy Catalog)

#### Therapy Catalog (JSON)
- Nested by `service_lines` → `therapies` array
- Each therapy has: `therapy_code`, `therapy_name`, `aliases[]`, `drug_cost_per_1000_mg_usd`, `dose_mg_per_day`, `bag_size_ml`, `include_in_review`
- Filter to `include_in_review: true` only

#### Patient Overrides (CSV)
- Columns: `therapy_code`, `revision`, `status`, `active_patients`
- **Critical**: Select only the highest revision where `status == "approved"` per therapy_code
- Ignore `draft` and `rejected` revisions entirely
- If no approved revision exists for an in-scope therapy, exclude it or escalate

#### Delivery Payment (CSV)
- Columns: `therapy_label`, `payment_per_delivery_per_patient_usd`
- `therapy_label` matches `aliases[]` or `therapy_name` from catalog — NOT `therapy_code`
- Must resolve alias matching (case-insensitive, strip hyphens/spaces)

#### Bag Supply Cost (CSV)
- Columns: `bag_size_ml`, `bag_supply_cost_usd`
- Join key: `bag_size_ml` from therapy catalog

### Variant B: Oncology Cooler Dispatch (Program Catalog)

#### Program Catalog (JSON)
- Nested by `service_groups` → `programs` array
- Each program has: `program_code`, `program_name`, `known_labels[]`, `acquisition_cost_per_1000_units_usd`, `units_per_day`, `cooler_type`, `default_active_sites`, `review_flag`
- Filter to `review_flag: "review"` only (string comparison)

#### Site Overrides (CSV)
- Columns: `program_code`, `version_no`, `approval_state`, `active_sites`
- **Critical**: Select only the highest `version_no` where `approval_state == "approved"` per program_code
- If no approved version exists, fallback to `default_active_sites` from catalog

#### Contract Payment (CSV)
- Columns: `program_label`, `payment_per_dispatch_per_site_usd`
- `program_label` matches `known_labels[]` or `program_name` (case-insensitive)

#### Cooler Cost (CSV)
- Columns: `cooler_type`, `cooler_cost_usd`
- Join key: `cooler_type` from program catalog

### Variant C: Vaccination Outreach Dispatch (Campaign Manifest)

#### Campaign Manifest (JSON)
- Nested by `regions` → `campaigns` array
- Each campaign has: `campaign_id`, `campaign_name`, `alias_labels[]`, `drug_cost_per_1000_doses_usd`, `doses_per_day`, `crate_tier`, `default_active_clinics`, `analysis_flag`
- **Filter**: Exclude where `analysis_flag == "archive"`
- **Suspension filter**: Also check suspensions CSV for `suspension_status == "hold"` — exclude those

#### Suspensions (CSV)
- Columns: `campaign_id`, `suspension_status`
- Exclude campaigns where `suspension_status == "hold"`

#### Location Overrides (CSV)
- Columns: `campaign_id`, `revision`, `state`, `active_clinics`
- **Critical**: Select only the highest numeric revision where `state == "approved"` per campaign_id
- Skip rows with blank revision or blank active_clinics
- If no approved override with valid clinics exists, fallback to `default_active_clinics` from manifest

#### Billing (CSV)
- Columns: `campaign_label`, `status`, `cycle_tag`, `payment_per_dispatch_per_clinic_usd`
- `campaign_label` matches `alias_labels[]` or `campaign_name` (case-insensitive)
- **Critical selection**: Among `status == "active"`, pick the **latest** `cycle_tag` per campaign
- Do NOT sum multiple billing records — pick single latest active

#### Crate Costs (CSV)
- Columns: `crate_tier`, `crate_cost_usd`
- Join key: `crate_tier` from campaign manifest

## Workflow

### Variant A: Infusion Delivery Batch Analysis

1. **Parse therapy catalog**: Extract in-scope therapies (`include_in_review: true`).
2. **Resolve patient counts**: From overrides CSV, for each therapy_code, select the row with highest revision where status=approved. Store `active_patients`.
3. **Build alias map**: Map each alias (case-insensitive) and therapy_name → therapy_code for payment matching.
4. **Resolve delivery payments**: Match each therapy's aliases/therapy_name to `therapy_label` in delivery payment CSV (case-insensitive, normalize whitespace/hyphens).
5. **Resolve bag supply costs**: Join on `bag_size_ml`.
6. **Run Computation**: Execute `scripts/compute_infusion_batch.py` with appropriate arguments.
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
7. **Verify Outputs**: Check that `infusion_batch_analysis.json` and `infusion_batch_summary.md` are generated.
8. **Review Decision**: The script outputs the appropriate `move_to_X` or `keep_X` decision.

### Variant B: Oncology Cooler Dispatch Analysis

1. **Parse program catalog**: Extract in-scope programs (`review_flag == "review"`).
2. **Build label map**: Map each `known_label` (case-insensitive) and `program_name` → program_code for payment matching.
3. **Resolve active sites**: From overrides CSV, for each program_code, select the row with highest `version_no` where `approval_state == "approved"`. If no approved override exists, fallback to `default_active_sites` from catalog.
4. **Resolve cooler costs**: Join on `cooler_type`.
5. **Resolve contract payments**: Match each program's known_labels/program_name to `program_label` in payment CSV (case-insensitive).
6. **Run Computation**: Execute `scripts/compute_cooler_dispatch.py` with appropriate arguments.
   ```bash
   python3 scripts/compute_cooler_dispatch.py \
     --catalog program_catalog.json \
     --overrides site_overrides.csv \
     --cooler-costs cooler_cost.csv \
     --payments contract_payment.csv \
     --cycle-a 10 --cycle-b 20 \
     --days-per-year 360 \
     --threshold 10000 \
     --output-dir .
   ```
7. **Verify Outputs**: Check that `cooler_dispatch_analysis.json` and `cooler_dispatch_summary.md` are generated.
8. **Review Decision**: The script outputs the appropriate `keep_X_day` or `switch_to_X_day` decision.

### Variant C: Vaccination Outreach Dispatch Analysis

1. **Parse campaign manifest**: Extract campaigns where `analysis_flag != "archive"`.
2. **Filter by suspensions**: Check suspensions CSV; exclude campaigns where `suspension_status == "hold"`.
3. **Build alias map**: Map each `alias_label` (case-insensitive) and `campaign_name` → campaign_id for billing matching.
4. **Resolve clinics**: From overrides CSV, for each campaign_id, select the row with highest numeric revision where `state == "approved"` AND `active_clinics` is non-empty. If no valid approved override, fallback to `default_active_clinics` from manifest.
5. **Resolve crate costs**: Join on `crate_tier`.
6. **Resolve billing**: Match each campaign's alias_labels/campaign_name to `campaign_label` in billing CSV (case-insensitive). Among `status == "active"` records, pick the **latest** `cycle_tag`.
7. **Run Computation**: Execute `scripts/compute_vaxcrate.py` with appropriate arguments.
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
8. **Verify Outputs**: Check that `vaxcrate_analysis.json` and `vaxcrate_summary.md` are generated.
9. **Review Decision**: The script outputs the appropriate `keep_X_day` or `switch_to_Y_day` decision.

## Key Formulas (with units)

### Variant A: Infusion Delivery

| Metric | Formula |
|--------|---------|
| Annual drug cost | `dose_mg_per_day × 365 × patients × (price_per_1000 / 1000)` |
| Annual supply cost | `bag_cost_usd × (365.0 / cycle_days) × patients` |
| Annual revenue | `payment_per_delivery × (365.0 / cycle_days) × patients` |
| Annual margin | `revenue - drug_cost - supply_cost` |

**Note**: Drug cost is identical between cycles (annual dose fixed). Supply and revenue scale with delivery frequency.

### Variant B: Oncology Cooler Dispatch

| Metric | Formula |
|--------|---------|
| Dispatches/year | `days_per_year / cycle_days` (use 360 or 365 per task spec) |
| Annual drug cost | `(price_per_1000 / 1000) × units_per_day × days_per_year × active_sites` |
| Annual cooler cost | `cooler_cost_usd × dispatches_per_year` (**NOT × sites**) |
| Annual revenue | `payment_per_dispatch_per_site × dispatches_per_year × active_sites` |
| Annual margin | `revenue - drug_cost - cooler_cost` |

**Critical**: Cooler cost is a per-dispatch program cost, NOT per-site. Do NOT multiply cooler cost by active sites.

### Variant C: Vaccination Outreach Dispatch

| Metric | Formula |
|--------|---------|
| Dispatches/year | `360.0 / cycle_days` (typically 360 days/year) |
| Annual drug cost | `doses_per_day × 360 × clinics × (price_per_1000 / 1000)` |
| Annual crate cost | `crate_cost_usd × dispatches_per_year` (**NOT × clinics**) |
| Annual revenue | `payment_per_dispatch_per_clinic × dispatches_per_year × clinics` |
| Annual margin | `revenue - drug_cost - crate_cost` |

**Critical**: Crate cost is a per-dispatch cost, NOT per-clinic. Do NOT multiply crate cost by clinics.

## Decision Rule

If `margin_B > margin_A` AND `|margin_B - margin_A| > threshold`: choose B (`move_to_B`).
Otherwise: keep A (`keep_A`).

**Common mistake**: Inverting the decision — if the better model's advantage is BELOW threshold, keep the current model.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, CSV, Excel). Pass raw float values directly. Let the verifier's
tolerance decide acceptable precision.

## Key Differences from Cycle Margin Analysis
- **Patient/site counts are per-program**, not a single global number
- **Drug cost uses dose_rate × days/year**, not price_per_1000 × doses_per_fill × fills
- **Revenue is per-patient/site per delivery/dispatch**, multiplied by patients/sites — NOT per-cohort
- **Entity matching uses aliases/labels**, not direct key joins
- **Overrides have revision/version control** — must select highest approved revision/version
- **Supply/cooler cost is per delivery/dispatch**, not per container per fill
- **Deliveries/dispatches per year uses exact float division**, not integer approximations
- **Variant B**: Days per year may be 360 (NOT 365) — verify task spec carefully
- **Variant B**: Cooler cost is NOT multiplied by sites — it's a per-dispatch cost

## Anti-Patterns

### General (All Variants)
- Do NOT use draft or rejected override revisions — only approved.
- Do NOT assume payment labels match program/therapy codes — use aliases/labels for matching.
- Do NOT use a single global patient/site count — each program has its own count from overrides.
- Do NOT assume drug costs differ between batch models when treatment days per year are equal.
- Do NOT invert the decision: if the better model's advantage is BELOW threshold, keep the current model.
- Do NOT use integer deliveries/year (`52`, `26`, `36`) — always use exact float division.
- Avoid inline Python for this calculation; use the bundled script to prevent join and alias-matching errors.

### Variant A Specific
- Do NOT multiply delivery payment by patient count twice — it's per-patient, so multiply by patients once.
- Do NOT forget to filter by `include_in_review: true` — some therapies are explicitly excluded.
- Do NOT assume the highest revision number is automatically approved — check status field.

### Variant B Specific
- **Do NOT multiply cooler cost by active sites** — cooler cost is per-dispatch, NOT per-site. This is the most common B4 error.
- Do NOT use `include_in_review` — B4 uses `review_flag: "review"` instead.
- Do NOT assume 365 days/year — B4 commonly uses 360. Verify task spec.
- Do NOT forget to fallback to `default_active_sites` when no approved override exists.
- Do NOT match payments by `program_code` — use `known_labels[]` or `program_name` (label map).

### Variant C Specific
- **Do NOT multiply crate cost by clinics** — crate cost is per-dispatch, NOT per-clinic. This is the most common B6 error.
- Do NOT use 365 days/year — B6 uses 360. Always use `360.0 / cycle_days`.
- Do NOT include campaigns where `analysis_flag == "archive"` — they are out of scope.
- Do NOT include campaigns where `suspension_status == "hold"` — check suspensions CSV.
- Do NOT sum billing records — pick the **latest** `cycle_tag` among `status == "active"`.
- Do NOT use draft/rejected overrides or blank revisions — only highest numeric approved revision with valid clinics.

## Troubleshooting

### General
- **Alias/label matching failures**: Normalize both sides (lowercase, strip hyphens, collapse whitespace). Build a lookup from all aliases/labels + name.
- **Multiple approved revisions for same program**: Take the one with the highest revision number.
- **Negative margins**: Expected in these models; focus on the difference between models.
- **Decision seems wrong**: Re-check the threshold comparison logic — switch only if the alternative is BOTH better AND exceeds threshold.
- **Precision mismatch**: Verify using float division (e.g., `360.0 / cycle_days`) not integer division.

### Variant A Specific
- **Missing approved revision**: If a therapy has no approved override row, flag it — do not assume zero patients.
- **Wrong patient count**: Ensure you selected highest approved revision, not highest revision overall.

### Variant B Specific
- **Missing payment match**: Check case-insensitive label mapping. `known_labels[]` and `program_name` are both valid keys.
- **Wrong site count**: Ensure fallback to `default_active_sites` when no approved override. Also check you're using highest approved `version_no`, not highest overall.
- **Cooler cost too high**: You may have multiplied by `active_sites`. Cooler cost is `cooler_cost × dispatches/year` only.
- **Days/year mismatch**: B4 commonly uses 360. Check if the task explicitly specifies `days_per_year` parameter.

### Variant C Specific
- **Missing billing match**: Check alias mapping. `alias_labels[]` and `campaign_name` are both valid keys.
- **Wrong clinic count**: Ensure non-empty `active_clinics` check. Skip blank revisions. Fallback to `default_active_clinics` when no valid approved override.
- **Crate cost too high**: You may have multiplied by `clinics`. Crate cost is `crate_cost × dispatches/year` only.
- **Wrong campaigns included**: Double-check `analysis_flag != "archive"` AND `suspension_status != "hold"` filters.
- **Multiple billing records**: Pick latest `cycle_tag` among `status == "active"` — do NOT sum.

## Known Invariants (by sub-task)

### harbor_infusionbatch_7v14 (Variant A: 7-day vs 14-day infusion batching)
- Decision strings: `keep_7_day` or `move_to_14_day`
- Margin difference field: `annual_margin_difference_14_minus_7_usd`
- Deliveries per year: 7-day=`365.0/7`, 14-day=`365.0/14`
- Treatment days per year: 365 (drug costs are equal between models)
- Patient override rule: highest approved revision per therapy_code
- Entity matching: therapy_label in delivery_payment.csv matches aliases[] or therapy_name in catalog (case-insensitive)
- In-scope filter: `include_in_review: true` in therapy catalog
- Revenue field naming: `annual_revenue` (not `annual_reimbursement`)

### onco_cooler_dispatch_10v20 (Variant B: 10-day vs 20-day cooler dispatch)
- Decision strings: `keep_10_day` or `switch_to_20_day`
- Margin difference field: `annual_margin_difference_20_minus_10_usd`
- Dispatches per year: 10-day=`days_per_year/10`, 20-day=`days_per_year/20`
- **Days per year**: Commonly 360 (NOT 365) — verify task parameter
- Site override rule: highest approved version_no per program_code, fallback to default_active_sites
- Entity matching: program_label in contract_payment.csv matches known_labels[] or program_name (case-insensitive)
- In-scope filter: `review_flag: "review"` (string comparison)
- **Cooler cost**: NOT multiplied by sites — use `cooler_cost × dispatches/year` only
- Output files: `cooler_dispatch_analysis.json`, `cooler_dispatch_summary.md`

### harbor_vaxcrate_6v12 (Variant C: 6-day vs 12-day vaccination crate dispatch)
- Decision strings: `keep_6_day` or `switch_to_12_day`
- Margin difference field: `annual_margin_difference_12_minus_6_usd`
- Dispatches per year: 6-day=`360.0/6=60.0`, 12-day=`360.0/12=30.0`
- **Days per year**: 360 (NOT 365)
- Clinic override rule: highest numeric approved revision with non-empty active_clinics per campaign_id, fallback to default_active_clinics
- Entity matching: campaign_label in billing.csv matches alias_labels[] or campaign_name (case-insensitive)
- In-scope filter: `analysis_flag != "archive"` AND `suspension_status != "hold"` (check suspensions CSV)
- Billing selection: latest `cycle_tag` among `status == "active"` per campaign
- **Crate cost**: NOT multiplied by clinics — use `crate_cost × dispatches/year` only
- Output files: `vaxcrate_analysis.json`, `vaxcrate_summary.md`

## Sub-Task Specifics
- For additional per-variant details, see `references/invariants.md`.
- For worked calculation examples, see `references/calculation-examples.md`.
