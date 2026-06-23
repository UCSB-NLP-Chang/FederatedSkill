---
name: pharmacy-margin-analysis
description: Analyze pharmacy therapy margins across different dispensing cycles (any fill sizes or card cycles). Use when task involves acquisition costs, reimbursement calculations, packaging/vial/blister/mailer costs, or comparing financial outcomes across dispensing scenarios. Handles vial-based dispensing, blister card synchronization programs, and mailer-based programs.
---

# Pharmacy Dispensing Margin Analysis

## When to Use
- Tasks comparing any refill cycle economics (28-day, 30-day, 45-day, 56-day, 90-day, 100-day, etc.)
- Calculating annual margins from acquisition, packaging, and reimbursement data
- Multi-file CSV joins involving medication costs and reimbursements
- Blister card synchronization program analysis
- Mailer-based dispensing program analysis
- Deciding between fill/cycle policies based on revenue/margin thresholds

## Packaging Models

### Vial-Based Dispensing
- Container size (drams) determines packaging cost
- Join key: `canister_size_units` or `vial_size_drams`
- Cost per vial varies by size
- Common for specialty medications

### Blister Card Packaging
- Card count per medication determines packaging cost
- Join key: `blister_card_count` or `cards_per_fill`
- Cost per card may vary by card count
- Common for synchronization programs

### Mailer-Based Dispensing
- Mailer format determines packaging cost
- Join key: `mailer_format` (string values like "standard", "buffered", "secure")
- Cost per mailer varies by format type
- Common for compound/specialty mail-order programs
- **Revenue may have multiple components**: base_payment + service_fee (sum them for total reimbursement)

## Input Data Structure
Expect CSV files with these concepts (column names may vary):
- **Acquisition/Wholesale cost**: medication name, price per unit (often per 1000 tablets/capsules/doses), packaging indicator (container size OR card count OR mailer format)
- **Packaging cost**: packaging indicator, cost per unit
- **Revenue/Reimbursement**: medication name, payment per fill/cycle for N patients (may be split into base_payment + service_fee)

### Common Column Name Variants
| Concept | Possible Column Names |
|---------|----------------------|
| Medication | `therapy`, `medication`, `drug` |
| Price per 1000 | `price_per_1000_doses_usd`, `price_per_1000_tablets_usd`, `price_per_1000_capsules_usd` |
| Container size (vials) | `canister_size_units`, `vial_size_drams` |
| Card count (blister) | `blister_card_count`, `cards_per_fill` |
| Mailer format | `mailer_format` |
| Packaging cost | `packaging_cost_usd`, `vial_price_usd`, `card_cost_usd`, `mailer_cost_usd` |
| Revenue - base | `base_payment_per_fill_N_patients_usd`, `reimbursement_per_fill_N_patients_usd` |
| Revenue - service fee | `service_fee_per_fill_N_patients_usd` |

## Calculation Workflow

1. **Identify packaging model**: Check for vial-size columns vs card-count columns vs mailer-format columns
2. **Identify schema**: Read headers to detect column names for each concept
3. **Join data** on medication name and packaging indicator (size, count, or format)
4. **Sum revenue components**: If both base_payment and service_fee exist, `total_reimbursement = base_payment + service_fee`
5. **Calculate daily dose cost**: `price_per_1000 / 1000` (assume 1 dose/day unless specified)
6. **Calculate per-fill/cycle acquisition cost**: `daily_dose_cost × days_per_fill`
7. **Calculate per-fill/cycle margin**: `total_reimbursement - acquisition_cost - packaging_cost`
8. **Annualize**: `per_fill_margin × fills_per_year × patients_per_medication`

## Key Insight
Reimbursement per fill/cycle is typically **fixed regardless of fill size**. This means:
- More fills per year = more total reimbursement revenue
- Longer fills (100-day vs 90-day, 56-day vs 28-day) reduce fills/year, reducing total reimbursement
- Drug costs scale linearly with days, so savings are proportional
- **Net effect**: Fewer fills usually means less revenue, even with drug cost savings
- **Exception**: If packaging costs are significant, longer cycles can reduce total packaging costs

## Fills Per Year Reference
| Cycle Size | Fills/Year |
|------------|------------|
| 28-day | 13 (or 12 for simplicity) |
| 30-day | 12 |
| 45-day | 8 (365/45 ≈ 8.1) |
| 56-day | 6.5 (or 6 for simplicity) |
| 90-day | 4 |
| 100-day | 3.65 (~3.6 or 4 depending on policy) |

Calculate precisely: `fills_per_year = 365 / days_per_cycle`

## Validation Steps
1. Verify all medications are accounted for in output
2. Check that margin differences make economic sense
3. Ensure output files match expected format (check task for specific schema)
4. Validate numeric precision (2 decimal places for currency)
5. **Confirm patient count** from reimbursement column name or task spec
6. **Verify packaging model detection** - check join completed successfully
7. **Sum all revenue components** - if base_payment and service_fee both exist, add them

## Common Pitfalls
- **Assuming fixed column names** - always read headers first
- **Hardcoding patient count** - extract from column name or task spec
- **Using wrong fills-per-year** - calculate from cycle size (365/days)
- **Not joining packaging cost correctly** - match on correct indicator (size vs count vs format name)
- **Missing medications in final output** - verify join completeness
- **Wrong output file names** - check task spec for exact filenames
- **Confusing vial, blister card, and mailer models** - detect which packaging model applies
- **Incorrect decision threshold logic** - verify comparison direction (greater vs less than)
- **Missing revenue components** - sum base_payment + service_fee if both exist
- **String join key mismatches** - mailer format is a string ("standard"), not numeric

## Troubleshooting

### Schema Mismatch
If column names don't match expected:
1. Read CSV headers with `head -1 file.csv` or Python `csv.DictReader`
2. Map discovered names to expected concepts
3. Proceed with calculation using mapped names

### Patient Count Extraction
Parse from reimbursement column name: `reimbursement_per_fill_300_patients_usd` → 300 patients
Or check task specification for explicit patient count.

### Packaging Model Detection
Check acquisition file columns:
- If `vial_size`, `canister_size`, `drams` → vial-based
- If `blister_card_count`, `card_count`, `cards` → blister card
- If `mailer_format` → mailer-based

### Multi-Component Revenue
If revenue is split across multiple columns:
1. Identify all revenue columns (base_payment, service_fee, etc.)
2. Sum them for total reimbursement per fill
3. Use total in margin calculation

### Output Format Mismatch
If tests fail on output format:
1. Check task spec for exact JSON schema and required fields
2. Verify recommendation format (e.g., `keep_90_day` vs `switch_to_100_day` vs `convert_to_56_day`)
3. Ensure currency formatting matches expected precision
4. Verify decision logic matches threshold comparison direction

## Output Requirements
Check task specification for exact output schema. Typical outputs:
- JSON file with detailed calculations, assumptions, and recommendation
- Markdown summary with key findings and recommendation
- Recommendation field should match expected format exactly

## Anti-Patterns
- Do not assume reimbursement scales with fill size
- Do not skip the packaging cost join
- Do not output partial results before validating all medications
- Do not hardcode column names - detect them from input files
- Do not assume patient count - extract from data or task spec
- Do not assume vial-based model - detect blister card vs vial vs mailer packaging
- Do not assume decision threshold direction - verify "greater than" vs "less than"
- Do not ignore additional revenue columns - sum all revenue components

## Scripts
- `scripts/margin_calculator.py` - Configurable calculator. Run with `--help` for options. Pass column mappings via arguments if schema differs from default. Supports vial, blister card, and mailer models via column detection.
