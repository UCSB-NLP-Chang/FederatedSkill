---
name: reagent-kit-analysis
description: Computes and compares annual margin between two reagent/test policy cycles (e.g., small-kit vs bulk-kit, 14-day vs 28-day dispatch) for diagnostic assays or panels. Use when tasked with evaluating lab supply chain economics, diagnostic network optimization, or replenishment cadence decisions involving assay/panel manifests, lab overrides with revision control, billing records with effective dates, and carrier/shipper costs. Covers two variants: (1) Reagent Kit: fixed runs/year, effective_month billing, carrier costs; (2) Panel Dispatch: variable cycle days, effective_week billing, shipper costs, network adjustments, holdouts.
---

# Reagent Kit Policy Analysis

## When to Use

This skill covers two related workflow variants:

### Variant 1: Reagent Kit Policy (B5)
- Task requires comparing financial impact of small-kit (e.g., 24 runs/year) vs bulk-kit (e.g., 12 runs/year) reagent policies.
- Input includes: JSON assay manifest with in-scope flags and aliases, CSV lab overrides with revision/status, CSV billing records with effective_month and is_active flags, CSV carrier costs.
- Entity matching uses aliases against billing labels, not direct code joins.
- Output requires JSON breakdown and Markdown summary with adopt/keep decision against threshold.

### Variant 2: Panel Dispatch Policy (B7)
- Task requires comparing financial impact of two diagnostic panel dispatch cycles (e.g., 14-day vs 28-day).
- Input includes: JSON panel manifest with analysis_mode flags and aliases, CSV lab overrides with rev/approval, CSV contract terms with effective_week and status_flag, CSV network adjustments by tier, CSV shipper costs, JSON holdouts with holdout_state exclusions.
- Entity matching uses alias_labels against contract panel_ref.
- Billing selection uses latest effective_week among status_flag=current.
- Network adjustment added to base payment per network_tier.
- Output requires JSON breakdown and Markdown summary with keep/switch decision against threshold.

## STOP — Read This First

**Do NOT compute inline.** This skill includes a bundled script (`scripts/compute_reagent_kit.py`) that handles all joins, alias matching, revision logic, and billing date selection. Running Python inline will produce errors. Use the script.

## Pre-Flight Checklist

Extract from task BEFORE computation:

### For Reagent Kit Policy (B5):
- [ ] Small-kit runs per year (commonly 24)
- [ ] Bulk-kit runs per year (commonly 12)
- [ ] Decision threshold in USD
- [ ] Decision output format (e.g., `adopt_bulk_kit`, `keep_small_kit`)
- [ ] Which assays are in-scope (`in_scope: true` in manifest)
- [ ] Lab override rule: highest approved revision per assay_id
- [ ] Billing rule: latest active effective_month per assay (aliases match)

### For Panel Dispatch Policy (B7):
- [ ] Cycle lengths in days (e.g., 14 vs 28)
- [ ] Days per year: **UNRESOLVED** - R8 used both 364 and 365.0; verify from task spec
- [ ] Runs per year: `days_per_year / cycle_days` (exact float)
- [ ] Decision threshold in USD
- [ ] Decision output format (e.g., `keep_14_day`, `switch_to_28_day`)
- [ ] In-scope filter: `analysis_mode == "review"` in panel manifest
- [ ] Holdout exclusion: panels with `holdout_state == "exclude"` removed
- [ ] Lab override rule: highest approved rev with non-empty active_labs, fallback to default_active_labs
- [ ] Contract rule: latest effective_week among status_flag=current, matched by alias_labels
- [ ] Network adjustment: added to base_payment per network_tier, default 0.0 if tier missing
- [ ] Shipper cost scaling: **UNRESOLVED** - R8 used both ×runs and ×runs×labs; verify from task spec

## Input Data Structure

### Variant 1: Reagent Kit (B5)

#### Assay Manifest (JSON)
- Nested structure: `regions` → `assays` array
- Each assay: `assay_id`, `assay_name`, `aliases[]`, `reagent_price_per_1000_tests_usd`, `tests_per_run_small`, `tests_per_run_bulk`, `carrier_type`, `default_active_labs`, `in_scope`
- Filter to `in_scope: true` only

#### Lab Overrides (CSV)
- Columns: `assay_id`, `revision`, `status`, `active_labs`
- **Critical**: Select only highest revision where `status == "approved"` per assay_id
- Ignore `draft` and `rejected` revisions
- Fallback to `default_active_labs` from manifest if no approved override

#### Billing Records (CSV)
- Columns: `assay_label`, `effective_month` (YYYY-MM format), `is_active`, `payment_per_run_per_lab_usd`
- **Critical matching rule**: Match `assay_label` against `assay_name` or `aliases[]` (case-sensitive, exact match)
- **Critical selection rule**: Among matching active records, select latest `effective_month` (descending sort)
- Do NOT sum multiple billing records; pick the single latest active one

