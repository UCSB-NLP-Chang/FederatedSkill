---
name: healthcare-json-catalog-analysis
description: Analyze healthcare therapy/medication financials from hierarchical JSON catalogs with patient overrides, alias matching, and supply cost lookups. Use when task involves therapy_catalog.json with service_line/therapies hierarchy, patient_overrides.csv with revision/approval status filtering, bag_supply_cost.csv lookups by size, and delivery_payment.csv matched by therapy aliases. Handles home infusion, specialty pharmacy, and clinical program batching analyses with non-standard recommendation enums like 'move_to_X_day'.
---

# Healthcare JSON Catalog Analysis

Analyze therapy financials from hierarchical JSON catalogs with complex patient override rules.

## Workflow

1. **Identify input files** - Look for these patterns:
   - `*catalog*.json` - Hierarchical service_line → therapies structure
   - `*overrides*.csv` - Patient counts with revision/status workflow
   - `*supply*cost*.csv` - Supply/bag costs by size
   - `*payment*.csv` - Per-delivery payments (may use aliases)

2. **Parse JSON catalog structure**
   ```json
   {
     "service_lines": [{
       "service_line": "pulmonary|immunology|...",
       "therapies": [{
         "therapy_code": "HINF-ALPHA",
         "therapy_name": "AlphaNeb",
         "aliases": ["ALPHA-NEB", "Alpha Neb"],
         "drug_cost_per_1000_mg_usd": 42.4,
         "dose_mg_per_day": 52,
         "bag_size_ml": 250,
         "include_in_review": true|false
       }]
     }]
   }
   ```
   **Critical**: Filter by `include_in_review: true` to determine scope

3. **Resolve patient overrides** - Complex approval workflow:
   - Group by `therapy_code`
   - For each therapy_code, find rows with `status: approved`
   - Select `highest revision` number among approved rows
   - Use that row's `active_patients` value
   - **Discard**: `draft`, `rejected`, or lower revision approved rows

4. **Match payments using aliases**
   - Payment CSV uses `therapy_label` (not therapy_code)
   - Match against: `therapy_name`, `therapy_code`, or any string in `aliases`
   - Case-insensitive matching often required

5. **Join supply costs by bag_size_ml**
   - Lookup: `bag_size_ml` → `bag_supply_cost_usd`

6. **Calculate financials per therapy**

   Annual drug cost (constant across scenarios):
   ```
   annual_doses_mg = dose_mg_per_day × 365 × active_patients
   annual_drug_cost = annual_doses_mg × drug_cost_per_1000_mg_usd / 1000
   ```

   Scenario calculations (delivery frequency A vs B):
   ```
   deliveries_per_year_A = 365 / days_per_delivery_A  (typically 52 for 7-day)
   deliveries_per_year_B = 365 / days_per_delivery_B  (typically 26 for 14-day)
   
   annual_supply_cost_A = bag_supply_cost_usd × deliveries_per_year_A × active_patients
   annual_supply_cost_B = bag_supply_cost_usd × deliveries_per_year_B × active_patients
   
   annual_revenue_A = payment_per_delivery × deliveries_per_year_A × active_patients
   annual_revenue_B = payment_per_delivery × deliveries_per_year_B × active_patients
   
   annual_margin_A = annual_revenue_A − annual_drug_cost − annual_supply_cost_A
   annual_margin_B = annual_revenue_B − annual_drug_cost − annual_supply_cost_B
   ```

7. **Aggregate and recommend**
   - Sum margins across all `include_in_review: true` therapies
   - Compare |margin_B − margin_A| against threshold
   - **Recommendation enum**: VERIFY exact format from task
     - Common: `keep_X_day`, `switch_to_Y_day`
     - **Also seen**: `move_to_Y_day` (home infusion pattern)

## Critical Differences from CSV Financial Analysis

| Aspect | JSON Catalog | CSV Standard |
|--------|-------------|--------------|
| Input format | Hierarchical JSON + CSV overrides | Flat CSV files |
| Patient counts | Override logic with status/revision | Fixed or simple lookup |
| Therapy matching | `therapy_code` with alias fallbacks | Direct column match |
| Scope filtering | `include_in_review: true` | Usually all rows |
| Recommendation | May use `move_to_X` not `switch_to_X` | Usually `switch_to_X` |

## Anti-Patterns

- **Don't use all therapies** - Only `include_in_review: true` entries
- **Don't use first override row** - Must filter by `status: approved`, then highest `revision`
- **Don't match payments by therapy_code** - Use aliases or therapy_name; payment CSV uses different labels
- **Don't assume standard enums** - `move_to_14_day` ≠ `switch_to_14_day`; verify task-specific schema
- **Don't forget drug cost is constant** - Same across scenarios; only supply and revenue vary

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Patient counts wrong | Wrong revision selection or status filter | Use highest `approved` revision only |
| Payment matching fails | Looking for exact therapy_code | Search aliases array + therapy_name |
| Too many therapies in output | Ignored `include_in_review` | Filter before processing |
| Recommendation rejected | Used `switch_to` instead of `move_to` | Check task schema for exact enum |
| Negative margins everywhere | Supply cost lookup failed | Verify bag_size_ml exists in supply table |

## Verification Checklist

- [ ] Only therapies with `include_in_review: true` are in scope
- [ ] Patient overrides: `status=approved`, highest `revision` per therapy_code
- [ ] Payment matched using `aliases` or `therapy_name`, not just `therapy_code`
- [ ] Annual drug cost identical across scenarios (sanity check)
- [ ] Recommendation enum matches task schema exactly (`move_to` vs `switch_to`)
- [ ] All 4 required top-level keys present: `assumptions`, `therapies`, `totals`, `recommendation`

## References

- See `references/json-catalog-schemas.md` for variant catalog structures
- See `references/override-patterns.md` for complex patient count workflows
- See `scripts/resolve_patients.py` for reference override implementation