---
name: mailer-policy-analysis
description: Analyzes medication mailer policy economics (45-day vs 90-day fill cycles) using compound cost, mailer cost, base payment, and service fee CSVs. Use when tasked with computing annual margins, mailer savings, and making a cycle conversion decision based on a financial threshold.
---

# Mailer Policy Analysis

## Overview
Compute annual financial margins for 45-day and 90-day medication fill cycles across 150 patients per medication. Output a detailed JSON breakdown and a concise Markdown summary.

## Execution
1. Place `compound_cost.csv`, `mailer_cost.csv`, `base_payment.csv`, and `service_fee.csv` in the working directory.
2. Run `python3 scripts/compute_mailer_policy.py [base_dir] [threshold]` (defaults to `/root` and `$8500`).
3. Verify outputs match the schema and line-count constraints below.

## Key Formulas & Constants
- **Patients per medication**: 150
- **45-day cycle**: 45 doses/fill, 8 fills/year
- **90-day cycle**: 90 doses/fill, 4 fills/year
- **Annual Drug Cost**: `(price_per_1000 / 1000) * patients * fills * doses_per_fill` (identical for both cycles)
- **Annual Mailer Cost**: `mailer_cost * patients * fills`
- **Annual Payment**: `(base_payment + service_fee) * fills`
- **Annual Margin**: `payment - drug_cost - mailer_cost`
- **Decision Rule**: If `abs(margin_90 - margin_45) < threshold`, recommend `switch_to_90_day`, else `keep_45_day`.

## Output Requirements
- **JSON (`mailer_policy_analysis.json`)**: Sorted alphabetically by medication. All currency values rounded to 2 decimals. Must include `assumptions`, `medications` array, and `totals`.
- **Markdown (`mailer_policy_summary.md`)**: Exactly 4-8 non-empty lines. Must state total margins for both cycles, absolute difference, threshold comparison, and final decision.

## Anti-Patterns
- Do not manually calculate values in the prompt; use the provided script to avoid floating-point or rounding errors.
- Do not assume annual drug costs differ between cycles; total annual doses are identical (360 per patient).
- Ensure the summary strictly adheres to the 4-8 non-empty line constraint.
- Use `python3` explicitly; `python` may not be available in the environment.

## Troubleshooting
- If the script fails due to missing CSV columns, verify column names exactly match: `medication`, `price_per_1000_doses_usd`, `mailer_format`, `mailer_cost_usd`, `base_payment_per_fill_150_patients_usd`, `service_fee_per_fill_150_patients_usd`.
- If totals mismatch, verify that `mailer_cost.csv` maps `mailer_format` to `mailer_cost_usd` correctly before running.