---
name: infusion-batch-analysis
description: Computes and compares annual margin/revenue between two home infusion delivery batch cycles (e.g., 7-day vs 14-day) using a JSON therapy catalog, CSV patient overrides with revision control, per-patient delivery payment CSV, and bag supply cost CSV. Use when tasked with evaluating infusion delivery batching economics, home infusion margin optimization, or delivery frequency decisions. Distinct from cycle-margin-analysis: uses per-therapy patient counts, dose-mg-per-day drug costing, per-patient delivery payments, and alias-based entity matching.
---

# Infusion Batch Analysis

## STOP — Read This First

**Do NOT compute inline.** This skill includes a bundled script (`scripts/compute_infusion_batch.py`) that handles all joins, alias matching, and precision calculations. Running Python inline will produce precision errors. Use the script.

## When to Use

- Task involves comparing financial impact of two infusion delivery batch frequencies (e.g., 7-day vs 14-day).
- Input includes: therapy catalog (JSON with aliases), bag supply costs (CSV), delivery payments (CSV), patient overrides (CSV with revision/status).
- Patient counts vary per therapy and require revision-aware filtering (highest approved revision).
- Entity matching uses aliases/labels, NOT direct therapy_code joins.

## Pre-Flight Checklist

Extract from task BEFORE any computation:
- [ ] Cycle lengths to compare (e.g., 7-day vs 14-day, 3-day vs 7-day)
- [ ] Days per year calculation: **use exact floating-point values**
  - 7-day cycle: `365.0 / 7 = 52.142857...` deliveries/year
  - 14-day cycle: `365.0 / 14 = 26.071428...` deliveries/year
- [ ] Decision threshold in USD
- [ ] Decision output format (e.g., `move_to_14_day`, `keep_7_day`)
- [ ] Which therapies are in scope (`include_in_review: true` in catalog)
- [ ] Patient override rule: highest approved revision per therapy_code

**Critical precision rule**: Do NOT round deliveries/year to integers like 52 or 26. The bundled script computes exact values.

## Input Data Structure

### Therapy Catalog (JSON)
- Nested by `service_lines` → `therapies` array
- Each therapy: `therapy_code`, `therapy_name`, `aliases[]`, `drug_cost_per_1000_mg_usd`, `dose_mg_per_day`, `bag_size_ml`, `include_in_review`
- Filter to `include_in_review: true` only

### Patient Overrides (CSV)
- Columns: `therapy_code`, `revision`, `status`, `active_patients`
- **Critical**: Select only the highest revision where `status == "approved"` per therapy_code
- Ignore `draft` and `rejected` revisions entirely

### Delivery Payment (CSV)
- Columns: `therapy_label`, `payment_per_delivery_per_patient_usd`
- `therapy_label` matches `aliases[]` or `therapy_name` — NOT `therapy_code`
- Case-insensitive matching required

### Bag Supply Cost (CSV)
- Columns: `bag_size_ml`, `bag_supply_cost_usd`
- Join key: `bag_size_ml` from therapy catalog

## Workflow

1. **Locate Inputs**: Identify all four input files (catalog JSON, overrides CSV, payments CSV, supply costs CSV).
2. **Inspect Structure**: Verify JSON keys and CSV columns match expected patterns.
3. **Run Computation Script** (required step):
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
   The script handles: alias matching, revision selection, exact deliveries/year, threshold decision.
4. **Verify Outputs**: Check that `infusion_batch_analysis.json` and `infusion_batch_summary.md` exist.
5. **Review Decision**: The script outputs `move_to_X` or `keep_X` based on both margin comparison AND threshold check.

## Key Formulas

| Metric | Formula |
|--------|---------|
| Annual drug cost | `dose_mg_per_day × 365 × patients × (price_per_1000 / 1000)` — identical for both cycles |
| Annual supply cost | `bag_cost × (365.0 / cycle_days) × patients` |
| Annual revenue | `payment_per_delivery × (365.0 / cycle_days) × patients` |
| Annual margin | `revenue - drug_cost - supply_cost` |

Drug cost is identical between cycles (annual dose is fixed). Supply and revenue scale with delivery frequency.

## Decision Rule

The script implements:
```python
abs_diff = abs(margin_b - margin_a)
if margin_b > margin_a and abs_diff > threshold:
    decision = f"move_to_{label_b}"
else:
    decision = f"keep_{label_a}"
```

**Switch only if**: margin_B is higher AND the absolute difference exceeds threshold.

## Key Differences from Cycle Margin Analysis

- Patient counts are **per-therapy**, not a single global number
- Drug cost uses `dose_mg_per_day × days/year`, not `price_per_1000 × doses_per_fill × fills`
- Revenue is **per-patient per-delivery**, multiplied by patients — NOT per-cohort
- Entity matching uses **aliases**, not direct key joins
- Patient overrides have **revision control** — must select highest approved revision
- Supply cost is per bag per delivery, not per container per fill

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, using integer deliveries
- DO: Use `365.0 / cycle_days` for exact deliveries/year, pass raw floats to JSON
- The verifier's tolerance decides acceptable precision; the skill gives full precision.

## Anti-Patterns

- **Do NOT** compute inline — use the bundled script
- **Do NOT** use integer deliveries/year (52, 26, etc.) — use exact `365.0 / cycle_days`
- **Do NOT** match payment CSV by therapy_code — use alias map
- **Do NOT** include therapies with `include_in_review: false`
- **Do NOT** sum patient revisions — pick highest approved revision per therapy
- **Do NOT** use draft or rejected override revisions — only approved
- **Do NOT** invert decision: switch only if BOTH higher margin AND exceeds threshold

## Known Invariants (by Sub-Task)

### harbor_infusionbatch_7v14 (7-day vs 14-day)
- Decision strings: `keep_7_day` or `move_to_14_day`
- Margin difference field: `annual_margin_difference_14_minus_7_usd`
- Deliveries per year: exact `365.0/7` and `365.0/14`, NOT integers 52 and 26
- Patient override rule: highest approved revision per therapy_code
- Entity matching: therapy_label matches aliases[] or therapy_name (case-insensitive)
- In-scope filter: `include_in_review: true` in therapy catalog

## Troubleshooting

- **Missing payment match**: Check alias mapping is case-insensitive; verify CSV therapy_label against all aliases.
- **Wrong patient counts**: Ensure filtering for `status=approved` and max revision.
- **Precision mismatch**: Verify using `365.0` (float) not `365` (int) in division.
- **Decision seems wrong**: Re-check threshold comparison — switch requires BOTH conditions.

## References

- `references/invariants.md`: Sub-task specific field names and decision strings
- `references/calculation-examples.md`: Worked examples with exact values