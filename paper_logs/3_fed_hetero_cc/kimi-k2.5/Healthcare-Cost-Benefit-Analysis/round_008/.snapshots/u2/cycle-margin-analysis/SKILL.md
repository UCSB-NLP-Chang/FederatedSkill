---
name: cycle-margin-analysis
description: Computes and compares annual pharmacy margin/revenue between two refill cycle options using acquisition, packaging/supply, and reimbursement CSVs. Use when tasked with evaluating refill cycle economics, pharmacy margin optimization, syncpack analysis, mailer policy, or formulary switch decisions based on fill frequency. Supports any pair of cycle lengths (e.g., 30 vs 90, 28 vs 56, 45 vs 90, 90 vs 100), variable patient counts, and diverse packaging types (vials, blister cards, syncpacks, mailers). For home infusion delivery batching with per-therapy patient counts and dose-mg-per-day drug costing, use infusion-batch-analysis instead.
---

# Cycle Margin Analysis

## STOP — Read This First

**Do NOT compute inline.** This skill includes a bundled script (`scripts/compute_margin.py`) that handles all joins, column mapping, and precision calculations. Running Python inline will produce errors. Use the script.

## When to Use
- Task requires comparing financial impact of two medication refill cycle lengths.
- Input data includes per-medication acquisition costs, packaging/supply costs, and reimbursement rates.
- Output requires a detailed JSON breakdown and a Markdown summary with a go/no-go decision against a monetary threshold.
- **Not for infusion delivery batching** — use `infusion-batch-analysis` skill when patient counts are per-therapy, drug cost is dose-mg-per-day based, or revenue is per-patient per-delivery.

## Pre-Flight Checklist (verify BEFORE computing)

Before running any calculations, extract these from the task specification:
- [ ] Patient count (common values: 150, 180, 240, 300)
- [ ] Fills per year for each cycle (e.g., 30-day=12, 45-day=8, 90-day=4, 100-day=3, 28-day=12, 56-day=6)
- [ ] Doses/tablets/capsules per fill for each cycle (e.g., 30-day=60, 45-day=45, 90-day=90, 100-day=100, 28-day=56, 56-day=112)
- [ ] Reimbursement scope: per-fill/cycle for N patients, NOT per-dose. Note the patient count in the column name.
- [ ] Decision threshold in USD
- [ ] Decision output string format (e.g., `keep_90_day` vs `switch_to_100_day` vs `convert_to_56_day`)

**Critical**: Do NOT assume annual drug cost is identical between models. It is only identical when `fills_A × doses_per_fill_A == fills_B × doses_per_fill_B`. For 90-day (4×90=360) vs 100-day (3×100=300), annual doses differ. For 28-day (12×56=672) vs 56-day (6×112=672), annual doses are identical. For 45-day (8×45=360) vs 90-day (4×90=360), annual doses are identical.

## Input Data Patterns

### Pattern A: Three-CSV Structure (Standard)
- **Acquisition CSV**: Entity + price_per_1000 + container size
- **Packaging CSV**: Container size + supply cost
- **Reimbursement CSV**: Entity + reimbursement_per_fill
- Join: Entity links acquisition↔reimbursement; container size links acquisition↔packaging

### Pattern B: Four-CSV Structure (Split Reimbursement)
- **Acquisition CSV**: Entity + price_per_1000 + format/type column
- **Supply CSV**: Format/type + supply cost (e.g., mailer_cost)
- **Base Payment CSV**: Entity + base_payment_per_fill
- **Service Fee CSV**: Entity + service_fee_per_fill
- Join: Entity links acquisition↔payments; format/type links acquisition↔supply
- **Total reimbursement** = base_payment + service_fee (sum before margin calculation)

### Pattern C: Multiple Reimbursement Components
- Reimbursement may be split across multiple CSVs (base_payment, service_fee, dispensing_fee, etc.)
- Always sum all per-fill payment components before calculating annual reimbursement
- Check column names for patient count suffix (e.g., `_150_patients_usd`)

