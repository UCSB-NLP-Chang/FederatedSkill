---
name: cycle-margin-analysis
description: Computes and compares annual pharmacy margin between two refill cycle options using acquisition, packaging/supply, and reimbursement CSVs. Use when tasked with evaluating refill cycle economics, pharmacy margin optimization, or formulary switch decisions based on fill frequency. Supports any pair of cycle lengths (e.g., 30 vs 90, 90 vs 100) and variable patient counts.
---

# Cycle Margin Analysis

## When to Use
- Task requires comparing financial impact of two medication refill cycle lengths.
- Input data includes per-medication acquisition costs, packaging/supply costs (keyed by container size), and reimbursement rates.
- Output requires a detailed JSON breakdown and a Markdown summary with a go/no-go decision against a monetary threshold.

## Pre-Flight Checklist (verify BEFORE computing)

Before running any calculations, extract these from the task specification:
- [ ] Patient count (common values: 240, 300)
- [ ] Fills per year for each cycle (e.g., 30-day=12, 90-day=4, 100-day=3)
- [ ] Doses/tablets per fill for each cycle (e.g., 30-day=60, 90-day=90, 100-day=100)
- [ ] Reimbursement scope: per-fill for N patients, NOT per-dose. Note the patient count in the column name.
- [ ] Decision threshold in USD
- [ ] Decision output string format (e.g., `keep_90_day` vs `switch_to_100_day`)

**Critical**: Do NOT assume annual drug cost is identical between models. It is only identical when `fills_A × doses_per_fill_A == fills_B × doses_per_fill_B`. For 90-day (4×90=360) vs 100-day (3×100=300), annual doses differ.

## Workflow
1. **Locate Inputs**: Identify the three CSV files (names vary: acquisition/wholesale_price, packaging/vial_price, reimbursement).
2. **Inspect Headers**: Read CSV headers to map column names. Common variants:
   - Entity column: `therapy` or `medication`
   - Acquisition: `price_per_1000_doses_usd` or `price_per_1000_tablets_usd`
   - Container size: `canister_size_units` or `vial_size_drams`
   - Supply cost: `packaging_cost_usd` or `vial_price_usd`
   - Reimbursement: `reimbursement_per_fill_240_patients_usd` or `reimbursement_per_fill_300_patients_usd`
3. **Run Computation**: Execute `scripts/compute_margin.py` with appropriate arguments.
   ```bash
   python3 scripts/compute_margin.py \
     --acquisition <path> --packaging <path> --reimbursement <path> \
     --threshold 16000 --output-dir . \
     --patients 300 \
     --fills-a 4 --fills-b 3 \
     --doses-a 90 --doses-b 100 \
     --label-a 90_day --label-b 100_day \
     --entity-col medication \
     --price-col price_per_1000_tablets_usd \
     --container-col vial_size_drams \
     --supply-col vial_price_usd \
     --reimb-col reimbursement_per_fill_300_patients_usd
   ```
4. **Verify Outputs**: Check that `cycle_margin_analysis.json` and `cycle_margin_summary.md` are generated.
5. **Review Decision**: The script outputs the appropriate keep/switch decision based on whether the absolute margin difference exceeds the threshold.

## Key Formulas (with units)

- **Annual Drug Cost [USD]**: `price_per_1000 [USD/1000] / 1000 × doses_per_fill [doses] × fills_per_year [fills] × patients`
  - This CAN differ between models if total annual doses differ.
- **Annual Supply Cost [USD]**: `supply_cost_per_container [USD] × fills_per_year [fills] × patients`
- **Annual Reimbursement [USD]**: `reimbursement_per_fill [USD/fill for N patients] × fills_per_year [fills]`
  - Reimbursement is already for the full patient cohort; do NOT multiply by patient count again.
- **Annual Margin [USD]**: `Reimbursement - Drug Cost - Supply Cost`
  - **WRONG**: Revenue = Reimbursement only (missing cost subtraction)
  - **RIGHT**: Margin = Reimbursement - Drug Cost - Supply Cost (full calculation)
- **Decision Rule**: If `|Margin_B - Margin_A| > threshold`, choose the higher margin model. Otherwise, default to keeping model A.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, CSV, Excel). Pass raw float values directly. Let the verifier's
tolerance decide acceptable precision.

## Anti-Patterns
- Do NOT assume annual drug cost is identical between cycle models — verify by computing `fills × doses_per_fill` for each.
- Do NOT use `fills_per_year = 365/N` approximations; use exact integers from the task (12, 4, 3, etc.).
- Do NOT multiply reimbursement by patient count; it is already per-fill for the entire cohort.
- Do NOT multiply supply cost by container size; it is already per container.
- Do NOT forget to divide `price_per_1000` by 1000 before multiplying by doses.
- Do NOT assume CSV column names; always inspect headers first.
- Avoid inline Python for this calculation; use the bundled script to prevent errors.

## Known invariants (by sub-task)

### pharmacy-refill-cycle-margin (30-day vs 90-day)
- Decision strings must be exactly `keep_30_day` or `switch_to_90_day`.
- Margin difference field must be `margin_difference_90_minus_30_usd` (exact field name).

### pharmacy-refill-cycle-margin (90-day vs 100-day)
- Decision strings must be exactly `keep_90_day` or `switch_to_100_day`.
- Margin difference field must be `margin_difference_100_minus_90_usd` (exact field name).
- All medications in acquisition/wholesale CSV must appear in output.

## Troubleshooting
- **Missing CSV columns**: Inspect headers with `head -1 <file>` and pass correct column names via CLI args.
- **Negative margins**: Expected in pharmacy models; focus on the *difference* between models.
- **Container size join mismatch**: The script joins supply cost by converting container size to string for matching. Verify types align.
