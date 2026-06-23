---
name: vaccination-crate-dispatch-analysis
description: Analyze vaccination campaign crate dispatch economics comparing different dispatch frequencies (6-day vs 12-day, etc.). Use when task involves campaign manifests with regions, location overrides with revision/state filtering, crate tier costs, per-dispatch billing with cycle_tag resolution, campaign name aliases, suspension status filtering, or threshold-based dispatch frequency recommendations.
---

# Vaccination Crate Dispatch Analysis

## When to Use
- Tasks comparing dispatch frequency economics (6-day vs 12-day, etc.)
- JSON campaign manifests with nested regions and campaign aliases
- Location override files with revision/state filtering logic
- Billing files with cycle_tag and status filtering
- Suspension status filtering for campaign exclusion
- Threshold-based recommendations for dispatch cycle decisions

## Input Data Structures

### Campaign Manifest (JSON)
```json
{
  "regions": [{
    "region": "north",
    "campaigns": [{
      "campaign_id": "VAX-ALPHA",
      "campaign_name": "Alpha Flu Mobile",
      "alias_labels": ["ALPHA FLU", "Alpha-FLU"],
      "drug_cost_per_1000_doses_usd": 94.2,
      "doses_per_day": 41,
      "crate_tier": "portable",
      "default_active_clinics": 16,
      "analysis_flag": "review"
    }]
  }]
}
```

### Location Overrides (CSV)
- Contains: `campaign_id`, `revision`, `state`, `active_clinics`
- Filter logic: Use highest revision where `state == "approved"` AND `active_clinics` is not blank
- If no valid override exists, use `default_active_clinics` from manifest

### Crate Cost (CSV)
- Maps `crate_tier` to `crate_cost_usd`
- Join key is crate_tier from campaign manifest

### Billing (CSV)
- Contains: `campaign_label`, `status`, `cycle_tag`, `payment_per_dispatch_per_clinic_usd`
- Filter logic: Use latest entry where `status == "active"` per campaign
- Requires matching via campaign_name and alias_labels

### Suspensions (CSV)
- Contains: `campaign_id`, `suspension_status`
- Filter logic: Exclude campaigns where `suspension_status == "hold"` (or other exclusion values)

## Workflow

1. **Parse campaign manifest**: Extract all campaigns from nested regions
2. **Filter in-scope campaigns**: Only those with `analysis_flag == "review"` (or specified flag)
3. **Apply suspension filter**: Exclude campaigns with suspension_status matching exclusion values
4. **Resolve clinic counts**: For each campaign, find highest approved revision with non-blank active_clinics; fall back to default_active_clinics
5. **Match billing**: Use campaign_name and alias_labels to match billing labels; select latest active entry by cycle_tag
6. **Join crate costs**: Match crate_tier to crate_cost_usd
7. **Calculate per-dispatch drug cost**: `(drug_cost_per_1000_doses / 1000) × doses_per_day × days_per_dispatch`
8. **Calculate per-dispatch revenue**: `payment_per_dispatch_per_clinic × active_clinics`
9. **Calculate per-dispatch margin**: `revenue - drug_cost - crate_cost`
10. **Annualize**: `annual_margin = per_dispatch_margin × dispatches_per_year`
11. **Compare models**: Calculate difference between dispatch frequencies
12. **Apply threshold**: Generate recommendation based on absolute difference vs threshold

## Calculation Formulas

### Per-Dispatch Drug Cost
```
drug_cost_per_dispatch = (drug_cost_per_1000_doses_usd / 1000) × doses_per_day × days_per_dispatch
```

### Per-Dispatch Revenue
```
revenue_per_dispatch = payment_per_dispatch_per_clinic_usd × active_clinics
```

### Per-Dispatch Margin
```
margin_per_dispatch = revenue_per_dispatch - drug_cost_per_dispatch - crate_cost_usd
```

### Annual Margin
```
annual_margin = margin_per_dispatch × dispatches_per_year
```

### Dispatches Per Year
- 6-day: 60 dispatches/year (360/6)
- 12-day: 30 dispatches/year
- General: `dispatches_per_year = 360 / days_per_dispatch` or as specified

## Location Override Resolution

