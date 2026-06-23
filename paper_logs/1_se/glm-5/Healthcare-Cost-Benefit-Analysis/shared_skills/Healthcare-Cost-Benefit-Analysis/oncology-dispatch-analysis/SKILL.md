---
name: oncology-dispatch-analysis
description: Analyze oncology supportive-care cooler dispatch economics comparing different dispatch frequencies. Use when task involves program catalogs with service groups, site overrides with version/approval filtering, cooler type costs, per-dispatch payment contracts, or threshold-based dispatch frequency recommendations.
---

# Oncology Cooler Dispatch Analysis

## When to Use
- Tasks comparing dispatch frequency economics (10-day vs 20-day, etc.)
- JSON program catalogs with nested service_groups and program aliases
- Site override files with version/approval_state filtering logic
- Program label matching across multiple data sources via known_labels
- Threshold-based recommendations for dispatch cycle decisions

## Input Data Structures

### Program Catalog (JSON)
```json
{
  "service_groups": [{
    "group_name": "antiemetic",
    "programs": [{
      "program_code": "ONC-ALFA",
      "program_name": "AlfaEase",
      "known_labels": ["ALFA EASE", "Alfa-Ease"],
      "acquisition_cost_per_1000_units_usd": 58.4,
      "units_per_day": 64,
      "cooler_type": "small_cold",
      "default_active_sites": 14,
      "review_flag": "review"
    }]
  }]
}
```

### Site Overrides (CSV)
- Contains: `program_code`, `version_no`, `approval_state`, `active_sites`
- Filter logic: Use highest version where `approval_state == "approved"`
- If no approved override exists, use `default_active_sites` from catalog

### Cooler Cost (CSV)
- Maps `cooler_type` to `cooler_cost_usd`
- Join key is cooler_type from program catalog

### Contract Payment (CSV)
- Maps program labels to `payment_per_dispatch_per_site_usd`
- Requires matching via program_name and known_labels

## Workflow

1. **Parse program catalog**: Extract all programs from nested service_groups
2. **Filter in-scope programs**: Only those with `review_flag == "review"` (or specified flag)
3. **Resolve site counts**: For each program, find highest approved version in site_overrides; fall back to default_active_sites
4. **Match contract payments**: Use program_name and known_labels to match against contract_payment labels
5. **Join cooler costs**: Match cooler_type to cooler_cost_usd
6. **Calculate per-dispatch costs**: `acquisition_cost = (acquisition_cost_per_1000_units / 1000) × units_per_day × days_per_dispatch`
7. **Calculate margins**: `margin = payment_per_dispatch_per_site × active_sites - acquisition_cost - cooler_cost`
8. **Annualize**: `annual_margin = per_dispatch_margin × dispatches_per_year`
9. **Compare models**: Calculate difference between dispatch frequencies
10. **Apply threshold**: Generate recommendation based on absolute difference vs threshold

## Calculation Formulas

### Per-Dispatch Acquisition Cost
```
acquisition_cost_per_dispatch = (acquisition_cost_per_1000_units_usd / 1000) × units_per_day × days_per_dispatch
```

### Per-Dispatch Margin
```
margin_per_dispatch = (payment_per_dispatch_per_site_usd × active_sites) - acquisition_cost_per_dispatch - cooler_cost_usd
```

### Annual Margin
```
annual_margin = margin_per_dispatch × dispatches_per_year
```

### Dispatches Per Year
- 10-day: 36 dispatches/year (360/10, allowing for holidays)
- 20-day: 18 dispatches/year
- General: `dispatches_per_year = 360 / days_per_dispatch` or as specified

## Site Override Resolution

Critical step - must filter correctly:
1. Filter rows where `approval_state == "approved"`
2. Group by `program_code`
3. Select row with highest `version_no`
4. Use `active_sites` value from that row
5. If no approved rows exist for a program, use `default_active_sites` from catalog

**Common pitfall**: Using draft or rejected rows, or not selecting highest version.

## Program Label Matching

Contract payment file may use any variant:
- program_name (e.g., "AlfaEase")
- Any known_label (e.g., "ALFA EASE", "Alfa-Ease")

Build a lookup map from all names/labels to program_code, then match contract_payment program_label values.

## Recommendation Logic

Typical threshold-based decision:
- If `abs(margin_difference) >= threshold`: maintain current dispatch frequency
- If `abs(margin_difference) < threshold`: switch to alternative dispatch frequency

**Verify the exact logic from task spec** - direction may vary.

## Validation Steps

1. **Verify program count**: Output should include all in-scope programs
2. **Check site counts**: Should match approved revisions or defaults
3. **Validate label matching**: All programs should have payment data
4. **Confirm output schema**: Match expected JSON structure exactly
5. **Verify recommendation format**: Use exact string format from task spec
6. **Check numeric precision**: Currency values to 2 decimal places
7. **Verify annual dispatches**: Check if 360 or 365 days used as base

## Common Pitfalls

- **Wrong site count**: Using wrong version or non-approved state
- **Missing program matching**: Not checking all known_labels for matching
- **Incorrect recommendation direction**: Verify threshold comparison logic
- **Output schema mismatch**: Check task spec for exact field names
- **Excluding programs incorrectly**: Only exclude where `review_flag != "review"`
- **Calculation errors**: Acquisition cost scales with days_per_dispatch
- **Missing default fallback**: For programs without approved overrides, use default_active_sites

## Anti-Patterns

- Do not assume program_code matches contract_payment labels directly
- Do not use draft or rejected site override rows
- Do not skip the highest-version selection for site overrides
- Do not assume recommendation direction without checking task spec
- Do not hardcode site counts - extract from approved overrides or defaults
- Do not forget to multiply by days_per_dispatch in acquisition cost calculation
- Do not forget to multiply payment by active_sites

## Troubleshooting

### Test Failures on Output Format
1. Check exact JSON schema required by task
2. Verify field names match expected
3. Confirm numeric formatting (2 decimal places for currency)
4. Check if totals should be summed across all programs

### Missing Program Matches
1. Print all program names and known_labels
2. Print all contract_payment program_label values
3. Check for case sensitivity or whitespace issues
4. Build comprehensive lookup from all variants

### Wrong Site Counts
1. Print site_overrides filtered by approval_state
2. Verify highest version selection per program
3. Check that programs without approved overrides use default_active_sites

### Margin Calculation Issues
1. Verify acquisition cost formula: per 1000 units → per unit → per day → per dispatch
2. Check that cooler cost is per dispatch, not per year
3. Confirm payment is per site, must multiply by active_sites
4. Verify dispatches_per_year calculation