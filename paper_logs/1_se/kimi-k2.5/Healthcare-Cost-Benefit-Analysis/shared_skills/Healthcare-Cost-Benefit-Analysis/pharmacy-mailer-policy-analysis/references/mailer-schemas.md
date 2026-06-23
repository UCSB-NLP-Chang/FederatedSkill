# Mailer Program Schema Variants

## Payment Structure Patterns

### Split Payment (Base + Service Fee)
```json
{
  "payment_components": {
    "base_payment_per_fill_N_patients_usd": "pharmacy reimbursement",
    "service_fee_per_fill_N_patients_usd": "additional program fee"
  },
  "calculation": "total_payment = base_payment + service_fee"
}
```

Common in: compound pharmacy mailers, specialty medication programs

### Mailer Format Cost Mapping
| Format | Typical Cost | Use Case |
|--------|-------------|----------|
| standard | ~$1.40 | Standard tablets/capsules |
| buffered | ~$1.95 | Moisture-sensitive compounds |
| secure | ~$2.65 | Controlled substances, high-value |

## Scenario Naming Conventions

| Scenario A | Scenario B | Output Pattern | Notes |
|------------|-----------|----------------|-------|
| 45_day | 90_day | `keep_45_day` / `switch_to_90_day` | May include `_cycle` suffix |
| 30_day | 90_day | `keep_30_day` / `switch_to_90_day` | Standard refill |
| 28_day | 56_day | `keep_28_day` / `switch_to_56_day` | SyncPack style |

## Column Name Variants

### Compound Cost
- `medication` - drug name/strength
- `price_per_1000_doses_usd` or `price_per_1000_capsules_usd`
- `mailer_format` - key to mailer_cost lookup

### Mailer Cost
- `mailer_format` - standard/buffered/secure
- `mailer_cost_usd` or `packaging_cost_usd`

### Payment Files
- `base_payment_per_fill_{N}_patients_usd`
- `service_fee_per_fill_{N}_patients_usd`
- May be combined as `total_payment_per_fill` in some variants

## Calculation Verification

When 90-day margin seems unexpectedly low:
1. Verify fills_per_year: 365/90 = 4.06 → typically 4 fills
2. Confirm service_fee is added to base_payment
3. Check mailer_cost scales: 4 fills vs 8 fills should halve mailer costs
4. Verify revenue calculation: (base + fee) × fills, not base × fills + fee