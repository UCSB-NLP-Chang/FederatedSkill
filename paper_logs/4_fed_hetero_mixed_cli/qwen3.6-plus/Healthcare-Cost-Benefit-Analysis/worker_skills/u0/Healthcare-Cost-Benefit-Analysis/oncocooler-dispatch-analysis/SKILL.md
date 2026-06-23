---
name: oncocooler-dispatch-analysis
description: Analyzes oncology supportive-care cooler dispatch economics comparing 10-day vs 20-day cycles using program catalog JSON, cooler cost CSV, contract payment CSV, and site overrides CSV with versioned approval states. Use when tasked with computing annual margins, cooler savings, and making a dispatch cycle conversion decision based on a financial threshold.
---

# OncoCooler Dispatch Analysis

## Overview
Compute annual financial margins for 10-day and 20-day cooler dispatch cycles across active sites per program. Output a detailed JSON breakdown and a concise Markdown summary.

## Execution
1. Place `program_catalog.json`, `cooler_cost.csv`, `contract_payment.csv`, and `site_overrides.csv` in the working directory.
2. Run `python3 scripts/compute_oncocooler.py [base_dir] [threshold]` (defaults to `/root` and `$10000`).
3. Verify outputs match the schema and line-count constraints below.

## Key Formulas & Constants
- **10-day cycle**: 36 dispatches/year, 10 days/dispatch
- **20-day cycle**: 18 dispatches/year, 20 days/dispatch  
- **Total days/year**: 360 (identical for both cycles)
- **Annual Drug Cost**: `(acquisition_cost_per_1000_units / 1000) * units_per_day * 360 * active_sites` (identical for both cycles)
- **Annual Cooler Cost**: `cooler_cost * dispatches_per_year * active_sites`
- **Annual Revenue**: `payment_per_dispatch * dispatches_per_year * active_sites`
- **Annual Margin**: `revenue - drug_cost - cooler_cost`
- **Decision Rule**: If `abs(margin_20 - margin_10) < threshold`, recommend `move_to_20_day`, else `keep_10_day`.

## Data Resolution Rules
- **In-Scope Programs**: Only include programs where `review_flag: "review"` in `program_catalog.json` (exclude "archive").
- **Site Overrides**: For each `program_code`, select the row with `approval_state: "approved"` and the highest `version_no`. Use its `active_sites` count. If no approved version exists, fall back to `default_active_sites` from the catalog.
- **Payment Matching**: `contract_payment.csv` uses `program_label`. Match it to any value in `known_labels` or `program_name` from the catalog.
- **Cooler Costs**: Map `cooler_type` from the catalog to `cooler_cost_usd` in the CSV.

## Output Requirements
- **JSON (`oncocooler_analysis.json`)**: Sorted alphabetically by `program_code`. All currency values rounded to 2 decimals. Must include `assumptions`, `programs` array, and `totals`.
- **Markdown (`oncocooler_summary.md`)**: Exactly 4-8 non-empty lines. Must state total margins for both cycles, absolute difference, and final decision.

## Anti-Patterns
- Do not manually calculate values; use the provided script to avoid floating-point or alias-matching errors.
- Do not assume annual drug costs differ between cycles; total annual days (360) are identical.
- Ensure `site_overrides.csv` correctly filters for `approved` approval_state and highest version_no per program before computing.
- Use `python3` explicitly; do not rely on `python` being available.

## Troubleshooting
- If the script fails due to missing therapies in `contract_payment.csv`, verify `program_label` matches `program_name` or `known_labels` exactly.
- If totals mismatch, verify that `site_overrides.csv` contains an approved version for every in-scope program or that defaults are correctly applied.
- If output validation fails for line count, ensure the Markdown summary contains no more than 8 non-empty lines.
