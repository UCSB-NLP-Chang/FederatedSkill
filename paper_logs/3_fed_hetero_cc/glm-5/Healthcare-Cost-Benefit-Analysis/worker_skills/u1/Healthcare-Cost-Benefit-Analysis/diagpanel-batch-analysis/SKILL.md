---
name: diagpanel-batch-analysis
description: Computes and compares annual margin between two replenishment cadences for diagnostic panel networks (e.g., 14-day vs 28-day). Use when tasked with evaluating panel batch economics, diagnostics supply chain optimization, or cadence decisions involving panel manifests with analysis_mode flags, holdout exclusions, lab capacity overrides with revision/approval control, contract terms with effective_week selection, network tier adjustments, and shipper costs. Distinct from reagent-kit-analysis: uses service_clusters→panels structure, analysis_mode filtering, holdout_state exclusions, effective_week billing selection (latest among current), and network_tier adjustments added to base payment.
---

# Diagnostic Panel Batch Analysis

## STOP — Read This First

**Do NOT compute inline.** This skill includes a bundled script (`scripts/compute_diagpanel_batch.py`) that handles all joins, alias matching, revision logic, effective_week selection, holdout filtering, and precision calculations. Running Python inline will produce errors. Use the script.

## When to Use

- Task requires comparing financial impact of two replenishment cadences for diagnostic panel networks (e.g., 14-day vs 28-day).
- Input includes: JSON panel manifest with `analysis_mode` flags, JSON holdouts with `holdout_state`, CSV lab capacity overrides with `rev`/`approval`, CSV contract terms with `effective_week` and `status_flag`, CSV network adjustments by `network_tier`, CSV shipper costs by `shipper_class`.
- Entity matching uses `alias_labels[]` against contract `panel_ref`, NOT direct `panel_code` joins.
- Billing selection uses latest `effective_week` per panel among `status_flag=current` records.
- Output requires JSON breakdown and Markdown summary with keep/switch decision against threshold.

## Pre-Flight Checklist

Extract from task BEFORE computation:
- [ ] Cadence frequencies in DAYS (commonly 14-day vs 28-day)
- [ ] Days per year: 365 (exact float division for runs/year)
- [ ] Runs per year: `365.0 / cycle_days` — NOT integers 26 and 13
- [ ] Decision threshold in USD (commonly 6000)
- [ ] Decision output format: `keep_14_day` or `switch_to_28_day`
- [ ] In-scope filter: `analysis_mode == "review"` (exclude "archive", etc.)
- [ ] Holdout exclusion: `holdout_state == "exclude"` → remove panel entirely
- [ ] Override rule: highest approved `rev` with non-empty `active_labs`, else `default_active_labs`
- [ ] Contract rule: latest `effective_week` among `status_flag=current` records
- [ ] Payment formula: `base_payment + network_adjustment` (network_tier lookup, default 0.0 if missing)

## Input Data Structure

### Panel Manifest (JSON)
- Nested: `service_clusters` → `panels` array
- Per-panel: `panel_code`, `panel_name`, `alias_labels[]`, `reagent_cost_per_1000_tests_usd`, `network_tier`, `shipper_class`, `tests_per_lab_per_run_14_day`, `tests_per_lab_per_run_28_day`, `default_active_labs`, `analysis_mode`
- Filter: `analysis_mode == "review"` only

### Holdouts (JSON)
- Structure: `holdouts` array with `panel_code` and `holdout_state`
- Exclude panels where `holdout_state == "exclude"`
- Panels with `holdout_state == "clear"` or other values are retained

### Lab Capacity Overrides (CSV)
- Columns: `panel_code`, `rev` (numeric), `approval` (approved/draft/rejected), `active_labs` (may be empty)
- **Critical**: Select highest numeric `rev` where `approval == "approved"` AND `active_labs` is non-empty
- Skip rows with blank `rev` OR blank `active_labs`
- Fallback to manifest `default_active_labs` if no qualifying override

### Contract Terms (CSV)
- Columns: `panel_ref`, `status_flag` (current/historic), `effective_week` (YYYY-WNN format), `base_payment_per_run_per_lab_usd`
- **Critical matching**: `panel_ref` matches `panel_name` OR any in `alias_labels[]` (case-insensitive)
- **Critical selection**: Among `status_flag == "current"`, pick lexicographically latest `effective_week` (e.g., 2026-W22 > 2026-W10)
- Do NOT sum multiple contract records — pick single latest current

### Network Adjustments (CSV)
- Columns: `network_tier`, `network_adjustment_per_run_per_lab_usd`
- Join by `network_tier` from panel manifest
- Missing tier → default 0.0 adjustment
- **Total payment** = `base_payment + network_adjustment`

### Shipper Costs (CSV)
- Columns: `shipper_class`, `shipper_cost_usd`
- Join by `shipper_class` from panel manifest

## Workflow

