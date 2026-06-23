---
name: pharmacy-mailer-policy-analysis
description: Analyze pharmacy mailer program financials comparing fill cycle scenarios (e.g., 45-day vs 90-day) for specialty medications with compound costs, variable mailer formats, and split payment structures (base + service fee). Use when task involves compound_cost.csv, mailer_cost.csv, base_payment.csv, service_fee.csv files and requires comparing fill frequency models for mail-order pharmacy programs.
---

# Pharmacy Mailer Policy Analysis

Compare fill cycle scenarios for specialty medication mailer programs.

## Workflow

1. **Identify input files** - Look for these specific patterns:
   - `compound_cost.csv` - medication prices with mailer format tags
   - `mailer_cost.csv` - per-format packaging costs (standard/buffered/secure)
   - `base_payment.csv` - base reimbursement per fill
   - `service_fee.csv` - additional per-fill service fees

2. **Parse compound cost structure**
   - Join with `mailer_cost.csv` on `mailer_format` column
   - Typical formats: `standard`, `buffered`, `secure` with costs ~$1.40-$2.65

3. **Calculate total per-fill payment**
   ```
   total_payment_per_fill = base_payment_per_fill + service_fee_per_fill
   ```
   **Critical**: Do NOT omit service fee - it's separate from base payment

4. **Calculate annual financials per medication**
   
   Annual drug cost (constant across fill frequencies):
   ```
   annual_doses = daily_doses × 365 × patients
   annual_drug_cost = annual_doses × price_per_1000 / 1000
   ```
   
   Annual mailer cost (varies by fill frequency):
   ```
   annual_mailer_cost = mailer_cost_per_fill × fills_per_year × patients
   ```
   
   Annual revenue (varies by fill frequency):
   ```
   annual_revenue = total_payment_per_fill × fills_per_year
   ```
   
   Annual margin:
   ```
   annual_margin = annual_revenue − annual_drug_cost − annual_mailer_cost
   ```

5. **Fill frequency calculations**
   | Days | Fills/Year | Common scenarios |
   |------|-----------|------------------|
   | 45 | 8 | Bi-monthly mailer |
   | 90 | 4 | Quarterly mailer |

6. **Aggregate and decide**
   - Sum margins across all medications per scenario
   - Compare |scenario_B − scenario_A| against threshold
   - **Recommendation enum**: Verify exact format - commonly `keep_45_day`, `switch_to_90_day` or `keep_45_day_cycle`, `switch_to_90_day_cycle`

## Critical Differences from Standard Refill Analysis

| Aspect | Mailer Program | Standard Therapy Analysis |
|--------|---------------|---------------------------|
| Cost file | `compound_cost.csv` with `mailer_format` | `acquisition_cost.csv` with `canister_size` |
| Packaging | Join on `mailer_format` → variable cost | Join on container size → fixed cost |
| Payment | Split: `base_payment` + `service_fee` | Single: `reimbursement_per_fill` |
| Scenarios | Often 45/90 day cycles | Often 30/90 or 28/56 day cycles |

## Anti-Patterns

- **Don't forget service fees** - They're separate from base payment, not included in it
- **Don't use therapy-based column names** - Mailer programs use `medication` not `therapy`
- **Don't assume payment scales with fill frequency** - Check if total_payment × fills makes sense; often it doesn't scale proportionally
- **Don't hardcode scenario names** - Verify if output expects `45_day` vs `45_day_cycle`
- **Don't trust low margin results** - If 90-day margin seems implausibly low, re-verify: service fees included? mailer costs applied? fill counts correct?

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| 90-day margin << 45-day margin unexpectedly | Service fee omitted from payment | Add `base_payment + service_fee` |
| Negative margins for multiple drugs | Payment calculation error or high mailer costs | Verify total_payment = base + fee; check mailer_cost lookup |
| Verifier rejects recommendation format | Wrong enum value | Check if schema wants `_cycle` suffix or different prefix |
| Margin difference seems wrong | Fill frequency math | 365/45=8.11→8 fills, 365/90=4.06→4 fills |

## Verification Checklist

- [ ] Service fees added to base payments for total per-fill revenue
- [ ] Mailer costs looked up by `mailer_format` not medication name
- [ ] Annual drug cost identical across scenarios (sanity check)
- [ ] `medication` key used not `therapy`
- [ ] Recommendation enum matches verifier expectations exactly
- [ ] Margin calculations include: revenue − drug_cost − mailer_cost

## References

- See `references/mailer-schemas.md` for payment structure variants
- See `scripts/calculate_mailer_margins.py` for reference implementation