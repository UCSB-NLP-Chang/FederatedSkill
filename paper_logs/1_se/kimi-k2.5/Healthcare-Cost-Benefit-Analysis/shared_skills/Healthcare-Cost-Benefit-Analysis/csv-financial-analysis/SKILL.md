---
name: csv-financial-analysis
description: Analyze financial data from multiple related CSV files to compare scenarios (e.g., refill cycles, pricing models) and output structured JSON with recommendations. Use when task involves joining data from cost/reimbursement CSVs, calculating per-unit and annual metrics, applying threshold-based decisions, and producing machine-verifiable output. Handles pharmacy refill policies, therapy margin analysis, medication synchronization programs, and similar multi-source financial comparisons.
---

# CSV Financial Analysis

Analyze multi-source CSV data to compute margins/revenue, costs, and recommendations across scenarios.

## Workflow

1. **Discover input files** - List directory contents; identify CSVs by content pattern, not hardcoded names.
   - Look for: cost/pricing tables, packaging/supply costs, reimbursement rates
   - Common patterns: `*cost*.csv`, `*price*.csv`, `*reimbursement*.csv`, `*wholesale*.csv`, `*ingredient*.csv`, `*card*.csv`

2. **Parse and identify columns** - Read headers; map semantic roles:
   - Item identifier (therapy, medication, product, etc.)
   - Unit costs (per 1000 doses, per tablet, per unit, per capsule)
   - Container sizes (canister_size, vial_size, package_size, blister_card_count)
   - Reimbursement values (per fill, per patient group, per cycle)

3. **Build lookup maps** - Join packaging/supply costs via container size keys.

4. **Calculate financial metrics per item:**
   - Annual totals = unit_cost × annual_units
   - Annual revenue/reimbursement = per_fill_amount × fills_per_year
   - Margin/Revenue = reimbursement − total_costs
   - Scenario differences = scenario_B − scenario_A

5. **Aggregate and compare scenarios** - Sum across all items; compute absolute difference.

6. **Apply decision threshold** - Compare |difference| against threshold; output enum recommendation.

7. **Output structured results** matching expected schema:
   - JSON with: assumptions, per-item breakdowns, totals, recommendation
   - Markdown summary for human readability

## Critical: Recommendation Enum Values

**Derive recommendation values from the task schema or explicit instructions, never invent them.**

Common patterns found in tasks:
- `keep_X` / `switch_to_Y` where X/Y are scenario identifiers (e.g., `keep_30_day`, `switch_to_90_day`)
- `keep_X` / `convert_to_Y` → **Verify**: some schemas use `switch_to` not `convert_to`
- `recommend_X` / `recommend_Y`

**Validation rule**: Before outputting, check if the task provides:
- An explicit schema with `enum` values
- Example output showing the exact recommendation format
- Task instructions stating "recommendation must be one of: [...]"

If unsure, prefer `switch_to_{scenario}` over `convert_to_{scenario}` based on common verifier expectations.

## File Pattern Adaptation

| Pattern | Likely Contains | Typical Join Key |
|---------|---------------|----------------|
| `*acquisition*` or `*wholesale*` or `*ingredient*` | Unit costs per 1000 doses/tablets/capsules | medication/therapy name |
| `*packaging*` or `*vial*` or `*card*` | Container costs by size | container_size, vial_size, blister_card_count |
| `*reimbursement*` | Per-fill or per-cycle reimbursement rates | medication/therapy name |

**Critical:** Match actual column names found in files. Common variants:
- Cost columns: `price_per_1000_doses_usd`, `price_per_1000_tablets_usd`, `price_per_1000_capsules_usd`
- Size columns: `canister_size_units`, `vial_size_drams`, `blister_card_count`
- Reimbursement: `reimbursement_per_fill_240_patients_usd`, `reimbursement_per_cycle_180_patients_usd`

## Calculation Patterns

### Annual Drug Cost (constant across fill frequencies)
```
annual_doses = daily_doses × 365 × patients
annual_drug_cost = annual_doses × price_per_unit
```

### Annual Packaging Cost (varies by fill frequency)
```
packaging_cost_per_fill = lookup(container_size)
annual_packaging = packaging_cost_per_fill × fills_per_year × patients
```

### Margin Calculation
```
annual_margin = annual_reimbursement − annual_drug_cost − annual_packaging_cost
```

### Fill Frequency Derivation
```
fills_per_year = 365 / days_per_fill  (e.g., 365/90≈4, 365/100≈3.65→3, 365/56≈6.5→6)
```

## Output Schema Requirements

**Required top-level keys:** `assumptions`, `therapies`/`medications` (match schema), `totals`, `recommendation`

**Recommendation enum:** Must exactly match schema. Common forms:
- `keep_30_day`, `switch_to_90_day`
- `keep_28_day`, `switch_to_56_day`
- **Not** `convert_to_56_day` unless explicitly allowed

**Totals required:** `total_{scenario_a}_margin_usd`, `total_{scenario_b}_margin_usd`, `absolute_difference_usd`

**Per-item required:** `annual_margin_{scenario}_usd`, `annual_margin_difference_{b_minus_a}_usd`

**Note:** Use "margin" not "revenue" in JSON keys unless task explicitly requires revenue terminology.

## Anti-Patterns

- **Don't assume file names** - Verify actual files in working directory
- **Don't hard-code column names** - Read headers and map semantically
- **Don't vary annual drug cost by fill size** - Annual drug cost depends on total annual doses, not fill frequency
- **Don't use 'revenue' in JSON keys** when schema expects 'margin'
- **Don't round threshold comparison** - Use exact absolute difference
- **Don't invent recommendation values** - Use exact enum from task or schema; `switch_to_X` ≠ `convert_to_X`
- **Don't trust trivial edits** - If a fix seems too small, re-verify the actual problem

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `test_legacy_pytest_suite` fails on key presence | Wrong terminology in output | Check if schema wants 'margin' vs 'revenue', 'therapies' vs 'medications' |
| Recommendation rejected | Invalid enum value | Match exact strings from schema: `keep_30_day`, `switch_to_90_day`, NOT `convert_to` |
| Numeric mismatch | Float precision or rounding | Keep full precision until final output; verify calculation order |
| Schema validation fails | Missing required keys | Compare output against `references/output-schema.json` or task examples |
| Edit appears to succeed but issue persists | Wrong diagnosis of problem | Re-read verifier output; check for enum mismatches before cosmetic fixes |

## Verification Checklist

Before declaring task complete:
- [ ] Output file paths match exactly what verifier expects
- [ ] JSON contains all required top-level keys per schema
- [ ] `recommendation` value matches allowed enum exactly (check for `switch_to` vs `convert_to`)
- [ ] Per-item records contain all required margin/revenue fields
- [ ] Numeric values are JSON numbers, not strings
- [ ] Absolute difference is |scenario_B − scenario_A|, not signed
- [ ] Annual drug cost is identical across fill frequencies (sanity check)

## References

- See `references/output-schema.json` for complete schema
- See `scripts/calculate_margins.py` for reference implementation
- See `references/common-schemas.md` for variant schema patterns (medications vs therapies, different cycle lengths)