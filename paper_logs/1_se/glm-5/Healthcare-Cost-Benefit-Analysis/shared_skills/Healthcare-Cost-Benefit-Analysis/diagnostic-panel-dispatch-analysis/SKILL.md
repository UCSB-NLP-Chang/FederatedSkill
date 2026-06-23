---
name: diagnostic-panel-dispatch-analysis
description: Analyze diagnostic panel dispatch economics comparing different run frequencies (14-day vs 28-day). Use when task involves panel manifests with service clusters, contract terms with effective_week resolution, network tier adjustments, lab capacity overrides with rev/approval filtering, holdout exclusions, or threshold-based dispatch frequency recommendations.
---

# Diagnostic Panel Dispatch Analysis

## When to Use
- Tasks comparing dispatch frequency economics (14-day vs 28-day, etc.)
- JSON panel manifests with nested service_clusters and panel aliases
- Contract terms files with effective_week resolution (not effective_month)
- Network tier adjustment files for per-run per-lab adjustments
- Lab capacity override files with rev/approval filtering
- Holdout files for panel exclusion
- Threshold-based recommendations for dispatch cycle decisions

## Input Data Structures

### Panel Manifest (JSON)
```json
{
  "service_clusters": [{
    "cluster_name": "core",
    "panels": [{
      "panel_code": "DP-ALPHA",
      "panel_name": "Alpha Chem Core",
      "alias_labels": ["ALPHA CORE", "Alpha-Core"],
      "reagent_cost_per_1000_tests_usd": 118.4,
      "network_tier": "metro",
      "shipper_class": "ambient_lab",
      "tests_per_lab_per_run_14_day": 34,
      "tests_per_lab_per_run_28_day": 68,
      "default_active_labs": 15,
      "analysis_mode": "review"
    }]
  }]
}
```

### Contract Terms (CSV)
- Contains: `panel_ref`, `status_flag`, `effective_week`, `base_payment_per_run_per_lab_usd`
- Filter logic: Use latest entry where `status_flag == "current"` per panel
- Requires matching via panel_name and alias_labels
- **Key difference**: Uses `effective_week` (e.g., "2026-W22"), not effective_month

### Network Adjustments (CSV)
- Maps `network_tier` to `network_adjustment_per_run_per_lab_usd`
- **Add to base payment** for total per-run per-lab revenue

### Shipper Cost (CSV)
- Maps `shipper_class` to `shipper_cost_usd`
- Join key is shipper_class from panel manifest

### Lab Capacity Overrides (CSV)
- Contains: `panel_code`, `rev`, `approval`, `active_labs`
- Filter logic: Use highest rev where `approval == "approved"` AND `active_labs` is not blank
- If no valid override exists, use `default_active_labs` from manifest

### Holdouts (JSON)
- Contains: `panel_code`, `holdout_state`
- Filter logic: Exclude panels where `holdout_state == "exclude"`

## Workflow

1. **Parse panel manifest**: Extract all panels from nested service_clusters
2. **Filter in-scope panels**: Only those with `analysis_mode == "review"`
3. **Apply holdout filter**: Exclude panels where holdout_state == "exclude"
4. **Resolve contract terms**: Match via panel_name/alias_labels; select latest by effective_week
5. **Apply network adjustment**: Add network_adjustment to base_payment for total revenue
6. **Resolve lab counts**: For each panel, find highest approved rev with non-blank active_labs; fall back to default
7. **Join shipper costs**: Match shipper_class to shipper_cost_usd
8. **Calculate per-run reagent cost**: `(reagent_cost_per_1000_tests / 1000) × tests_per_lab_per_run × active_labs`
9. **Calculate per-run revenue**: `(base_payment + network_adjustment) × active_labs`
10. **Calculate per-run margin**: `revenue - reagent_cost - shipper_cost`
11. **Annualize**: `annual_margin = per_run_margin × runs_per_year`
12. **Compare models**: Calculate difference between cadence options
13. **Apply threshold**: Generate recommendation based on absolute difference vs threshold

## Calculation Formulas

### Per-Run Revenue (Two Components)
```
total_payment_per_run_per_lab = base_payment_per_run_per_lab_usd + network_adjustment_per_run_per_lab_usd
revenue_per_run = total_payment_per_run_per_lab × active_labs
```

### Per-Run Reagent Cost
```
reagent_cost_per_run = (reagent_cost_per_1000_tests_usd / 1000) × tests_per_lab_per_run × active_labs
```

### Per-Run Margin
```
margin_per_run = revenue_per_run - reagent_cost_per_run - shipper_cost_usd
```

### Annual Margin
```
annual_margin = margin_per_run × runs_per_year
```

