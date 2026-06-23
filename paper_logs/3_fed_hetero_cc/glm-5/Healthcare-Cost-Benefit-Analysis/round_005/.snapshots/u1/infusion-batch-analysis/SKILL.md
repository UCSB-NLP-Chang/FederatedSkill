---
name: infusion-batch-analysis
description: Computes and compares annual margin/revenue between two home infusion delivery batch cycles (e.g., 7-day vs 14-day) using a JSON therapy catalog, CSV patient overrides with revision control, per-patient delivery payment CSV, and bag supply cost CSV. Use when tasked with evaluating infusion delivery batching economics, home infusion margin optimization, or delivery frequency decisions. Distinct from cycle-margin-analysis: uses per-therapy patient counts, dose-mg-per-day drug costing, per-patient delivery payments, and alias-based entity matching.
---

# Infusion Batch Analysis

## When to Use
- Task involves comparing financial impact of two infusion delivery batch frequencies (e.g., 7-day vs 14-day).
- Input includes a JSON therapy catalog with dose rates, CSV patient overrides with revision/status, per-patient delivery payment CSV, and bag supply cost CSV.
- Output requires JSON breakdown and Markdown summary with a move/keep decision against a threshold.
- **Not for pharmacy refill cycles** — use `cycle-margin-analysis` skill when drug costs are per-fill, patient counts are global, and inputs are CSV-only.

## Pre-Flight Checklist
- [ ] Delivery frequencies and cycle days (e.g., 7-day, 14-day, 3-day, 21-day)
- [ ] **Critical precision rule**: Use EXACT `365.0 / cycle_days` for deliveries/year — never round to integers
- [ ] Decision threshold in USD
- [ ] Decision output string format (e.g., `keep_7_day` vs `move_to_14_day`)
- [ ] Which therapies are in scope (`include_in_review` flag in catalog)
- [ ] Patient override selection rule: highest approved revision per therapy_code

**Critical precision rule**: Do NOT round deliveries/year to integers like `52` or `26`. Always use `365.0 / cycle_days`:
- 7-day cycle: `365.0 / 7 = 52.142857...` deliveries/year
- 14-day cycle: `365.0 / 14 = 26.071428...` deliveries/year
- 3-day cycle: `365.0 / 3 = 121.666...` deliveries/year

## Input Data Structure

### Therapy Catalog (JSON)
- Nested by `service_lines` → `therapies` array
- Each therapy has: `therapy_code`, `therapy_name`, `aliases[]`, `drug_cost_per_1000_mg_usd`, `dose_mg_per_day`, `bag_size_ml`, `include_in_review`
- Filter to `include_in_review: true` only

### Patient Overrides (CSV)
- Columns: `therapy_code`, `revision`, `status`, `active_patients`
- **Critical**: Select only the highest revision where `status == "approved"` per therapy_code
- Ignore `draft` and `rejected` revisions entirely
- If no approved revision exists for an in-scope therapy, exclude it or escalate

### Delivery Payment (CSV)
- Columns: `therapy_label`, `payment_per_delivery_per_patient_usd`
- `therapy_label` matches `aliases[]` or `therapy_name` from catalog — NOT `therapy_code`
- Must resolve alias matching (case-insensitive, strip hyphens/spaces)

### Bag Supply Cost (CSV)
- Columns: `bag_size_ml`, `bag_supply_cost_usd`
- Join key: `bag_size_ml` from therapy catalog

## Workflow
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

## Key Formulas (with units)

| Metric | Formula |
|--------|---------|
| Annual drug cost | `dose_mg_per_day × 365 × patients × (price_per_1000 / 1000)` |
| Annual supply cost | `bag_cost_usd × (365.0 / cycle_days) × patients` |
| Annual revenue | `payment_per_delivery × (365.0 / cycle_days) × patients` |
| Annual margin | `revenue - drug_cost - supply_cost` |

**Note**: Drug cost is identical between cycles (annual dose fixed). Supply and revenue scale with delivery frequency.

## Decision Rule

If `margin_B > margin_A` AND `|margin_B - margin_A| > threshold`: choose B (`move_to_B`).
Otherwise: keep A (`keep_A`).

**Common mistake**: Inverting the decision — if the better model's advantage is BELOW threshold, keep the current model.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, CSV, Excel). Pass raw float values directly. Let the verifier's
tolerance decide acceptable precision.

## Key Differences from Cycle Margin Analysis
- **Patient counts are per-therapy**, not a single global number
- **Drug cost uses dose_mg_per_day × 365**, not price_per_1000 × doses_per_fill × fills
- **Revenue is per-patient per-delivery**, multiplied by patients — NOT per-cohort
- **Entity matching uses aliases**, not direct key joins
- **Patient overrides have revision control** — must select highest approved revision
- **Supply cost is per bag per delivery**, not per container per fill
- **Deliveries/year uses exact division `365.0/cycle_days`**, not integer approximations

## Anti-Patterns
- Do NOT use draft or rejected patient override revisions — only approved.
- Do NOT assume therapy_label matches therapy_code — use aliases for matching.
- Do NOT use a single global patient count — each therapy has its own count from overrides.
- Do NOT multiply delivery payment by patient count twice — it's per-patient, so multiply by patients once.
- Do NOT assume drug costs differ between batch models when treatment days per year are equal.
- Do NOT invert the decision: if the better model's advantage is BELOW threshold, keep the current model.
- Do NOT forget to filter by `include_in_review: true` — some therapies are explicitly excluded.
- Do NOT assume the highest revision number is automatically approved — check status field.
- Do NOT use integer deliveries/year (`52`, `26`) — always use `365.0 / cycle_days`.
- Avoid inline Python for this calculation; use the bundled script to prevent join and alias-matching errors.

## Troubleshooting
- **Alias matching failures**: Normalize both sides (lowercase, strip hyphens, collapse whitespace). Build a lookup from all aliases + therapy_name.
- **Missing approved revision**: If a therapy has no approved override row, flag it — do not assume zero patients.
- **Multiple approved revisions for same therapy**: Take the one with the highest revision number.
- **Negative margins**: Expected in infusion models; focus on the difference between models.
- **Decision seems wrong**: Re-check the threshold comparison logic — switch only if the alternative is BOTH better AND exceeds threshold.
- **Precision mismatch**: Verify using `365.0` (float) not `365` (int) in division.

## Sub-Task Specifics
- For per-variant decision strings and field name patterns, see `references/invariants.md`.
- For worked calculation examples, see `references/calculation-examples.md`.