## Workflow
1. **Locate Inputs**: Identify all CSV files and their roles (acquisition, packaging/supply, reimbursement components).
2. **Inspect Headers**: Read CSV headers to map column names. Common variants:
   - Entity column: `therapy`, `medication`, or `drug`
   - Acquisition: `price_per_1000_doses_usd`, `price_per_1000_tablets_usd`, or `price_per_1000_capsules_usd`
   - Container/format column: `canister_size_units`, `vial_size_drams`, `blister_card_count`, or `mailer_format`
   - Supply cost: `packaging_cost_usd`, `vial_price_usd`, `card_cost_usd`, or `mailer_cost_usd`
   - Reimbursement: `reimbursement_per_fill_N_patients_usd`, `base_payment_per_fill_N_patients_usd`, `service_fee_per_fill_N_patients_usd`
3. **Determine Join Keys**: Identify which column links acquisition to supply costs (container size OR format/type).
4. **Sum Reimbursement Components**: If reimbursement is split across multiple CSVs, sum all per-fill payment columns.
5. **Run Computation**: Execute `scripts/compute_margin.py` with appropriate arguments.
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
6. **For Split Reimbursement**: If reimbursement is in separate CSVs, merge them first or use inline computation.
7. **Verify Outputs**: Check that `cycle_margin_analysis.json` and `cycle_margin_summary.md` are generated.
8. **Review Decision**: The script outputs the appropriate keep/switch/convert decision based on whether the absolute margin difference exceeds the threshold.

## Key Formulas (with units)

- **Annual Drug Cost [USD]**: `price_per_1000 [USD/1000] / 1000 × doses_per_fill [doses] × fills_per_year [fills] × patients`
  - This CAN differ between models if total annual doses differ.
- **Annual Supply Cost [USD]**: `supply_cost_per_container [USD] × fills_per_year [fills] × patients`
- **Annual Reimbursement [USD]**: `total_payment_per_fill [USD/fill for N patients] × fills_per_year [fills]`
  - Reimbursement is already for the full patient cohort; do NOT multiply by patient count again.
  - If split: `total_payment = base_payment + service_fee + ...`
- **Annual Margin/Revenue [USD]**: `Reimbursement - Drug Cost - Supply Cost`
- **Decision Rule**: If `|Margin_B - Margin_A| > threshold`, choose the higher margin model. Otherwise, default to keeping model A.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, CSV, Excel). Pass raw float values directly. Let the verifier's
tolerance decide acceptable precision.

## Anti-Patterns
- Do NOT assume annual drug cost is identical between cycle models — verify by computing `fills × doses_per_fill` for each.
- Do NOT use `fills_per_year = 365/N` approximations; use exact integers from the task (12, 8, 6, 4, 3, etc.).
- Do NOT multiply reimbursement by patient count; it is already per-fill/cycle for the entire cohort.
- Do NOT multiply supply cost by container size; it is already per container.
- Do NOT forget to divide `price_per_1000` by 1000 before multiplying by doses.
- Do NOT assume CSV column names; always inspect headers first.
- Do NOT assume a single reimbursement CSV; check for split components (base_payment, service_fee, etc.).
- Do NOT assume container size is the join key; check for format/type columns (e.g., `mailer_format`).
- **Do NOT** compute inline — use the bundled script to prevent errors

## Troubleshooting
- **Missing CSV columns**: Inspect headers with `head -1 <file>` and pass correct column names via CLI args.
- **Negative margins**: Expected in pharmacy models; focus on the *difference* between models.
- **Container size join mismatch**: The script joins supply cost by converting container size to string for matching. Verify types align.
- **Reimbursement column naming**: If the CSV uses `per_cycle` instead of `per_fill`, pass it directly to `--reimb-col`. The math is identical.
- **Split reimbursement files**: Merge base_payment and service_fee CSVs before running the script, or compute total reimbursement per medication first.
- **Format-based join (not container size)**: If supply cost is keyed by format/type (e.g., `mailer_format`), ensure the acquisition CSV has a matching column and pass it via `--container-col`.