### Runs Per Year
- 14-day: 26 runs/year (364/14 or 52/2)
- 28-day: 13 runs/year (364/28)
- General: `runs_per_year = 364 / days_per_run` or as specified

## Contract Term Resolution

Contract terms file uses `effective_week` format (e.g., "2026-W22"):
1. Match panel via panel_name or alias_labels against `panel_ref`
2. Filter for `status_flag == "current"`
3. Select entry with latest `effective_week` (compare alphabetically or parse week number)
4. Use `base_payment_per_run_per_lab_usd` from that entry

**Common pitfall**: Using wrong effective_week or not selecting latest.

## Lab Capacity Override Resolution

Critical step - must filter correctly:
1. Filter rows where `approval == "approved"`
2. Filter out rows where `active_labs` is blank/empty/null
3. Group by `panel_code`
4. Select row with highest `rev` number
5. Use `active_labs` value from that row
6. If no valid rows exist, use `default_active_labs` from manifest

**Common pitfalls**:
- Using draft or rejected rows
- Not selecting highest rev
- Not filtering out blank active_labs values
- Missing default fallback

## Panel Name Matching

Contract terms file may use any variant:
- panel_name (e.g., "Alpha Chem Core")
- Any alias_label (e.g., "ALPHA CORE", "Alpha-Core")

Build a lookup map from all names/aliases to panel_code, then match contract_terms panel_ref values.

## Recommendation Logic

Typical threshold-based decision:
- If `abs(margin_difference) >= threshold`: maintain current cadence
- If `abs(margin_difference) < threshold`: switch to alternative cadence

**Verify the exact logic and output format from task spec** - direction and string format may vary.

## Validation Steps

1. **Verify panel count**: Output should include all in-scope, non-excluded panels
2. **Check lab counts**: Should match approved revs with non-blank values or defaults
3. **Validate name matching**: All panels should have contract terms
4. **Confirm network adjustment applied**: Total revenue = base + network adjustment
5. **Confirm output schema**: Match expected JSON structure exactly
6. **Verify recommendation format**: Use exact string format from task spec
7. **Check numeric precision**: Currency values to 2 decimal places
8. **Verify contract resolution**: Should use latest effective_week per panel

## Common Pitfalls

- **Missing network adjustment**: Must ADD network_adjustment to base_payment
- **Wrong lab count**: Using wrong rev, non-approved status, or blank values
- **Missing panel matching**: Not checking all alias_labels for matching
- **Incorrect recommendation direction**: Verify threshold comparison logic
- **Output schema mismatch**: Check task spec for exact field names
- **Excluding panels incorrectly**: Only exclude where analysis_mode != "review" or holdout_state == "exclude"
- **Calculation errors**: Reagent cost scales with tests_per_lab_per_run × active_labs
- **Missing contract resolution**: Must select latest effective_week per panel
- **Using wrong tests_per_run**: Use 14-day value for 14-day calc, 28-day value for 28-day calc

## Anti-Patterns

- Do not assume panel_code matches contract_terms panel_ref directly
- Do not use draft or rejected lab capacity override rows
- Do not skip the highest-rev selection for lab overrides
- Do not forget to add network_adjustment to base_payment
- Do not assume recommendation direction without checking task spec
- Do not hardcode lab counts - extract from approved overrides or defaults
- Do not forget to multiply by active_labs in revenue calculation
- Do not use inactive contract terms - filter for status_flag == "current"
- Do not ignore effective_week when multiple contract entries exist
- Do not forget to filter by holdout_state
- Do not use override rows with blank active_labs values

## Troubleshooting

### Test Failures on Output Format
1. Check exact JSON schema required by task
2. Verify field names match expected
3. Confirm numeric formatting (2 decimal places for currency)
4. Check if totals should be summed across all panels
5. Verify output file names match expected
6. Verify recommendation string format matches exactly

### Missing Panel Matches
1. Print all panel names and alias_labels
2. Print all contract_terms panel_ref values
3. Check for case sensitivity or whitespace issues
4. Build comprehensive lookup from all variants

### Wrong Lab Counts
1. Print lab_capacity_overrides filtered by approval
2. Verify highest rev selection per panel
3. Check that panels without valid overrides use default_active_labs
4. Ensure blank active_labs values are skipped

### Margin Calculation Issues
1. Verify reagent cost formula: per 1000 tests → per test → per run → per lab
2. Check that shipper cost is per run, not per year
3. Confirm revenue includes BOTH base_payment AND network_adjustment
4. Verify runs_per_year calculation
5. Confirm correct tests_per_lab_per_run value used for each cadence