---
name: dispatch-cycle-analysis
description: Computes and compares annual margin/revenue between two dispatch/delivery cycle frequencies (e.g., 6-day vs 12-day, 7-day vs 14-day) for field operations like vaccination outreach, home infusion, or cooler dispatch. Use when tasked with evaluating dispatch consolidation economics, delivery frequency optimization, or batch cycle decisions. Requires JSON entity catalog with aliases, CSV overrides with revision control, CSV billing with active/latest selection, and CSV supply costs. Distinct from cycle-margin-analysis: uses per-entity site/clinic counts, dose-per-day drug costing, and dispatch-based (not fill-based) frequency.
---

# Dispatch Cycle Analysis

## STOP — Read This First

**Do NOT compute inline.** This skill includes a bundled script (`scripts/compute_dispatch_cycle.py`) that handles all joins, alias matching, revision logic, billing selection, and precision calculations. Running Python inline will produce errors. Use the script.

## When to Use

- Task requires comparing financial impact of two dispatch/delivery cycle frequencies.
- Input includes: JSON catalog (campaigns/therapies/programs), CSV overrides with revision/status, CSV billing with effective date/cycle tags, CSV supply costs.
- Entity matching uses aliases/labels against billing records, not direct code joins.
- Per-entity counts (clinics/sites/patients) vary and require revision-aware filtering.
- Output requires JSON breakdown and Markdown summary with keep/switch decision against threshold.

## Pre-Flight Checklist

Extract from task BEFORE computation:
- [ ] Cycle days to compare (e.g., 6 vs 12, 7 vs 14, 3 vs 7)
- [ ] Days per year for calculations (commonly 365, but verify — B4 cooler dispatch uses 360)
- [ ] Dispatches per year = `days_per_year / cycle_days` (use exact float, NOT integer)
- [ ] Decision threshold in USD
- [ ] Decision output format (e.g., `keep_6_day`, `move_to_14_day`, `switch_to_12_day`)
- [ ] In-scope filter criteria (e.g., `analysis_flag == "review"`, `include_in_review: true`)
- [ ] Suspension/exclusion rule (e.g., `suspension_status != "hold"`)
- [ ] Override rule: highest approved revision per entity, fallback to default count
- [ ] Billing rule: latest active record per entity (match aliases, not codes)

**Critical precision rule**: Do NOT round dispatches/year to integers. Use exact `days_per_year / cycle_days` as float.

## Input Data Patterns

### Catalog (JSON)
Nested structure with entity arrays. Common patterns:
- `regions` → `campaigns[]` or `service_lines` → `therapies[]` or `service_groups` → `programs[]`
- Per-entity: `doses_per_day` or `dose_mg_per_day` or `units_per_day`
- `alias_labels[]` or `aliases[]` or `known_labels[]` for billing matching
- `default_active_clinics` or `default_active_sites` or `default_active_patients`
- In-scope flag: `analysis_flag`, `include_in_review`, or `review_flag`
- Supply key: `crate_tier`, `bag_size_ml`, `cooler_type`

### Overrides (CSV)
- Columns typically: entity_id, revision/version, status/approval_state, active_clinics/sites
- **Critical**: Select highest revision where status == "approved" per entity
- Fallback to catalog default if no approved override
- Ignore draft, rejected, or blank-revision rows

### Billing (CSV)
- Columns typically: label/therapy_label/campaign_label, status/is_active, cycle_tag/effective_month, payment_per_dispatch_per_clinic_usd
- **Critical matching**: Match label against `alias_labels[]` or entity name (case-insensitive or exact per variant)
- **Critical selection**: Among active records, pick latest cycle_tag/effective_month (descending sort)
- Do NOT sum multiple billing records; pick single latest active one

### Supply Costs (CSV)
- Columns: supply_key (crate_tier/bag_size_ml/cooler_type), cost_usd
- Join to catalog by supply key

## Workflow

