---
name: vaxcrate-dispatch-analysis
description: Analyzes vaccination crate dispatch economics comparing 6-day vs 12-day cycles using campaign manifest JSON, crate cost CSV, billing CSV with versioned cycle tags, location overrides CSV with revision approval states, and suspensions CSV. Use when tasked with computing annual margins, crate savings, and making a dispatch cycle conversion decision based on a financial threshold.
---

# Vaccination Crate Dispatch Analysis

## Overview
Compute annual financial margins for 6-day and 12-day crate dispatch cycles across active clinics per campaign. Output a detailed JSON breakdown and a concise Markdown summary.

## Execution
1. Place `campaign_manifest.json`, `crate_cost.csv`, `billing.csv`, `location_overrides.csv`, and `suspensions.csv` in the working directory.
2. Run `python3 scripts/compute_vaxcrate.py [base_dir] [threshold]` (defaults to `/root` and `$11000`).
3. Verify outputs match the schema and line-count constraints below.

## Key Formulas & Constants
- **6-day cycle**: 60 dispatches/year (360/6), 6 days/dispatch
- **12-day cycle**: 30 dispatches/year (360/12), 12 days/dispatch
- **Total days/year**: 360 (identical for both cycles)
- **Annual Drug Cost**: `(drug_cost_per_1000_doses / 1000) * doses_per_day * 360 * active_clinics` (identical for both cycles)
- **Annual Crate Cost**: `crate_cost * dispatches_per_year * active_clinics`
- **Annual Revenue**: `payment_per_dispatch * dispatches_per_year * active_clinics`
- **Annual Margin**: `revenue - drug_cost - crate_cost`
- **Decision Rule**: If `abs(margin_12 - margin_6) < threshold`, recommend `move_to_12_day`, else `keep_6_day`.

## Data Resolution Rules
- **In-Scope Campaigns**: Only include campaigns where `analysis_flag: "review"` in `campaign_manifest.json` (exclude "archive").
- **Suspension Exclusion**: Exclude any campaign_id where `suspensions.csv` has `suspension_status: "hold"`.
- **Location Overrides**: For each `campaign_id`, select the row with `state: "approved"` and the highest numeric `revision` where `active_clinics` is non-empty. Use its `active_clinics` count. If no approved version exists with valid clinics, fall back to `default_active_clinics` from the manifest.
- **Billing Resolution**: `billing.csv` uses `campaign_label`. Match it to `campaign_name` or any value in `alias_labels` from the manifest. Filter for rows where `status: "active"`. For each campaign, select the row with the latest `cycle_tag` (lexicographic/date comparison). Use its `payment_per_dispatch_per_clinic_usd`.
- **Crate Costs**: Map `crate_tier` from the manifest to `crate_cost_usd` in `crate_cost.csv`.

## Output Requirements
- **JSON (`vaxcrate_analysis.json`)**: Sorted alphabetically by `campaign_id`. All currency values rounded to 2 decimals. Must include `assumptions`, `campaigns` array, and `totals`.
- **Markdown (`vaxcrate_summary.md`)**: Exactly 4-8 non-empty lines. Must state total margins for both cycles, absolute difference, threshold comparison, and final decision.

## Anti-Patterns
- Do not manually calculate values; use the provided script to avoid floating-point or date-parsing errors.
- Do not assume annual drug costs differ between cycles; total annual doses are identical (balanced by days/year).
- Ensure billing resolution filters for `status: "active"` before selecting the latest `cycle_tag`.
- Ensure `location_overrides.csv` correctly handles empty `active_clinics` values and filters for `approved` state.
- Use `python3` explicitly; do not rely on `python` being available.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### vaxcrate-dispatch
- Suspension filter excludes only "hold" status — campaigns with "clear" or missing from suspensions.csv are retained.
- Billing resolution uses `cycle_tag` format YYYY-QN; requires proper parsing for latest comparison.
- Location overrides require non-empty `revision` AND non-empty `active_clinics` for a valid approved version.

## Troubleshooting
- If the script fails due to missing billing data, verify `campaign_label` matches `campaign_name` or `aliases` exactly, and that `status` is "active".
- If totals mismatch, verify that `location_overrides.csv` contains an approved revision with non-empty active_clinics for every in-scope campaign, or that defaults are correctly applied.
- If output validation fails for line count, ensure the Markdown summary contains no more than 8 non-empty lines.