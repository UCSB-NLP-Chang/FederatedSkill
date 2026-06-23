---
name: reagent-kit-analysis
description: Computes and compares annual margin between small-kit and bulk-kit reagent policies for diagnostic assays. Use when tasked with evaluating reagent kit economics, lab supply chain optimization, or bulk purchasing decisions involving assay manifests, lab overrides with revision control, billing records with effective dates, and carrier costs. Distinct from cycle-margin-analysis and infusion-batch-analysis: uses per-assay lab counts, tests-per-run scaling, effective_month billing selection, and small-vs-bulk kit comparison (24 vs 12 runs/year).
---

# Reagent Kit Policy Analysis

## When to Use

- Task requires comparing financial impact of small-kit (e.g., 24 runs/year) vs bulk-kit (e.g., 12 runs/year) reagent policies.
- Input includes: JSON assay manifest with in-scope flags and aliases, CSV lab overrides with revision/status, CSV billing records with effective_month and is_active flags, CSV carrier costs.
- Entity matching uses aliases against billing labels, not direct code joins.
- Output requires JSON breakdown and Markdown summary with adopt/keep decision against threshold.

## STOP — Read This First

**Do NOT compute inline.** This skill includes a bundled script (`scripts/compute_reagent_kit.py`) that handles all joins, alias matching, revision logic, and billing date selection. Running Python inline will produce errors. Use the script.

## Pre-Flight Checklist

Extract from task BEFORE computation:
- [ ] Small-kit runs per year (commonly 24)
- [ ] Bulk-kit runs per year (commonly 12)
- [ ] Decision threshold in USD
- [ ] Decision output format (e.g., `adopt_bulk_kit`, `keep_small_kit`)
- [ ] Which assays are in-scope (`in_scope: true` in manifest)
- [ ] Lab override rule: highest approved revision per assay_id
- [ ] Billing rule: latest active effective_month per assay (aliases match)

## Input Data Structure

### Assay Manifest (JSON)
- Nested structure: `regions` → `assays` array
- Each assay: `assay_id`, `assay_name`, `aliases[]`, `reagent_price_per_1000_tests_usd`, `tests_per_run_small`, `tests_per_run_bulk`, `carrier_type`, `default_active_labs`, `in_scope`
- Filter to `in_scope: true` only

### Lab Overrides (CSV)
- Columns: `assay_id`, `revision`, `status`, `active_labs`
- **Critical**: Select only highest revision where `status == "approved"` per assay_id
- Ignore `draft` and `rejected` revisions
- Fallback to `default_active_labs` from manifest if no approved override

### Billing Records (CSV)
- Columns: `assay_label`, `effective_month` (YYYY-MM format), `is_active`, `payment_per_run_per_lab_usd`
- **Critical matching rule**: Match `assay_label` against `assay_name` or `aliases[]` (case-sensitive, exact match)
- **Critical selection rule**: Among matching active records, select latest `effective_month` (descending sort)
- Do NOT sum multiple billing records; pick the single latest active one

### Carrier Costs (CSV)
- Columns: `carrier_type`, `carrier_cost_usd`
- Join key: `carrier_type` from assay manifest

## Workflow

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
5. **Review Decision**: Script outputs `adopt_bulk_kit` or `keep_small_kit` based on margin comparison AND threshold.

## Key Formulas

| Metric | Formula |
|--------|---------|
| Annual reagent cost | `tests_per_run × runs_per_year × labs × (price_per_1000 / 1000)` — identical for both policies |
| Annual carrier cost | `carrier_cost × runs_per_year × labs` — scales with runs (bulk has fewer runs) |
| Annual revenue | `payment_per_run × runs_per_year × labs` |
| Annual margin | `revenue - reagent_cost - carrier_cost` |

Reagent cost is identical between policies (same total annual tests). Carrier and revenue scale with run frequency.

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

- **Do NOT** compute inline — use the bundled script
- **Do NOT** sum multiple billing records — pick latest active effective_month only
- **Do NOT** match billing by assay_id — use alias matching against assay_label
- **Do NOT** include assays with `in_scope: false`
- **Do NOT** sum lab revisions — pick highest approved per assay
- **Do NOT** use draft or rejected override revisions
- **Do NOT** assume carrier cost scales with tests — it scales with runs

## Troubleshooting

- **Missing billing match**: Check alias list includes the billing CSV's assay_label; verify case-sensitive matching.
- **Wrong lab counts**: Ensure filtering for `status=approved` and max revision; check fallback to default_active_labs.
- **Revenue seems wrong**: Verify you're using latest effective_month, not earliest or summing multiple months.
- **Decision seems wrong**: Re-check threshold comparison — adopt requires BOTH higher margin AND exceeds threshold.

## References

- `references/variant-mappings.md`: Sub-task specific field names and decision strings for known variants