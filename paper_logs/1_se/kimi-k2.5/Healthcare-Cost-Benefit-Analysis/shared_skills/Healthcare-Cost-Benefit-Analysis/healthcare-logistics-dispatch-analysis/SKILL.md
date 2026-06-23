---
name: healthcare-logistics-dispatch-analysis
description: Analyze healthcare logistics program financials comparing dispatch frequency scenarios for programs requiring cold chain or specialized shipping containers. Use when task involves program_catalog.json with service_groups structure, cooler/container costs by type, site overrides with approval workflow, payment matching via known_labels/aliases, review_flag-based scope filtering, and optional suspensions exclusions. Common in oncology cooler programs, specialty pharmacy cold chain logistics, vaccination campaigns, and clinical supply dispatch operations. Handles suspension exclusions, empty override values, and variable recommendation enums.
---

# Healthcare Logistics Dispatch Analysis

Compare dispatch frequency scenarios for healthcare programs requiring specialized logistics (coolers, cold chain containers, vaccine crates).

## Workflow

1. **Identify all input files** - Look for these patterns:
   - `*catalog*.json` - Hierarchical `service_groups` → `programs`/`campaigns` structure
   - `*cost*.csv` - Cooler/container/crate costs by type
   - `*payment*.csv` / `*billing*.csv` - Per-dispatch payments matched by program labels
   - `*overrides*.csv` / `*location_overrides*.csv` - Site/clinic counts with version/revision workflow
   - `*suspensions*.csv` **optional** - Campaigns to exclude (e.g., `suspension_status: hold`)

2. **Parse catalog structure**
   ```json
   {
     "service_groups": [{
       "group_name": "antiemetic|supportive|...",
       "programs": [{
         "program_code": "ONC-ALFA",
         "program_name": "AlfaEase",
         "known_labels": ["ALFA EASE", "Alfa-Ease"],
         "acquisition_cost_per_1000_units_usd": 58.4,
         "units_per_day": 64,
         "cooler_type": "small_cold|large_cold|portable|secure",
         "default_active_sites": 14,
         "analysis_flag": "review|archive"
       }]
     }]
   }
   ```

3. **Apply scope filters** (in order):
   - **Suspension exclusion**: If `suspensions.csv` present, exclude any `program_code` with `suspension_status: "hold"`
   - **Review flag**: Only include programs with `"analysis_flag": "review"` (or `"review_flag": "review"`)
   - **Exclude**: `"archive"`, `"deprecated"`, or suspended entries

4. **Resolve site overrides** (approval workflow)
   - Group by `program_code`
   - Filter to `approval_state: "approved"` (or `status: "approved"`) rows only
   - Select highest `version_no`/`revision` among approved rows
   - Use `active_sites`/`active_clinics` from that row
   - **CRITICAL**: Handle empty values - if `active_sites` is blank/null, fall back to `default_active_sites`
   - Fall back to `default_active_sites` if no approved override exists
   - **Discard**: `draft`, `rejected`, `pending` rows

5. **Match payments using known_labels/aliases**
   - Payment/billing CSV uses `program_label`/`campaign_label` (not program_code)
   - Match case-insensitively against: `program_name`/`campaign_name` or any string in `known_labels`/`alias_labels`
   - For multiple active entries, use latest `effective_month`/`cycle_tag` (if present) or highest payment
   - Normalize whitespace: `"ALFA EASE"` matches `"Alfa-Ease"`

6. **Join container costs by type**
   - Lookup: `cooler_type`/`crate_tier` → container cost

7. **Calculate financials per program**

   Annual drug cost (constant across dispatch frequencies):
   ```
   annual_units = units_per_day × 365 × active_sites
   annual_drug_cost = annual_units × acquisition_cost_per_1000_units_usd / 1000
   ```

   Scenario calculations (dispatch frequency A vs B):
   ```
   dispatches_per_year_A = 365 / days_per_dispatch_A
   dispatches_per_year_B = 365 / days_per_dispatch_B
   
   annual_container_cost_A = container_cost_usd × dispatches_per_year_A × active_sites
   annual_container_cost_B = container_cost_usd × dispatches_per_year_B × active_sites
   
   annual_revenue_A = payment_per_dispatch × dispatches_per_year_A × active_sites
   annual_revenue_B = payment_per_dispatch × dispatches_per_year_B × active_sites
   
   annual_margin_A = annual_revenue_A − annual_drug_cost − annual_container_cost_A
   annual_margin_B = annual_revenue_B − annual_drug_cost − annual_container_cost_B
   ```