Critical step - must filter correctly:
1. Filter rows where `state == "approved"`
2. Filter out rows where `active_clinics` is blank/empty/null
3. Group by `campaign_id`
4. Select row with highest `revision` number
5. Use `active_clinics` value from that row
6. If no valid rows exist, use `default_active_clinics` from manifest

**Common pitfalls**:
- Using draft or rejected state rows
- Not selecting highest revision
- Not filtering out blank active_clinics values
- Missing default fallback

## Billing Resolution

Billing file may have multiple entries per campaign with different cycle_tags:
1. Match campaign via campaign_name or alias_labels against `campaign_label`
2. Filter for `status == "active"`
3. Select entry with latest `cycle_tag` (alphabetically or chronologically)
4. Use `payment_per_dispatch_per_clinic_usd` from that entry

**Important**: When multiple aliases match different billing entries, collect all matches and select the one with latest cycle_tag.

## Campaign Name Matching

Billing file may use any variant:
- campaign_name (e.g., "Alpha Flu Mobile")
- Any alias_label (e.g., "ALPHA FLU", "Alpha-FLU")

Build a lookup map from all names/aliases to campaign_id, then match billing campaign_label values.

## Recommendation Logic

Typical threshold-based decision:
- If `abs(margin_difference) >= threshold`: maintain current dispatch frequency
- If `abs(margin_difference) < threshold`: switch to alternative dispatch frequency

**Verify the exact logic and output format from task spec** - direction and string format may vary.

## Validation Steps

1. **Verify campaign count**: Output should include all in-scope, non-suspended campaigns
2. **Check clinic counts**: Should match approved revisions with non-blank values or defaults
3. **Validate name matching**: All campaigns should have billing data
4. **Confirm output schema**: Match expected JSON structure exactly (check task spec)
5. **Verify recommendation format**: Use exact string format from task spec (e.g., `keep_6_day` vs `switch_to_12_day`)
6. **Check numeric precision**: Currency values to 2 decimal places
7. **Verify billing resolution**: Should use latest active entry per campaign

## Common Pitfalls

- **Wrong clinic count**: Using wrong revision, non-approved state, or blank values
- **Missing campaign matching**: Not checking all alias_labels for name matching
- **Incorrect recommendation direction**: Verify threshold comparison logic
- **Output schema mismatch**: Check task spec for exact field names and structure
- **Excluding campaigns incorrectly**: Only exclude where analysis_flag != "review" or suspension_status == "hold"
- **Calculation errors**: Drug cost scales with doses_per_day × days_per_dispatch
- **Missing billing resolution**: Must select latest active billing entry per campaign
- **Using inactive billing entries**: Filter for status == "active"
- **Not handling blank override values**: Skip rows with blank active_clinics
- **Multiple alias matches**: When aliases match different billing entries, resolve by cycle_tag

## Anti-Patterns

- Do not assume campaign_id matches billing labels directly
- Do not use draft or rejected location override rows
- Do not skip the highest-revision selection for location overrides
- Do not assume recommendation direction without checking task spec
- Do not hardcode clinic counts - extract from approved overrides or defaults
- Do not forget to multiply by active_clinics in revenue calculation
- Do not use inactive billing entries - filter for status == "active"
- Do not ignore cycle_tag when multiple billing entries exist
- Do not forget to filter by suspension_status
- Do not use override rows with blank active_clinics values

## Troubleshooting

### Test Failures on Output Format
1. Check exact JSON schema required by task
2. Verify field names match expected
3. Confirm numeric formatting (2 decimal places for currency)
4. Check if totals should be summed across all campaigns
5. Verify output file names match expected
6. Verify recommendation string format matches exactly

### Missing Campaign Matches
1. Print all campaign names and alias_labels
2. Print all billing campaign_label values
3. Check for case sensitivity or whitespace issues
4. Build comprehensive lookup from all variants

### Wrong Clinic Counts
1. Print location_overrides filtered by state
2. Verify highest revision selection per campaign
3. Check that campaigns without valid overrides use default_active_clinics
4. Ensure blank active_clinics values are skipped

### Margin Calculation Issues
1. Verify drug cost formula: per 1000 doses → per dose → per day → per dispatch
2. Check that crate cost is per dispatch, not per year
3. Confirm revenue is per clinic, must multiply by active_clinics
4. Verify dispatches_per_year calculation