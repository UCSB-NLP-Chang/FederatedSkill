---
name: cycle-margin-analysis
description: Computes and compares annual pharmacy margin for 30-day vs 90-day refill cycles using acquisition, packaging, and reimbursement CSVs. Use when tasked with evaluating refill cycle economics, pharmacy margin optimization, or formulary switch decisions based on fill frequency.
---

# Cycle Margin Analysis

## When to Use
- Task requires comparing financial impact of 30-day vs 90-day medication refill cycles.
- Input data includes per-therapy acquisition costs, packaging costs (keyed by canister size), and reimbursement rates.
- Output requires a detailed JSON breakdown and a Markdown summary with a go/no-go decision against a monetary threshold.

## Workflow
1. **Locate Inputs**: Identify the three CSV files: `acquisition_cost.csv`, `packaging_cost.csv`, `reimbursement.csv`.
2. **Run Computation**: Execute `scripts/compute_margin.py` with the paths to the three CSVs and the decision threshold.
   ```bash
   python3 scripts/compute_margin.py --acquisition <path> --packaging <path> --reimbursement <path> --threshold 12000 --output-dir .
   ```
3. **Verify Outputs**: Check that `cycle_margin_analysis.json` and `cycle_margin_summary.md` are generated in the output directory.
4. **Review Decision**: The script outputs `keep_30_day` or `switch_to_90_day` based on whether the absolute margin difference exceeds the threshold.

## Key Assumptions & Formulas
- **Patients per therapy**: 240
- **Fills per year**: 12 (30-day), 4 (90-day)
- **Doses per fill**: 60 (30-day), 180 (90-day)
- **Annual Drug Cost**: Identical for both models (same total annual dose volume).
- **Annual Packaging Cost**: `packaging_cost * fills_per_year * patients`
- **Annual Reimbursement**: `reimbursement_per_fill * fills_per_year`
- **Annual Margin**: `Reimbursement - (Drug Cost + Packaging Cost)`
- **Decision Rule**: If `|Margin_90 - Margin_30| > threshold`, choose the higher margin model. Otherwise, default to `keep_30_day`.

## Data Mapping Notes
- `packaging_cost.csv` is keyed by `canister_size_units`, not therapy name. The script automatically joins it to `acquisition_cost.csv` using the canister size.
- `reimbursement.csv` provides aggregate reimbursement for 240 patients per fill. Do not multiply by patient count again.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

Note: The bundled script handles rounding consistently for display purposes.
When writing custom output, prefer full precision.

## Anti-Patterns
- Do not calculate drug cost differently for 30-day vs 90-day; annual dose volume is constant.
- Avoid inline Python for this calculation; use the bundled script to prevent escape sequence warnings and ensure consistent rounding.
- Do not assume all CSVs share the same primary key. Verify headers before merging.
- **WRONG**: `packaging_cost * canister_size_units` — packaging cost is per canister, not multiplied by canister size.
- **RIGHT**: `packaging_cost * fills_per_year * patients` — packaging cost multiplied by fill count and patient count only.

## Known invariants (by sub-task)

### pharmacy-refill-cycle-margin
- Output JSON must include `margin_difference_90_minus_30_usd` field (exact field name).
- Decision strings must be exactly `keep_30_day` or `switch_to_90_day`.
- All therapies in acquisition_cost.csv must appear in output.

## Troubleshooting
- **Missing CSV columns**: Verify headers match `therapy`, `price_per_1000_doses_usd`, `canister_size_units`, `packaging_cost_usd`, `reimbursement_per_fill_240_patients_usd`.
- **Negative margins**: Expected in pharmacy models; the script handles negative values correctly. Focus on the *difference* between models.
