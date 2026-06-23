# JSON Catalog Schema Variants

## Standard Home Infusion Structure

```json
{
  "service_lines": [
    {
      "service_line": "pulmonary|immunology|oncology|...",
      "therapies": [
        {
          "therapy_code": "HINF-XXX",
          "therapy_name": "BrandName",
          "aliases": ["ALIAS-1", "Alias 1"],
          "drug_cost_per_1000_mg_usd": 0.0,
          "dose_mg_per_day": 0,
          "bag_size_ml": 0,
          "include_in_review": true|false
        }
      ]
    }
  ]
}
```

## Common Variations

### Dosing Units
| Field | Alternative | Conversion |
|-------|-------------|------------|
| `dose_mg_per_day` | `dose_mg_per_fill`, `daily_dose_mg` | May need × fills/year |
| `drug_cost_per_1000_mg_usd` | `price_per_1000_mg`, `cost_per_1000_mg` | Same semantics |

### Container/Supply Sizing
| Field | Join Target |
|-------|-------------|
| `bag_size_ml` | `bag_supply_cost.csv` |
| `vial_size_ml` | `vial_supply_cost.csv` |
| `container_size_units` | Generic supply cost table |

### Scope Flags
- `include_in_review` (boolean) - Most common
- `active` (boolean) - Alternative flag name
- `status` (string: "active"|"inactive") - Rare variant

## Alias Matching Priority

When `therapy_label` in payment CSV doesn't match `therapy_code`:

1. Exact match: `therapy_name`
2. Substring match: any element in `aliases` array
3. Normalized match: case-insensitive, whitespace-normalized

## Service Line Patterns

Service lines group therapies but rarely affect calculations:
- `pulmonary` - Respiratory therapies
- `immunology` - Autoimmune/immunodeficiency
- `oncology` - Cancer therapies
- `cardiology` - Cardiac therapies

All therapies across service lines typically combined in final analysis.