# Oncology Cooler Dispatch Analysis (B4) — Variant Invariants

This reference covers B4 (cooler dispatch analysis) which follows the same abstract workflow as B3 (infusion batch analysis) with different entity names and a critical supply cost formula difference.

## Entity Mapping (B3 → B4)

| B3 (Infusion) | B4 (Cooler Dispatch) |
|---------------|----------------------|
| `therapy_code` | `program_code` |
| `therapy_name` | `program_name` |
| `therapies[]` | `programs[]` |
| `service_lines` | `service_groups` |
| `aliases[]` | `known_labels[]` |
| `active_patients` | `active_sites` |
| `revision` | `version_no` |
| `status` | `approval_state` |
| `include_in_review` | `review_flag == "review"` |
| `bag_size_ml` | `cooler_type` |
| `bag_supply_cost_usd` | `cooler_cost_usd` |
| `dose_mg_per_day` | `units_per_day` |

## Key Formula Differences

### Cooler Cost — CRITICAL

**B4-specific rule: Cooler cost is NOT multiplied by active sites.**

```
Annual cooler cost = cooler_cost_usd × dispatches_per_year
```

Unlike B3 where supply cost is multiplied by patients, cooler cost is a per-dispatch program cost.

| Metric | B3 Formula | B4 Formula |
|--------|-----------|------------|
| Drug cost | `dose_mg/day × 365 × patients × (price/1000)` | `(price/1000) × units/day × days_per_year × sites` |
| Supply cost | `bag_cost × deliveries/year × patients` | `cooler_cost × dispatches/year` (NO sites multiplier!) |
| Revenue | `payment × deliveries/year × patients` | `payment × dispatches/year × sites` |
| Margin | `revenue - drug - supply` | `revenue - drug - cooler` |

### Days Per Year

B3 uses **365** days for drug costing. B4 commonly uses **360** days — verify from task spec.

## Input Structure Differences

### Catalog (JSON)
```json
{
  "service_groups": [{
    "programs": [{
      "program_code": "ONCO-SUPPORT-001",
      "program_name": "Supportive Care Alpha",
      "known_labels": ["SC-ALPHA", "SUPPORT-ALPHA"],
      "acquisition_cost_per_1000_units_usd": 42.50,
      "units_per_day": 150,
      "cooler_type": "Standard-40L",
      "default_active_sites": 25,
      "review_flag": "review"
    }]
  }]
}
```

Filter: `review_flag == "review"` (string comparison, not boolean)

### Site Overrides (CSV)
```csv
program_code,version_no,approval_state,active_sites
ONCO-SUPPORT-001,1,draft,22
ONCO-SUPPORT-001,2,approved,28
ONCO-SUPPORT-001,3,rejected,30
```

Select: highest `version_no` where `approval_state == "approved"`.
Fallback: `default_active_sites` from catalog if no approved override.

### Cooler Cost (CSV)
```csv
cooler_type,cooler_cost_usd
Standard-40L,125.00
Large-80L,210.00
```

### Contract Payment (CSV)
```csv
program_label,payment_per_dispatch_per_site_usd
SC-ALPHA,8.50
SUPPORT-ALPHA,8.50
```

Match `program_label` against `known_labels[]` or `program_name` (case-insensitive).

## Common B4 Failures

1. **Cooler cost multiplied by sites** — wrong. Cooler cost is per-dispatch, NOT per-site.
2. **365 vs 360 days** — verify task spec; drug cost uses different days_per_year.
3. **No default fallback** — when no approved override exists, use `default_active_sites`.
4. **Case-sensitive label matching** — use case-insensitive matching.
5. **Review flag is string** — `review_flag == "review"` not boolean `true`.

## Decision Rule (same as B3)

Switch only if BOTH conditions met:
1. `margin_B > margin_A`
2. `|margin_B - margin_A| > threshold`

Decision strings: `keep_X_day` or `switch_to_Y_day` (verify task spec for exact format).