#### Carrier Costs (CSV)
- Columns: `carrier_type`, `carrier_cost_usd`
- Join key: `carrier_type` from assay manifest

### Variant 2: Panel Dispatch (B7)

#### Panel Manifest (JSON)
- Nested structure: `service_clusters` → `panels` array
- Each panel: `panel_code`, `panel_name`, `alias_labels[]`, `reagent_cost_per_1000_tests_usd`, `tests_per_lab_per_run_14_day`, `tests_per_lab_per_run_28_day`, `network_tier`, `shipper_class`, `default_active_labs`, `analysis_mode`
- Filter to `analysis_mode == "review"` only

#### Holdouts (JSON)
- Structure: `holdouts` array with `panel_code` and `holdout_state`
- Exclude panels where `holdout_state == "exclude"`

#### Lab Overrides (CSV)
- Columns: `panel_code`, `rev`, `approval`, `active_labs`
- **Critical**: Select highest numeric `rev` where `approval == "approved"` AND `active_labs` is non-empty
- Fallback to `default_active_labs` if no qualifying override

#### Contract Terms (CSV)
- Columns: `panel_ref`, `status_flag`, `effective_week` (YYYY-WNN format), `base_payment_per_run_per_lab_usd`
- **Critical matching**: Match `panel_ref` against `panel_name` or `alias_labels[]`
- **Critical selection**: Among `status_flag == "current"`, pick latest `effective_week`

#### Network Adjustments (CSV)
- Columns: `network_tier`, `network_adjustment_per_run_per_lab_usd`
- Add to base payment per network_tier, default 0.0 if tier missing

#### Shipper Costs (CSV)
- Columns: `shipper_class`, `shipper_cost_usd`
- Join by `shipper_class` from panel manifest

## Workflow

### For Reagent Kit Policy (B5):
1. **Locate Inputs**: Identify all four input files (manifest JSON, overrides CSV, billing CSV, carrier CSV).
2. **Inspect Structure**: Verify JSON keys and CSV columns match expected patterns.
3. **Run Computation Script** (required):
   ```bash
   python3 scripts/compute_reagent_kit.py \
     --manifest assay_manifest.json \
     --overrides lab_overrides.csv \
     --billing billing.csv \
     --carriers carrier_cost.csv \
     --runs-small 24 --runs-bulk 12 \
     --threshold 7000 \
     --output-dir .
   ```
4. **Verify Outputs**: Check that `reagent_policy_report.json` and `reagent_policy_summary.md` exist.
5. **Review Decision**: Script outputs `adopt_bulk_kit` or `keep_small_kit`.

### For Panel Dispatch Policy (B7):
1. **Locate Inputs**: Identify all six input files (manifest JSON, holdouts JSON, overrides CSV, contracts CSV, network CSV, shipper CSV, template JSON).
2. **Inspect Structure**: Verify JSON keys and CSV columns match expected patterns.
3. **Run Computation Script** (required):
   ```bash
   python3 scripts/compute_panel_dispatch.py \
     --manifest panel_manifest.json \
     --holdouts holdouts.json \
     --overrides lab_capacity_overrides.csv \
     --contracts contract_terms.csv \
     --network network_adjustments.csv \
     --shipper shipper_cost.csv \
     --template report_template.json \
     --cycle-a 14 --cycle-b 28 \
     --threshold 6000 \
     --output-dir .
   ```
4. **Verify Outputs**: Check that `diagpanel_policy_report.json` and `diagpanel_policy_summary.md` exist.
5. **Review Decision**: Script outputs `keep_14_day` or `switch_to_28_day`.

## Key Formulas

### Variant 1: Reagent Kit (B5)

| Metric | Formula |
|--------|---------|
| Annual reagent cost | `tests_per_run × runs_per_year × labs × (price_per_1000 / 1000)` — identical for both policies |
| Annual carrier cost | `carrier_cost × runs_per_year × labs` — scales with runs (bulk has fewer runs) |
| Annual revenue | `payment_per_run × runs_per_year × labs` |
| Annual margin | `revenue - reagent_cost - carrier_cost` |

Reagent cost is identical between policies (same total annual tests). Carrier and revenue scale with run frequency.

### Variant 2: Panel Dispatch (B7)

| Metric | Formula |
|--------|---------|
| Runs per year | `days_per_year / cycle_days` (exact float) |
| Total payment per run | `base_payment + network_adjustment` |
| Annual reagent cost | `tests_per_run × runs_per_year × labs × (price_per_1000 / 1000)` — identical for both cycles |
| Annual shipper cost | `shipper_cost × runs_per_year × labs` (UNRESOLVED: may be ×runs only) |
| Annual revenue | `total_payment × runs_per_year × labs` |
| Annual margin | `revenue - reagent_cost - shipper_cost` |

