---
name: infusion-therapy-analysis
description: Analyze home infusion therapy delivery batching decisions. Use when task involves therapy catalogs with service lines, patient overrides with revision/status filtering, therapy name aliases, delivery frequency comparisons (7-day vs 14-day), or threshold-based recommendations for infusion programs.
---

# Infusion Therapy Delivery Batching Analysis

## When to Use
- Tasks comparing delivery frequency economics (7-day vs 14-day batching)
- JSON therapy catalogs with nested service lines and therapy aliases
- Patient override files with revision/status filtering logic
- Therapy name matching across multiple data sources via aliases
- Threshold-based recommendations for operational decisions

## Input Data Structures

### Therapy Catalog (JSON)
```json
{
  "service_lines": [{
    "service_line": "pulmonary",
    "therapies": [{
      "therapy_code": "HINF-ALPHA",
      "therapy_name": "AlphaNeb",
      "aliases": ["ALPHA-NEB", "Alpha Neb"],
      "drug_cost_per_1000_mg_usd": 42.4,
      "dose_mg_per_day": 52,
      "bag_size_ml": 250,
      "include_in_review": true
    }]
  }]
}
```

### Patient Overrides (CSV)
- Contains: `therapy_code`, `revision`, `status`, `active_patients`
- Filter logic: Use highest revision where `status == "approved"`
- Multiple revisions may exist; must select correct one

### Delivery Payment (CSV)
- Maps therapy labels (may use aliases) to payment per delivery per patient
- Requires fuzzy matching via therapy_name and aliases

### Bag Supply Cost (CSV)
- Maps `bag_size_ml` to `bag_supply_cost_usd`
- Join key is bag_size_ml from therapy catalog

## Workflow

1. **Parse therapy catalog**: Extract all therapies from nested service_lines
2. **Filter in-scope therapies**: Only those with `include_in_review: true`
3. **Resolve patient counts**: For each therapy, find highest approved revision in patient_overrides
4. **Match delivery payments**: Use therapy_name and aliases to match against delivery_payment labels
5. **Join bag supply costs**: Match bag_size_ml to bag_supply_cost_usd
6. **Calculate per-delivery costs**: `drug_cost = (drug_cost_per_1000_mg / 1000) × dose_mg_per_day × days_per_delivery`
7. **Calculate margins**: `margin = payment - drug_cost - bag_supply_cost`
8. **Annualize**: `annual_margin = per_delivery_margin × deliveries_per_year × active_patients`
9. **Compare models**: Calculate difference between delivery frequencies
10. **Apply threshold**: Generate recommendation based on absolute difference vs threshold

## Calculation Formulas

### Per-Delivery Drug Cost
```
drug_cost_per_delivery = (drug_cost_per_1000_mg_usd / 1000) × dose_mg_per_day × days_per_delivery
```

### Per-Delivery Margin
```
margin_per_delivery = payment_per_delivery_per_patient_usd - drug_cost_per_delivery - bag_supply_cost_usd
```

### Annual Margin
```
annual_margin = margin_per_delivery × deliveries_per_year × active_patients
```

### Deliveries Per Year
- 7-day: 52 deliveries/year
- 14-day: 26 deliveries/year

## Patient Override Resolution

Critical step - must filter correctly:
1. Filter rows where `status == "approved"`
2. Group by `therapy_code`
3. Select row with highest `revision` number
4. Use `active_patients` value from that row

**Common pitfall**: Using draft or rejected status rows, or not selecting highest revision.

## Therapy Name Matching

Delivery payment file may use any variant:
- therapy_name (e.g., "AlphaNeb")
- Any alias (e.g., "ALPHA-NEB", "Alpha Neb")

Build a lookup map from all names/aliases to therapy_code, then match delivery_payment labels.

## Recommendation Logic

Typical threshold-based decision:
- If `abs(margin_difference) >= threshold`: recommend current model (stay)
- If `abs(margin_difference) < threshold`: recommend switch to alternative model

**Verify the exact logic from task spec** - direction may vary.

## Validation Steps

1. **Verify therapy count**: Output should include all in-scope therapies
2. **Check patient counts**: Should match approved revisions only
3. **Validate name matching**: All therapies should have payment data
4. **Confirm output schema**: Match expected JSON structure exactly
5. **Verify recommendation format**: Use exact string format from task spec
6. **Check numeric precision**: Currency values to 2 decimal places

## Common Pitfalls

- **Wrong patient count**: Using wrong revision or non-approved status
- **Missing therapy matching**: Not checking all aliases for name matching
- **Incorrect recommendation direction**: Verify threshold comparison logic
- **Output schema mismatch**: Check task spec for exact field names and structure
- **Excluding therapies incorrectly**: Only exclude where `include_in_review: false`
- **Calculation errors**: Drug cost scales with days_per_delivery

## Anti-Patterns

- Do not assume therapy_code matches delivery_payment labels directly
- Do not use draft or rejected patient override rows
- Do not skip the highest-revision selection for patient overrides
- Do not assume recommendation direction without checking task spec
- Do not hardcode patient counts - extract from approved overrides
- Do not forget to multiply by days_per_delivery in drug cost calculation

## Troubleshooting

### Test Failures on Output Format
1. Check exact JSON schema required by task
2. Verify field names match expected (e.g., `recommendation` vs `decision`)
3. Confirm numeric formatting (2 decimal places for currency)
4. Check if totals should be summed across all therapies

### Missing Therapy Matches
1. Print all therapy names and aliases
2. Print all delivery_payment labels
3. Check for case sensitivity or whitespace issues
4. Build comprehensive lookup from all variants

### Wrong Patient Counts
1. Print patient_overrides filtered by status
2. Verify highest revision selection per therapy
3. Check that excluded therapies (include_in_review: false) are not in output

### Margin Calculation Issues
1. Verify drug cost formula: per 1000 mg → per mg → per day → per delivery
2. Check that bag supply cost is per delivery, not per year
3. Confirm deliveries_per_year calculation (365/days)
