---
name: reagent-kit-analysis
description: Analyze laboratory reagent kit restocking policies comparing different run frequencies (small-kit vs bulk-kit). Use when task involves assay catalogs with regions, lab overrides with revision/status filtering, carrier type costs, per-run billing with effective_month resolution, assay name aliases, or threshold-based restocking policy recommendations.
---

# Reagent Kit Restocking Analysis

## When to Use
- Tasks comparing restocking frequency economics (small-kit vs bulk-kit, different runs per year)
- JSON assay catalogs with nested regions and assay aliases
- Lab override files with revision/status filtering logic
- Billing files with effective_month and is_active filtering
- Threshold-based recommendations for restocking policy decisions

## Input Data Structures

### Assay Catalog (JSON)
```json
{
  "regions": [{
    "region": "central",
    "assays": [{
      "assay_id": "CHEM-ION",
      "assay_name": "Ion Balance Panel",
      "aliases": ["ION BAL PANEL", "Ion Panel"],
      "reagent_price_per_1000_tests_usd": 86.4,
      "carrier_type": "ambient_small",
      "tests_per_lab_per_run_small": 42,
      "tests_per_lab_per_run_bulk": 84,
      "default_active_labs": 12,
      "in_scope": true
    }]
  }]
}
```

### Lab Overrides (CSV)
- Contains: `assay_id`, `revision`, `status`, `active_labs`
- Filter logic: Use highest revision where `status == "approved"`
- If no approved override exists, use `default_active_labs` from catalog

### Carrier Cost (CSV)
- Maps `carrier_type` to `carrier_cost_usd`
- Join key is carrier_type from assay catalog

### Billing (CSV)
- Contains: `assay_label`, `effective_month`, `is_active`, `payment_per_run_per_lab_usd`
- Filter logic: Use latest entry where `is_active == true` per assay
- Requires matching via assay_name and aliases

## Workflow

1. **Parse assay catalog**: Extract all assays from nested regions
2. **Filter in-scope assays**: Only those with `in_scope: true`
3. **Resolve lab counts**: For each assay, find highest approved revision in lab_overrides; fall back to default_active_labs
4. **Match billing**: Use assay_name and aliases to match billing labels; select latest active entry by effective_month
5. **Join carrier costs**: Match carrier_type to carrier_cost_usd
6. **Calculate per-run reagent cost**: `(reagent_price_per_1000_tests / 1000) × tests_per_lab_per_run × active_labs`
7. **Calculate per-run revenue**: `payment_per_run_per_lab × active_labs`
8. **Calculate per-run margin**: `revenue - reagent_cost - carrier_cost`
9. **Annualize**: `annual_margin = per_run_margin × runs_per_year`
10. **Compare models**: Calculate difference between small-kit and bulk-kit
11. **Apply threshold**: Generate recommendation based on absolute difference vs threshold

## Calculation Formulas

### Per-Run Reagent Cost
```
reagent_cost_per_run = (reagent_price_per_1000_tests_usd / 1000) × tests_per_lab_per_run × active_labs
```

### Per-Run Revenue
```
revenue_per_run = payment_per_run_per_lab_usd × active_labs
```

### Per-Run Margin
```
margin_per_run = revenue_per_run - reagent_cost_per_run - carrier_cost_usd
```

### Annual Margin
```
annual_margin = margin_per_run × runs_per_year
```

### Runs Per Year
- Small-kit: 24 runs/year (biweekly restocking)
- Bulk-kit: 12 runs/year (monthly restocking)
- Or as specified in task

## Lab Override Resolution

Critical step - must filter correctly:
1. Filter rows where `status == "approved"`
2. Group by `assay_id`
3. Select row with highest `revision` number
4. Use `active_labs` value from that row
5. If no approved rows exist for an assay, use `default_active_labs` from catalog

**Common pitfall**: Using draft or rejected status rows, or not selecting highest revision.

## Billing Resolution

Billing file may have multiple entries per assay with different effective months:
1. Match assay via assay_name or aliases against `assay_label`
2. Filter for `is_active == true`
3. Select entry with latest `effective_month`
4. Use `payment_per_run_per_lab_usd` from that entry

**Common pitfall**: Using inactive entries or not selecting latest effective_month.

## Assay Name Matching

Billing file may use any variant:
- assay_name (e.g., "Ion Balance Panel")
- Any alias (e.g., "ION BAL PANEL", "Ion Panel")

Build a lookup map from all names/aliases to assay_id, then match billing assay_label values.

## Recommendation Logic

Typical threshold-based decision:
- If `abs(margin_difference) >= threshold`: maintain current policy
- If `abs(margin_difference) < threshold`: switch to alternative policy

**Verify the exact logic from task spec** - direction may vary.

## Validation Steps

1. **Verify assay count**: Output should include all in-scope assays
2. **Check lab counts**: Should match approved revisions or defaults
3. **Validate name matching**: All assays should have billing data
4. **Confirm output schema**: Match expected JSON structure exactly
5. **Verify recommendation format**: Use exact string format from task spec
6. **Check numeric precision**: Currency values to 2 decimal places
7. **Verify billing resolution**: Should use latest active entry per assay

## Common Pitfalls

- **Wrong lab count**: Using wrong revision or non-approved status
- **Missing assay matching**: Not checking all aliases for name matching
- **Incorrect recommendation direction**: Verify threshold comparison logic
- **Output schema mismatch**: Check task spec for exact field names
- **Excluding assays incorrectly**: Only exclude where `in_scope: false`
- **Calculation errors**: Reagent cost scales with tests_per_lab_per_run × active_labs
- **Missing billing resolution**: Must select latest active billing entry per assay
- **Using inactive billing entries**: Filter for is_active == true

## Anti-Patterns

- Do not assume assay_id matches billing labels directly
- Do not use draft or rejected lab override rows
- Do not skip the highest-revision selection for lab overrides
- Do not assume recommendation direction without checking task spec
- Do not hardcode lab counts - extract from approved overrides or defaults
- Do not forget to multiply by active_labs in revenue calculation
- Do not use inactive billing entries - filter for is_active == true
- Do not ignore effective_month when multiple billing entries exist

## Troubleshooting

### Test Failures on Output Format
1. Check exact JSON schema required by task
2. Verify field names match expected
3. Confirm numeric formatting (2 decimal places for currency)
4. Check if totals should be summed across all assays
5. Verify output file names match expected

### Missing Assay Matches
1. Print all assay names and aliases
2. Print all billing assay_label values
3. Check for case sensitivity or whitespace issues
4. Build comprehensive lookup from all variants

### Wrong Lab Counts
1. Print lab_overrides filtered by status
2. Verify highest revision selection per assay
3. Check that assays without approved overrides use default_active_labs

### Margin Calculation Issues
1. Verify reagent cost formula: per 1000 tests → per test → per run → per lab
2. Check that carrier cost is per run, not per year
3. Confirm revenue is per lab, must multiply by active_labs
4. Verify runs_per_year calculation