# Infusion Batch Calculation Examples

## Example: HINF-ALPHA (7-day vs 14-day)

**Inputs:**
- `dose_mg_per_day`: 52
- `patients`: 92
- `drug_cost_per_1000_mg_usd`: 42.4
- `bag_size_ml`: 250 → `bag_supply_cost_usd`: 6.40
- `payment_per_delivery_per_patient_usd`: 5.70

**Deliveries per year (exact):**
- 7-day: `365 / 7 = 52.142857142857146`
- 14-day: `365 / 14 = 26.071428571428573`

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

## Example: ONCO-COOL-A (10-day vs 20-day cooler dispatch)

**Inputs:**
- `acquisition_cost_per_1000_units_usd`: 850.00
- `units_per_day`: 4
- `active_sites`: 12 (from overrides, else `default_active_sites`)
- `cooler_type`: standard → `cooler_cost_usd`: 15.00
- `payment_per_dispatch_per_site_usd`: 2.50
- `days_per_year`: 360

**Dispatches per year:**
- 10-day: `360 / 10 = 36.0`
- 20-day: `360 / 20 = 18.0`

**Annual drug cost (identical for both cycles):**
```
(850 / 1000) × 4 units/day × 360 days × 12 sites = $14,688.00
```

**Annual cooler cost (CRITICAL: NOT multiplied by sites):**
- 10-day: `15.00 × 36 = $540.00`
- 20-day: `15.00 × 18 = $270.00`

**Annual revenue:**
- 10-day: `2.50 × 36 × 12 = $1,080.00`
- 20-day: `2.50 × 18 × 12 = $540.00`

**Annual margin:**
- 10-day: `1,080.00 - 14,688.00 - 540.00 = -$14,148.00`
- 20-day: `540.00 - 14,688.00 - 270.00 = -$14,418.00`
- Difference: `-$270.00` (10-day is better)

## Common Pitfall: Cooler Cost Multiplied by Sites

WRONG: `15.00 × 36 × 12 = $6,480.00` (cooler cost × dispatches × sites)

CORRECT: `15.00 × 36 = $540.00` (cooler cost × dispatches only)

Cooler is a per-dispatch program cost, NOT per-site.

## Common Pitfall: Integer Dispatches

Using `36` vs `18` is correct for 360/10 and 360/20 (exact integers).

But for 365-day year: `365/10 = 36.5`, `365/20 = 18.25` — do NOT round.
