# Infusion Batch Calculation Examples

## Example: HINF-ALPHA (7-day vs 14-day)

**Inputs:**
- `dose_mg_per_day`: 52
- `patients`: 92
- `drug_cost_per_1000_mg_usd`: 42.4
- `bag_size_ml`: 250 → `bag_supply_cost_usd`: 6.40
- `payment_per_delivery_per_patient_usd`: 5.70

**Deliveries per year (exact):**
- 7-day: `365.0 / 7 = 52.142857142857146`
- 14-day: `365.0 / 14 = 26.071428571428573`

**Annual drug cost (identical for both cycles):**
```
52 mg/day × 365 days × 92 patients × (42.4 / 1000) = $73,651.71
```

**Annual supply cost:**
- 7-day: `6.40 × 52.142857... × 92 = $30,697.60`
- 14-day: `6.40 × 26.071428... × 92 = $15,348.80`

**Annual revenue:**
- 7-day: `5.70 × 52.142857... × 92 = $27,343.20`
- 14-day: `5.70 × 26.071428... × 92 = $13,671.60`

**Annual margin:**
- 7-day: `27,343.20 - 73,651.71 - 30,697.60 = -$77,006.11`
- 14-day: `13,671.60 - 73,651.71 - 15,348.80 = -$75,328.91`
- Difference: `$1,677.20`

## Common Pitfall: Integer Deliveries

Using `52` and `26` instead of exact values:
- 7-day supply: `6.40 × 52 × 92 = $30,617.60` (off by $80)
- 14-day supply: `6.40 × 26 × 92 = $15,308.80` (off by $40)

This creates margin errors that accumulate across therapies.

## Patient Override Resolution

Given overrides CSV:
```
therapy_code,revision,status,active_patients
HINF-ALPHA,1,draft,88
HINF-ALPHA,2,approved,92
HINF-ALPHA,3,rejected,95
```

Selection: revision 2, approved, 92 patients (highest approved revision).

## Alias Matching

Payment CSV uses `therapy_label` which must match catalog `aliases`:

| Payment CSV therapy_label | Catalog alias match | therapy_code |
|---------------------------|---------------------|--------------|
| `ALPHA-NEB` | `ALPHA-NEB` | HINF-ALPHA |
| `BETA FLOW` | `BETA FLOW` | HINF-BETA |
| `GammaSure Infusion` | `GammaSure Infusion` | HINF-GAMMA |

Case-insensitive matching required.