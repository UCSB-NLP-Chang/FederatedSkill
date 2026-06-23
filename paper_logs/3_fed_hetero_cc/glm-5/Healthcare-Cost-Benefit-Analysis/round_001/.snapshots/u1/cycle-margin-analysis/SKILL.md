---
name: cycle-margin-analysis
description: Computes and compares annual pharmacy margin for 30-day vs 90-day refill cycles using acquisition, packaging, and reimbursement CSVs. Use when tasked with evaluating refill cycle economics, pharmacy margin optimization, or formulary switch decisions based on fill frequency.
---

# Cycle Margin Analysis

## When to Use
- Task requires comparing financial impact of 30-day vs 90-day medication refill cycles.
- Input data includes per-therapy acquisition costs, packaging costs (often keyed by canister size), and reimbursement rates.
- Output requires a detailed JSON breakdown and a Markdown summary with a go/no-go decision against a monetary threshold.

## Pre-Flight Checklist (verify BEFORE computing)

Before running any calculations, verify these constants:
- [ ] `fills_per_year(30-day) = 12` (exactly 12, not 365/30 approximation)
- [ ] `fills_per_year(90-day) = 4` (exactly 4, not 365/90 approximation)
- [ ] `doses_per_fill(30-day) = 60`
- [ ] `doses_per_fill(90-day) = 180`
- [ ] `patients = 240`
- [ ] `reimbursement` is per-fill for 240 patients, NOT per-dose

If any constant differs from task specification, adjust accordingly.

## Workflow
1. **Locate Inputs**: Identify the three CSV files: `acquisition_cost.csv`, `packaging_cost.csv`, `reimbursement.csv`.
2. **Run Computation**: Execute `scripts/compute_margin.py` with the paths to the three CSVs and the decision threshold.
   ```bash
   python3 scripts/compute_margin.py --acquisition <path> --packaging <path> --reimbursement <path> --threshold 12000 --output-dir .
   ```
3. **Verify Outputs**: Check that `cycle_margin_analysis.json` and `cycle_margin_summary.md` are generated in the output directory.
4. **Review Decision**: The script outputs `keep_30_day` or `switch_to_90_day` based on whether the absolute margin difference exceeds the threshold.

## Key Assumptions & Formulas (with units)

- **Patients per therapy**: 240 (unitless count)
- **Fills per year**: 12 (30-day), 4 (90-day) [fills/year]
- **Doses per fill**: 60 (30-day), 180 (90-day) [doses/fill]
- **Annual Drug Cost [USD]**: Identical for both models (same total annual dose volume).
  - Formula: `price_per_1000_doses [USD/1000 doses] / 1000 * doses_per_fill [doses] * fills_per_year [fills] * patients`
- **Annual Packaging Cost [USD]**: `packaging_cost_usd [USD/canister] * fills_per_year [fills] * patients`
- **Annual Reimbursement [USD]**: `reimbursement_per_fill [USD/fill for 240 patients] * fills_per_year [fills]`
  - NOTE: reimbursement is already for 240 patients; do NOT multiply by patient count again
- **Annual Margin [USD]**: `Reimbursement - Drug Cost - Packaging Cost`
- **Decision Rule**: If `|Margin_90 - Margin_30| > threshold`, choose the higher margin model. Otherwise, default to `keep_30_day`.

## Data Mapping Notes
- `packaging_cost.csv` is typically keyed by `canister_size_units`, not therapy name. The script automatically joins it to `acquisition_cost.csv` using the canister size.
- `reimbursement.csv` usually provides aggregate reimbursement for 240 patients per fill. Do not multiply by patient count again.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-Patterns
- Do not calculate drug cost differently for 30-day vs 90-day; annual dose volume is constant.
- Avoid inline Python for this calculation; use the bundled script to prevent escape sequence warnings and ensure consistent rounding.
- Do not assume all CSVs share the same primary key. Verify headers before merging.
- Do not multiply packaging cost by canister_size_units; packaging cost is already per canister.
- Do not forget to divide `price_per_1000_doses` by 1000 before multiplying by doses.
- Do not assume reimbursement is per dose; it is per fill for the entire patient cohort.
- Do not use `fills_per_year = 365/30`; use exactly 12 and 4 unless task specifies otherwise.

## Known invariants (by sub-task)

### pharmacy-refill-cycle-margin
- Decision output strings must be exactly `keep_30_day` or `switch_to_90_day`.
- Margin difference field must be `margin_difference_90_minus_30_usd` (direction matters).

## Troubleshooting
- **Missing CSV columns**: Verify headers match `therapy`, `price_per_1000_doses_usd`, `canister_size_units`, `packaging_cost_usd`, `reimbursement_per_fill_240_patients_usd`.
- **Negative margins**: Expected in pharmacy models; the script handles negative values correctly. Focus on the *difference* between models.