1. **Locate Inputs**: Identify all four input files (catalog JSON, overrides CSV, billing CSV, supply CSV).
2. **Inspect Structure**: Verify JSON nesting and CSV columns match expected patterns.
3. **Determine Variant**: Check `references/variant-mappings.md` for field name mappings specific to your task.
4. **Run Computation Script**:
   ```bash
   python3 scripts/compute_dispatch_cycle.py \
     --catalog campaign_manifest.json \
     --overrides location_overrides.csv \
     --billing billing.csv \
     --supply crate_cost.csv \
     --cycle-a 6 --cycle-b 12 \
     --days-per-year 365 \
     --threshold 11000 \
     --output-dir .
   ```
   Common args:
   - `--entity-col`: campaign_id, therapy_code, program_code (default: auto-detect)
   - `--name-col`: campaign_name, therapy_name, program_name
   - `--alias-col`: alias_labels, aliases, known_labels
   - `--scope-flag`: analysis_flag, include_in_review, review_flag
   - `--scope-value`: "review", true, "review"
   - `--suspension-csv`: path to suspensions CSV (optional)
   - `--suspension-status`: status to exclude, e.g., "hold"
5. **Verify Outputs**: Check that `<prefix>_analysis.json` and `<prefix>_summary.md` exist.
6. **Review Decision**: Script outputs keep/switch/move decision based on margin comparison AND threshold check.

## Key Formulas

| Metric | Formula |
|--------|---------|
| Dispatches/year | `days_per_year / cycle_days` (exact float) |
| Annual drug cost | `doses_per_day × days_per_year × clinics × (price_per_1000 / 1000)` — identical for both cycles |
| Annual supply cost | `supply_cost × dispatches/year × clinics` — scales with dispatch frequency |
| Annual revenue | `payment_per_dispatch × dispatches/year × clinics` |
| Annual margin | `revenue - drug_cost - supply_cost` |

Drug cost is identical between cycles (annual dose is fixed). Supply and revenue scale with dispatch frequency.

## Decision Rule

Switch only if BOTH conditions met:
1. `margin_B > margin_A`
2. `|margin_B - margin_A| > threshold`

## Key Differences from Related Skills

| Aspect | Cycle Margin | Infusion Batch | Reagent Kit | Dispatch Cycle (this) |
|--------|-----------|----------------|-------------|----------------------|
| Entity | medication | therapy | assay | campaign/therapy/program |
| Count type | patients (global) | patients (per-therapy) | labs (per-assay) | clinics/sites (per-entity) |
| Cost basis | doses per fill | dose mg per day | tests per run | doses per day |
| Frequency | fills per year | deliveries per year | runs per year | dispatches per year |
| Supply | packaging per container | bags per delivery | carrier per run | crate/bag/cooler per dispatch |
| Revenue | per-fill for N patients | per-delivery per patient | per-run per lab | per-dispatch per clinic |
| Billing | single CSV | alias match | alias + effective_month | alias + latest cycle_tag |
| Exclusions | — | — | — | suspension_status, analysis_flag |

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (JSON). Pass raw float values directly. Use exact `days_per_year / cycle_days` for dispatches/year. The verifier's tolerance decides acceptable precision.

## Anti-Patterns

- **Do NOT** compute inline — use the bundled script
- **Do NOT** use integer dispatches/year — use exact float division
- **Do NOT** match billing by entity_id — use alias matching
- **Do NOT** sum multiple billing records — pick latest active only
- **Do NOT** include entities with wrong analysis_flag or hold suspension
- **Do NOT** sum override revisions — pick highest approved per entity
- **Do NOT** use draft/rejected override revisions
- **Do NOT** forget suspension exclusion check (e.g., VAX-ZETA with "hold")
- **Do NOT** assume 365 days — verify task spec (cooler dispatch uses 360)

## Troubleshooting

- **Missing billing match**: Check alias list includes billing CSV labels; verify case sensitivity per variant.
- **Wrong clinic counts**: Ensure filtering for approved status and max revision; check fallback to default.
- **Precision mismatch**: Verify using `365.0 / cycle_days` not `365 // cycle_days`.
- **Excluded campaigns appearing**: Double-check suspension filter and analysis_flag filter.
- **Decision seems wrong**: Re-check threshold comparison — switch requires BOTH conditions.

## References

- `references/variant-mappings.md`: Sub-task specific field names, decision strings, and formula differences (B3 infusion, B4 cooler, B5 reagent, B6 vaxcrate, etc.)