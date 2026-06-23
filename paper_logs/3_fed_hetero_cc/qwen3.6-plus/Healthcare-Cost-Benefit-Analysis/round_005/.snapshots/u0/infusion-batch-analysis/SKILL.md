---
name: infusion-batch-analysis
description: Computes and compares annual margin/revenue between two home infusion delivery batch cycles (e.g., 7-day vs 14-day) using a JSON therapy catalog, CSV patient overrides with revision control, per-patient delivery payment CSV, and bag supply cost CSV. Use when tasked with evaluating infusion delivery batching economics, home infusion margin optimization, or delivery frequency decisions. Distinct from cycle-margin-analysis: uses per-therapy patient counts, dose-mg-per-day drug costing, per-patient delivery payments, and alias-based entity matching.
---

# Infusion Batch Analysis

## When to Use
- Task involves comparing financial impact of two infusion delivery batch frequencies (e.g., 7-day vs 14-day).
- Input includes a JSON therapy catalog with dose rates, CSV patient overrides with revision/status, per-patient delivery payment CSV, and bag supply cost CSV.
- Output requires JSON breakdown and Markdown summary with a move/keep decision against a threshold.

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

## Key Formulas

| Metric | Formula |
|--------|---------|
| Annual drug cost | `dose_mg_per_day × 365 × patients × (price_per_1000 / 1000)` |
| Annual supply cost | `bag_cost_usd × (365.0 / cycle_days) × patients` |
| Annual revenue | `payment_per_delivery × (365.0 / cycle_days) × patients` |
| Annual margin | `revenue - drug_cost - supply_cost` |

**Note**: Drug cost is identical between cycles (annual dose fixed). Supply and revenue scale with delivery frequency.

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

## Troubleshooting
- **Missing payment match**: Check alias mapping is case-insensitive; verify CSV therapy_label against all aliases.
- **Wrong patient counts**: Ensure filtering for `status=approved` and max revision, not just latest row.
- **Precision mismatch**: Verify using `365.0` (float) not `365` (int) in division.
- **Negative margins**: Expected in infusion models; focus on difference between cycles.
- **Decision seems wrong**: Re-check threshold comparison — switch only if BOTH conditions met.

## Reference Files
- `references/invariants.md`: Sub-task specific field names and decision strings.
- `references/calculation-examples.md`: Worked examples with exact precision.
