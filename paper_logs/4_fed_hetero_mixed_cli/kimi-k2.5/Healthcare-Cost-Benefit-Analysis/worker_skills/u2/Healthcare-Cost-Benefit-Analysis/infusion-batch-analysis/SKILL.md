---
name: infusion-batch-analysis
description: Analyzes medication infusion delivery economics comparing 7-day vs 14-day cycles using therapy catalog JSON, bag supply cost CSV, delivery payment CSV, and patient override CSV. Use when tasked with computing annual margins, supply savings, and making a delivery cycle conversion decision based on a financial threshold.
---

# Infusion Batch Analysis

## Overview
Compute annual financial margins for 7-day and 14-day infusion delivery cycles across active patients per therapy. Output a detailed JSON breakdown and a concise Markdown summary.

## Execution
1. Place `therapy_catalog.json`, `bag_supply_cost.csv`, `delivery_payment.csv`, and `patient_overrides.csv` in the working directory.
2. Run `python3 scripts/compute_infusion_batch.py [base_dir] [threshold]` (defaults to `/root` and `$15000`).
3. Verify outputs match the schema and line-count constraints below.

## Key Formulas & Constants
- **7-day cycle**: 52 deliveries/year, 7 days/delivery
- **14-day cycle**: 26 deliveries/year, 14 days/delivery
- **Total days/year**: 364 (identical for both cycles)
- **Annual Drug Cost**: `(drug_cost_per_1000_mg / 1000) * dose_mg_per_day * 364 * active_patients` (identical for both cycles)
- **Annual Supply Cost**: `bag_supply_cost * deliveries_per_year * active_patients`
- **Annual Revenue**: `payment_per_delivery * deliveries_per_year * active_patients`
- **Annual Margin**: `revenue - drug_cost - supply_cost`
- **Decision Rule**: If `abs(margin_14 - margin_7) < threshold`, recommend `move_to_14_day`, else `keep_7_day`.

## Data Resolution Rules
- **In-Scope Therapies**: Only include therapies where `include_in_review: true` in `therapy_catalog.json`.
- **Patient Overrides**: For each `therapy_code`, select the row with `status: "approved"` and the highest `revision`. Use its `active_patients` count.
- **Payment Matching**: `delivery_payment.csv` uses `therapy_label`. Match it to `therapy_name` or any value in `aliases` from the catalog.
- **Bag Costs**: Map `bag_size_ml` from the catalog to `bag_supply_cost_usd` in the CSV.

## Output Requirements
- **JSON (`infusion_batch_analysis.json`)**: Sorted alphabetically by `therapy_code`. All currency values rounded to 2 decimals. Must include `assumptions`, `therapies` array, and `totals`.
- **Markdown (`infusion_batch_summary.md`)**: Exactly 4-8 non-empty lines. Must state total margins for both cycles, absolute difference, and final decision.

## Anti-Patterns
- Do not manually calculate values; use the provided script to avoid floating-point or alias-matching errors.
- Do not assume annual drug costs differ between cycles; total annual days (364) are identical.
- Ensure `patient_overrides.csv` correctly filters for `approved` status and highest revision per therapy before computing.
- Use `python3` explicitly.

## Troubleshooting
- If the script fails due to missing therapies in `delivery_payment.csv`, verify `therapy_label` matches `therapy_name` or `aliases` exactly.
- If totals mismatch, verify that `patient_overrides.csv` contains an approved revision for every in-scope therapy.