8. **Aggregate and recommend**
   - Sum margins across all in-scope programs
   - Compare |margin_B − margin_A| against threshold
   - **CRITICAL: Verify recommendation enum from task schema**

## Critical: Recommendation Enum Values

**Derive recommendation values from the task schema or explicit instructions, never invent them.**

Common patterns found in logistics tasks:
- `keep_X_day` / `switch_to_Y_day` - Most common
- `keep_X_day_dispatch` / `switch_to_Y_day_dispatch` - Variant with suffix
- `move_to_Y_day` - Home infusion pattern (verify before using)
- `keep_X` / `adopt_Y` - Lab/policy variants

**Validation rule**: Before outputting, check if the task provides:
- An explicit schema with `enum` values
- Example output showing the exact recommendation format
- Task instructions stating "recommendation must be one of: [...]"

**When unsure**: Prefer `switch_to_{scenario}` over `move_to_{scenario}` unless task explicitly specifies.

## Critical Differences from Related Skills

| Aspect | Logistics Dispatch | JSON Catalog Analysis | CSV Financial |
|--------|-------------------|----------------------|---------------|
| Input structure | `service_groups` → `programs`/`campaigns` | `service_lines` → `therapies` | Flat CSV files |
| Scope filter | `analysis_flag: "review"` + suspensions | `include_in_review: true` | Usually all rows |
| Container matching | `cooler_type`/`crate_tier` → cost | `bag_size_ml` → cost | `canister_size` or `mailer_format` |
| Frequency unit | dispatches/year | deliveries/year | fills/year |
| Payment matching | `known_labels`/`alias_labels` | `aliases` + `therapy_name` | Direct column match |
| Override fields | `version_no`/`revision`, `approval_state`/`status` | `revision`, `status` | Usually none |
| Suspension exclusion | Yes (from suspensions.csv) | No | No |

## Anti-Patterns

- **Don't use all programs** - Filter by `analysis_flag: "review"` AND exclude suspended campaigns
- **Don't use first override row** - Must filter by `approval_state: "approved"`, then highest `version_no`
- **Don't ignore empty override values** - If `active_sites` is blank, use `default_active_sites`
- **Don't match payments by program_code** - Use `known_labels` or `program_name`
- **Don't assume recommendation prefix** - `move_to` vs `switch_to` vs `adopt`; verify from schema
- **Don't vary drug cost by dispatch frequency** - Annual drug cost is constant; only logistics costs vary
- **Don't round dispatch counts early** - Use exact values (365/10=36.5→36 or 37 depending on task)
- **Don't forget suspensions.csv** - Check for suspension exclusions if file exists

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Site counts wrong | Wrong version selection or state filter | Use highest `approved` version only; check for empty values |
| Payment matching fails | Looking for exact program_code | Search `known_labels`/`alias_labels` + `program_name` |
| Too many programs in output | Ignored `analysis_flag` or suspensions | Filter by review flag AND exclude suspended campaigns |
| Recommendation rejected | Invalid enum value | Match exact strings from schema - `switch_to` not `move_to` |
| Negative margins everywhere | Container cost lookup failed | Verify `cooler_type`/`crate_tier` exists in cost table |
| Margin difference wrong | Dispatch frequency math | Verify 365/days_per_dispatch rounding; check fill counts |
| Missing campaign in output | Suspension hold not excluded | Check suspensions.csv for `suspension_status: hold` |

## Verification Checklist

Before declaring task complete:
- [ ] Suspension exclusions applied (if suspensions.csv exists)
- [ ] Only programs with `analysis_flag: "review"` are in scope
- [ ] Site overrides: `approval_state=approved`, highest `version_no` per program_code
- [ ] Empty override values fall back to `default_active_sites`
- [ ] Payment matched using `known_labels`/`alias_labels`, not just `program_code`
- [ ] Annual drug cost identical across scenarios (sanity check)
- [ ] Recommendation enum matches task schema exactly (`switch_to` vs `move_to` vs `adopt`)
- [ ] All 4 required top-level keys present: `assumptions`, `programs`/`campaigns`, `totals`, `recommendation`
- [ ] Numeric values are JSON numbers, not strings

## References

- See `references/dispatch-schemas.md` for variant catalog structures, override patterns, and suspension handling
- See `scripts/calculate_dispatch_margins.py` for reference implementation