Reagent cost is identical between cycles (same total annual tests). Shipper and revenue scale with run frequency.

## Decision Rule

The script implements:
```python
abs_diff = abs(margin_bulk - margin_small)
if margin_bulk > margin_small and abs_diff > threshold:
    decision = "adopt_bulk_kit"
else:
    decision = "keep_small_kit"
```

**Adopt only if**: bulk margin is higher AND absolute difference exceeds threshold.

## Key Differences from Related Skills

| Aspect | Cycle Margin | Infusion Batch | Reagent Kit |
|--------|-----------|----------------|-------------|
| Entity | therapy/medication | therapy | assay |
| Count type | patients (global or per-therapy) | patients (per-therapy) | labs (per-assay) |
| Cost basis | doses per fill | dose mg per day | tests per run |
| Frequency | fills per year | deliveries per year | runs per year |
| Supply | packaging per container | bags per delivery | carrier per run |
| Revenue | per-fill for N patients | per-delivery per patient | per-run per lab |
| Override rule | — | highest approved revision | highest approved revision |
| Billing selection | — | latest active by alias | latest active effective_month |

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (JSON). Pass raw float values directly. The verifier's tolerance decides acceptable precision.

## Anti-Patterns

### For Reagent Kit Policy (B5):
- **Do NOT** compute inline — use the bundled script
- **Do NOT** sum multiple billing records — pick latest active effective_month only
- **Do NOT** match billing by assay_id — use alias matching against assay_label
- **Do NOT** include assays with `in_scope: false`
- **Do NOT** sum lab revisions — pick highest approved per assay
- **Do NOT** use draft or rejected override revisions
- **Do NOT** assume carrier cost scales with tests — it scales with runs

### For Panel Dispatch Policy (B7):
- **Do NOT** compute inline — use the bundled script
- **Do NOT** include panels with `analysis_mode != "review"`
- **Do NOT** include panels with `holdout_state == "exclude"`
- **Do NOT** match contracts by `panel_code` — use alias matching against `panel_ref`
- **Do NOT** sum multiple contract records — pick latest effective_week among current only
- **Do NOT** use draft/rejected overrides or empty rev/active_labs rows
- **Do NOT** forget network adjustment — add to base payment, default 0.0 if missing
- **Do NOT** use integer runs/year (26, 13) — use exact `days_per_year / cycle_days`

## Troubleshooting

- **Missing billing match**: Check alias list includes the billing CSV's assay_label; verify case-sensitive matching.
- **Wrong lab counts**: Ensure filtering for `status=approved` and max revision; check fallback to default_active_labs.
- **Revenue seems wrong**: Verify you're using latest effective_month, not earliest or summing multiple months.
- **Decision seems wrong**: Re-check threshold comparison — adopt requires BOTH higher margin AND exceeds threshold.

## References

- `references/variant-mappings.md`: Sub-task specific field names and decision strings for known variants
- `references/panel-dispatch-invariants.md`: B7 (panel dispatch) variant rules — formula details, unresolved issues

## Known Invariants (by Sub-Task)

### harbor_reagentkit_bulk (B5: Reagent Kit Policy)
- Decision strings: `adopt_bulk_kit`, `keep_small_kit`
- Runs per year: fixed values (small=24, bulk=12)
- Lab override rule: highest approved revision per assay_id
- Billing rule: latest active effective_month per assay
- In-scope filter: `in_scope: true` in assay manifest
- Entity matching: assay_label matches assay_name or aliases[] (case-sensitive)

### harbor_diagpanel_14v28 (B7: Panel Dispatch Policy)
- Decision strings: `keep_14_day`, `switch_to_28_day`
- Margin difference field: `annual_margin_difference_28_minus_14_usd`
- **UNRESOLVED R8**: days_per_year (364 vs 365.0) — both failed, verify from task spec
- **UNRESOLVED R8**: shipper cost scaling (×runs vs ×runs×labs) — both failed, verify from task spec
- Lab override rule: highest approved rev with non-empty active_labs per panel_code
- Contract rule: latest effective_week among status_flag=current per panel
- In-scope filter: `analysis_mode: "review"` in panel manifest
- Holdout filter: exclude where `holdout_state: "exclude"` in holdouts JSON
- Entity matching: panel_ref matches alias_labels[] or panel_name
- Payment: `base_payment + network_adjustment` per run per lab
- Output files: `diagpanel_policy_report.json`, `diagpanel_policy_summary.md`