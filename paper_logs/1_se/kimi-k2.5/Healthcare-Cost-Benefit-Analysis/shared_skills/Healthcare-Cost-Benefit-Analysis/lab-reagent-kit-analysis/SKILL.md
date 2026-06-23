---
name: lab-reagent-kit-analysis
description: Analyze laboratory reagent kit financials comparing small-kit vs bulk-kit policies for assays with different restocking frequencies. Use when task involves assay_manifest.json with regions/assays hierarchy, carrier costs by type, lab overrides with revision/status workflow, billing matched by assay aliases, and in_scope filtering. Common in pathology ops, clinical lab reagent purchasing, and assay restocking policy decisions.
---

# Lab Reagent Kit Analysis

Compare small-kit (frequent restock) vs bulk-kit (infrequent restock) policies for laboratory assays.

## Workflow

1. **Identify input files**
   - `*manifest*.json` - Hierarchical `regions` → `assays` structure
   - `*cost*.csv` - Carrier costs by `carrier_type`
   - `*billing*.csv` - Per-run payments matched by assay aliases
   - `*overrides*.csv` - Lab counts with `revision`/`status` workflow

2. **Parse manifest structure**
   ```json
   {
     "regions": [{
       "region": "central|specialty|...",
       "assays": [{
         "assay_id": "CHEM-ION",
         "assay_name": "Ion Balance Panel",
         "aliases": ["ION BAL PANEL", "Ion Panel"],
         "reagent_price_per_1000_tests_usd": 86.4,
         "carrier_type": "ambient_small|cold_chain|frozen",
         "tests_per_lab_per_run_small": 42,
         "tests_per_lab_per_run_bulk": 84,
         "default_active_labs": 12,
         "in_scope": true|false
       }]
     }]
   }
   ```

3. **Filter scope by in_scope**
   - Only include assays with `"in_scope": true`
   - Exclude `"in_scope": false` or missing flag

4. **Resolve lab overrides** (approval workflow)
   - Group by `assay_id`
   - Filter to `status: "approved"` rows only
   - Select highest `revision` among approved rows
   - Use `active_labs` from that row
   - Fall back to `default_active_labs` if no approved override
   - **Discard**: `draft`, `rejected`, `pending` rows

5. **Match billing payments using aliases**
   - Billing CSV uses `assay_label` (not `assay_id`)
   - Match case-insensitively against: `assay_name` or any string in `aliases`
   - For multiple matches, use `effective_month` ordering (latest active)

6. **Join carrier costs by carrier_type**
   - Lookup: `carrier_type` → `carrier_cost_usd`

7. **Calculate financials per assay**

   Annual reagent cost (constant across kit policies):
   ```
   annual_tests = tests_per_lab_per_run × runs_per_year × active_labs
   annual_reagent_cost = annual_tests × reagent_price_per_1000 / 1000
   ```

   Scenario calculations (small-kit A vs bulk-kit B):
   ```
   runs_per_year_small = 24  # Or task-specific
   runs_per_year_bulk = 12   # Or task-specific
   
   annual_carrier_cost_small = carrier_cost_usd × runs_per_year_small × active_labs
   annual_carrier_cost_bulk = carrier_cost_usd × runs_per_year_bulk × active_labs
   
   annual_revenue_small = payment_per_run × runs_per_year_small × active_labs
   annual_revenue_bulk = payment_per_run × runs_per_year_bulk × active_labs
   
   annual_margin_small = annual_revenue_small − annual_reagent_cost − annual_carrier_cost_small
   annual_margin_bulk = annual_revenue_bulk − annual_reagent_cost − annual_carrier_cost_bulk
   ```

8. **Aggregate and recommend**
   - Sum margins across all `in_scope` assays
   - Compare |margin_bulk − margin_small| against threshold
   - **CRITICAL: Verify recommendation enum from task schema**

## Critical Differences from Related Skills

| Aspect | Reagent Kit Analysis | Logistics Dispatch | JSON Catalog Analysis |
|--------|---------------------|-------------------|----------------------|
| Input structure | `regions` → `assays` | `service_groups` → `programs` | `service_lines` → `therapies` |
| Scope filter | `in_scope: true/false` | `review_flag: "review"` | `include_in_review: true` |
| Container matching | `carrier_type` → cost | `cooler_type` → cost | `bag_size_ml` → cost |
| Override fields | `revision`, `status` | `version_no`, `approval_state` | `revision`, `status` |
| Frequency unit | runs/year | dispatches/year | deliveries/year |
| Payment matching | `aliases` + `assay_name` | `known_labels` + `program_name` | `aliases` + `therapy_name` |

## Critical: Recommendation Enum Values

**Derive recommendation values from the task schema or explicit instructions, never invent them.**

Common patterns found in reagent kit tasks:
- `keep_small_kit` / `adopt_bulk_kit` - Common lab pattern
- `keep_X` / `switch_to_Y` - Generic pattern

**Validation rule**: Before outputting, check if the task provides:
- An explicit schema with `enum` values
- Example output showing the exact recommendation format
- Task instructions stating "recommendation must be one of: [...]"

## Anti-Patterns

- **Don't use all assays** - Only `in_scope: true` entries
- **Don't use first override row** - Must filter by `status: "approved"`, then highest `revision`
- **Don't match billing by assay_id** - Use `aliases` or `assay_name`
- **Don't assume recommendation prefix** - `adopt_bulk_kit` vs `switch_to_bulk` vs others; verify from schema
- **Don't vary reagent cost by kit policy** - Annual reagent cost is constant (same total tests); only carrier and revenue vary
- **Don't use tests_per_lab_per_run_bulk for small-kit calculations** - Each policy uses its own test count

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Lab counts wrong | Wrong revision selection or status filter | Use highest `approved` revision only |
| Payment matching fails | Looking for exact assay_id | Search `aliases` + `assay_name` |
| Too many assays in output | Ignored `in_scope` | Filter before processing |
| Recommendation rejected | Invalid enum value | Match exact strings from schema |
| Negative margins everywhere | Carrier cost lookup failed | Verify `carrier_type` exists in cost table |
| Margin difference seems wrong | Run frequency math | Verify runs_per_year values match task |

## Verification Checklist

- [ ] Only assays with `in_scope: true` are in scope
- [ ] Lab overrides: `status=approved`, highest `revision` per `assay_id`
- [ ] Payment matched using `aliases`, not just `assay_id`
- [ ] Annual reagent cost identical across scenarios (sanity check)
- [ ] `tests_per_lab_per_run_small` and `tests_per_lab_per_run_bulk` used correctly per scenario
- [ ] Recommendation enum matches task schema exactly
- [ ] All required top-level keys present: `assumptions`, `assays`, `totals`, `recommendation`
- [ ] Numeric values are JSON numbers, not strings

## References

- See `references/reagent-schemas.md` for variant manifest structures and override patterns
- See `scripts/calculate_kit_margins.py` for reference implementation