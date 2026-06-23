---
name: infusion-batch-analysis
description: Analyzes infusion therapy delivery batch economics (7-day vs 14-day cycles) using therapy catalog JSON, bag supply costs, delivery payments, and patient overrides. Use when tasked with computing annual margins, supply savings, and making a cycle conversion decision based on a financial threshold.
---

# Infusion Batch Analysis

## Overview
Compute annual financial margins for 7-day and 14-day infusion delivery cycles. Filter therapies by `include_in_review` flag, resolve patient counts using highest approved revision, and output a detailed JSON breakdown with a concise Markdown summary.

## Execution
1. Place `therapy_catalog.json`, `bag_supply_cost.csv`, `delivery_payment.csv`, and `patient_overrides.csv` in the working directory.
2. Run `python3 scripts/compute_infusion_batch.py [base_dir] [threshold]` (defaults to `/root` and `$15000`).
3. Verify outputs match the schema and line-count constraints below.

## Key Formulas & Constants
- **Days per year**: 364 (52 weeks × 7 days)
- **7-day cycle**: 52 deliveries/year
- **14-day cycle**: 26 deliveries/year
- **Annual Drug Cost**: `dose_mg_per_day * 364 * (drug_cost_per_1000_mg / 1000) * patients` (identical for both cycles)
- **Annual Supply Cost**: `bag_supply_cost * deliveries_per_year * patients`
- **Annual Revenue**: `payment_per_delivery * deliveries_per_year * patients`
- **Annual Margin**: `revenue - drug_cost - supply_cost`
- **Decision Rule**: If `abs(margin_14 - margin_7) < threshold`, recommend `convert_to_14_day`, else `keep_7_day`.

## Business Rules
- **Therapy filtering**: Only include therapies where `include_in_review: true` in the catalog.
- **Patient count resolution**: From `patient_overrides.csv`, use the highest revision number where `status: approved`. If no approved revision exists, exclude the therapy.
- **Payment matching**: Match `therapy_label` in `delivery_payment.csv` to `therapy_name` or any alias in the therapy catalog.

## Output Requirements
- **JSON (`infusion_batch_analysis.json`)**: Sorted alphabetically by therapy_code. All currency values rounded to 2 decimals. Must include `assumptions`, `therapies` array, and `totals`.
- **Markdown (`infusion_batch_summary.md`)**: Exactly 4-8 non-empty lines. Must state total margins for both cycles, absolute difference, threshold comparison, and final decision.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-Patterns
- Do not manually calculate values in the prompt; use the provided script to avoid floating-point or rounding errors.
- Do not assume annual drug costs differ between cycles; total annual doses are identical (364 days × dose_mg_per_day).
- Do not include therapies with `include_in_review: false`.
- Do not use patient counts from rejected or draft revisions.
- Ensure the summary strictly adheres to the 4-8 non-empty line constraint.

## Known invariants (by sub-task)

### infusion-batch-analysis
- Drug cost identical across cycles (364 days × dose_mg_per_day).
- Patient count: highest approved revision only (status="approved").
- Year length: 364 days (52 weeks), not 365.
- Payment matching: check both `therapy_name` AND `aliases` array.

## Troubleshooting
- If payment lookup fails, verify `therapy_label` in `delivery_payment.csv` matches `therapy_name` or one of the aliases in `therapy_catalog.json`.
- If patient counts seem wrong, check that only `status: approved` rows are used and the highest revision is selected.
- If totals mismatch, verify `bag_supply_cost.csv` maps `bag_size_ml` to `bag_supply_cost_usd` correctly.