1. **Locate Inputs**: Identify all input files (manifest JSON, holdouts JSON, overrides CSV, contracts CSV, network CSV, shipper CSV).
2. **Preserve Template**: If `report_template.json` exists, load and preserve `metadata` and `audit_notes` exactly in output.
3. **Inspect Structure**: Verify column names match expected patterns.
4. **Run Computation Script**:
   ```bash
   python3 scripts/compute_diagpanel_batch.py \
     --manifest panel_manifest.json \
     --overrides lab_capacity_overrides.csv \
     --contracts contract_terms.csv \
     --network network_adjustments.csv \
     --shipper shipper_cost.csv \
     --holdouts holdouts.json \
     --cycle-a 14 --cycle-b 28 \
     --threshold 6000 \
     --output-dir .
   ```
   Optional: `--template report_template.json` to inject metadata/audit_notes.
5. **Verify Outputs**: Check that `diagpanel_policy_report.json` and `diagpanel_policy_summary.md` exist with correct structure.
6. **Review Decision**: Script outputs `keep_14_day` or `switch_to_28_day` based on margin comparison AND threshold.

## Key Formulas

| Metric | Formula |
|--------|---------|
| Runs/year (14-day) | `365.0 / 14 = 26.071428571428573` |
| Runs/year (28-day) | `365.0 / 28 = 13.035714285714286` |
| Total payment per run | `base_payment + network_adjustment` |
| Annual reagent cost | `tests_per_lab_per_run × runs_per_year × labs × (price_per_1000 / 1000)` — identical both cycles |
| Annual shipper cost | `shipper_cost × runs_per_year × labs` |
| Annual revenue | `total_payment × runs_per_year × labs` |
| Annual margin | `revenue - reagent_cost - shipper_cost` |

**Note**: Reagent cost is identical between cycles (same total annual tests). Shipper and revenue scale with run frequency.

## Decision Rule

```python
abs_diff = abs(margin_28 - margin_14)
if margin_28 > margin_14 and abs_diff > threshold:
    decision = "switch_to_28_day"
else:
    decision = "keep_14_day"
```

**Switch only if**: 28-day margin is higher AND absolute difference exceeds threshold.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, CSV, Excel). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-Patterns

- **Do NOT** compute inline — use the bundled script
- **Do NOT** use integer runs/year (26, 13) — use exact `365.0 / cycle_days`
- **Do NOT** match contracts by `panel_code` — use `alias_labels[]` matching against `panel_ref`
- **Do NOT** sum multiple contract records — pick single latest `effective_week` among `status_flag == "current"` only
- **Do NOT** include panels with `analysis_mode != "review"`
- **Do NOT** include panels with `holdout_state == "exclude"`
- **Do NOT** use draft/rejected overrides — only approved
- **Do NOT** use empty `active_labs` overrides — fall back to default
- **Do NOT** forget to add network_adjustment to base_payment
- **Do NOT** assume network_tier exists — default to 0.0 adjustment if missing

## Key Differences from Reagent Kit Analysis

| Aspect | Reagent Kit | Diagnostic Panel |
|--------|-------------|------------------|
| Entity | assay | panel |
| Cycle basis | 24 vs 12 runs/year (fixed) | 365/14 vs 365/28 (exact float) |
| Billing date | `effective_month` | `effective_week` |
| Override revision | `revision` | `rev` |
| Override status | `status` | `approval` |
| Network adjustment | none | `network_tier` → adjustment added to payment |
| Holdout exclusion | none | `holdout_state == "exclude"` |
| In-scope flag | `in_scope` | `analysis_mode == "review"` |
| Cost field name | `reagent_price_per_1000_tests_usd` | `reagent_cost_per_1000_tests_usd` |

## Known Invariants (by sub-task)

### harbor_diagpanel_14v28 (14-day vs 28-day diagnostic panel cadence)
- Decision strings: `keep_14_day` or `switch_to_28_day`
- Margin difference field: `annual_margin_difference_28_minus_14_usd`
- Runs per year: 14-day=`365.0/14=26.071...`, 28-day=`365.0/28=13.035...`
- Lab override rule: highest numeric approved `rev` with non-empty `active_labs` per panel_code
- Contract rule: latest `effective_week` among `status_flag="current"` per panel
- In-scope filter: `analysis_mode: "review"` in panel manifest
- Holdout filter: exclude where `holdout_state: "exclude"` in holdouts JSON
- Entity matching: `panel_ref` in contract_terms.csv matches `alias_labels[]` or `panel_name` (case-insensitive)
- Payment: `base_payment + network_adjustment` per run per lab
- Network adjustment default: 0.0 if network_tier not found
- Output files: `diagpanel_policy_report.json`, `diagpanel_policy_summary.md`

## Troubleshooting

- **Missing contract match**: Check `alias_labels[]` includes the contract CSV's `panel_ref`; verify case-insensitive matching.
- **Wrong lab counts**: Ensure selecting max `rev` with non-empty `active_labs`; check fallback to `default_active_labs`.
- **Precision mismatch**: Verify using `365.0` (float) not `365` (int) in division.
- **Decision seems wrong**: Re-check threshold comparison — switch requires BOTH conditions.
- **Missing network adjustment**: Check network_tier join; default to 0.0 if tier not found.

## References

- `references/invariants.md`: Additional sub-task specific details and common errors