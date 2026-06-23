---
name: syncpack-cycle-analysis
description: Analyzes medication packaging cycle economics (28-day vs 56-day) using ingredient, card cost, and reimbursement CSVs. Use when tasked with computing annual margins, packaging savings, and making a cycle conversion decision based on a financial threshold.
---

# SyncPack Cycle Analysis

## Overview
Compute annual financial margins for 28-day and 56-day medication packaging cycles across 180 patients per medication. Output a detailed JSON breakdown and a concise Markdown summary.

## Execution
1. Place `ingredient_cost.csv`, `card_cost.csv`, and `reimbursement.csv` in the working directory.
2. Run `python3 scripts/compute_syncpack.py [base_dir] [threshold]` (defaults to `/root` and `$9000`).
3. Verify outputs match the schema and line-count constraints below.

## Key Formulas & Constants
- **Patients per medication**: 180
- **Capsules per day**: 2
- **28-day cycle**: 56 capsules/fill, 12 fills/year
- **56-day cycle**: 112 capsules/fill, 6 fills/year
- **Annual Drug Cost**: `(caps_per_fill / 1000) * price_per_1000 * fills_per_year * 180` (identical for both cycles)
- **Annual Packaging Cost**: `card_cost * fills_per_year * 180`
- **Annual Reimbursement**: `reimbursement_per_cycle * fills_per_year`
- **Annual Margin**: `reimbursement - drug_cost - packaging_cost`
- **Decision Rule**: If `abs(margin_56 - margin_28) < threshold`, recommend `convert_to_56_day`, else `keep_28_day`.

## Output Requirements
- **JSON (`syncpack_analysis.json`)**: Sorted alphabetically by medication. All currency values rounded to 2 decimals. Must include `assumptions`, `medications` array, and `totals`.
- **Markdown (`syncpack_summary.md`)**: Exactly 4-8 non-empty lines. Must state total margins for both cycles, absolute difference, threshold comparison, and final decision.

## Anti-Patterns
- Do not manually calculate values in the prompt; use the provided script to avoid floating-point or rounding errors.
- Do not assume annual drug costs differ between cycles; total annual capsules are identical (672 per patient).
- Ensure the summary strictly adheres to the 4-8 non-empty line constraint.

## Troubleshooting
- If the script fails due to missing CSV columns, verify column names exactly match: `medication`, `price_per_1000_capsules_usd`, `blister_card_count`, `card_cost_usd`, `reimbursement_per_cycle_180_patients_usd`.
- If totals mismatch, verify that `card_cost.csv` maps `blister_card_count` to `card_cost_usd` correctly before running.