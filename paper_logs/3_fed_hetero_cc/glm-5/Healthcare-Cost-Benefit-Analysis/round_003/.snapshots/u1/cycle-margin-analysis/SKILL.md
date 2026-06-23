---
name: cycle-margin-analysis
description: Computes and compares annual pharmacy margin/revenue between two refill cycle options using acquisition, packaging/supply, and reimbursement CSVs. Use when tasked with evaluating refill cycle economics, pharmacy margin optimization, syncpack analysis, or formulary switch decisions based on fill frequency. Supports any pair of cycle lengths (e.g., 30 vs 90, 28 vs 56, 90 vs 100), variable patient counts, and diverse packaging types (vials, blister cards, syncpacks).
---

# Cycle Margin Analysis

## When to Use
- Task requires comparing financial impact of two medication refill cycle lengths.
- Input data includes per-medication acquisition costs, packaging/supply costs (keyed by container size), and reimbursement rates.
- Output requires a detailed JSON breakdown and a Markdown summary with a go/no-go decision against a monetary threshold.

## Pre-Flight Checklist (verify BEFORE computing)

Before running any calculations, extract these from the task specification:
- [ ] Patient count (common values: 180, 240, 300)
- [ ] Fills per year for each cycle (e.g., 30-day=12, 90-day=4, 100-day=3, 28-day=12, 56-day=6)
- [ ] Doses/tablets/capsules per fill for each cycle (e.g., 30-day=60, 90-day=90, 100-day=100, 28-day=56, 56-day=112)
- [ ] Reimbursement scope: per-fill/cycle for N patients, NOT per-dose. Note the patient count in the column name.
- [ ] Decision threshold in USD
- [ ] Decision output string format (e.g., `keep_90_day` vs `switch_to_100_day` vs `convert_to_56_day`)

**Critical**: Do NOT assume annual drug cost is identical between models. It is only identical when `fills_A × doses_per_fill_A == fills_B × doses_per_fill_B`. For 90-day (4×90=360) vs 100-day (3×100=300), annual doses differ. For 28-day (12×56=672) vs 56-day (6×112=672), annual doses are identical.

## Workflow
1. **Locate Inputs**: Identify the three CSV files (names vary: acquisition/wholesale_price/ingredient_cost, packaging/vial_price/card_cost, reimbursement).
2. **Inspect Headers**: Read CSV headers to map column names. Common variants:
   - Entity column: `therapy` or `medication`
   - Acquisition: `price_per_1000_doses_usd`, `price_per_1000_tablets_usd`, or `price_per_1000_capsules_usd`
   - Container size: `canister_size_units`, `vial_size_drams`, or `blister_card_count`
   - Supply cost: `packaging_cost_usd`, `vial_price_usd`, or `card_cost_usd`
   - Reimbursement: `reimbursement_per_fill_N_patients_usd` or `reimbursement_per_cycle_N_patients_usd` (treat `per_cycle` identically to `per_fill`)
3. **Run Computation**: Execute `scripts/compute_margin.py` with appropriate arguments.
   ```bash
   python3 scripts/compute_margin.py \
     --acquisition <path> --packaging <path> --reimbursement <path> \
     --threshold 9000 --output-dir . \
     --patients 180 \
     --fills-a 12 --fills-b 6 \
     --doses-a 56 --doses-b 112 \
     --label-a 28_day --label-b 56_day \
     --entity-col medication \
     --price-col price_per_1000_capsules_usd \
     --container-col blister_card_count \
     --supply-col card_cost_usd \
     --reimb-col reimbursement_per_cycle_180_patients_usd
   ```
4. **Verify Outputs**: Check that `cycle_margin_analysis.json` and `cycle_margin_summary.md` are generated.
5. **Review Decision**: The script outputs the appropriate keep/switch/convert decision based on whether the absolute margin difference exceeds the threshold.

## Key Formulas (with units)

- **Annual Drug Cost [USD]**: `price_per_1000 [USD/1000] / 1000 × doses_per_fill [doses] × fills_per_year [fills] × patients`
  - This CAN differ between models if total annual doses differ.
- **Annual Supply Cost [USD]**: `supply_cost_per_container [USD] × fills_per_year [fills] × patients`
- **Annual Reimbursement [USD]**: `reimbursement_per_fill [USD/fill for N patients] × fills_per_year [fills]`
  - Reimbursement is already for the full patient cohort; do NOT multiply by patient count again.
- **Annual Margin/Revenue [USD]**: `Reimbursement - Drug Cost - Supply Cost`
- **Decision Rule**: If `|Margin_B - Margin_A| > threshold`, choose the higher margin model. Otherwise, default to keeping model A.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, CSV, Excel). Pass raw float values directly. Let the verifier's
tolerance decide acceptable precision.

## Anti-Patterns
- Do NOT assume annual drug cost is identical between cycle models — verify by computing `fills × doses_per_fill` for each.
- Do NOT use `fills_per_year = 365/N` approximations; use exact integers from the task (12, 6, 4, 3, etc.).
- Do NOT multiply reimbursement by patient count; it is already per-fill/cycle for the entire cohort.
- Do NOT multiply supply cost by container size; it is already per container.
- Do NOT forget to divide `price_per_1000` by 1000 before multiplying by doses.
- Do NOT assume CSV column names; always inspect headers first.
- Avoid inline Python for this calculation; use the bundled script to prevent errors.

## Troubleshooting
- **Missing CSV columns**: Inspect headers with `head -1 <file>` and pass correct column names via CLI args.
- **Negative margins**: Expected in pharmacy models; focus on the *difference* between models.
- **Container size join mismatch**: The script joins supply cost by converting container size to string for matching. Verify types align.
- **Reimbursement column naming**: If the CSV uses `per_cycle` instead of `per_fill`, pass it directly to `--reimb-col`. The math is identical.
