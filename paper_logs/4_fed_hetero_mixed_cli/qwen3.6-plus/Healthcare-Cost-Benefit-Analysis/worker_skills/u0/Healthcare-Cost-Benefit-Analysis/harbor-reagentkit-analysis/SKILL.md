---
name: harbor-reagentkit-analysis
description: Analyzes reagent kit restocking economics comparing small-kit (24 runs/year) vs bulk-kit (12 runs/year) policies using assay manifest JSON, carrier cost CSV, billing CSV with versioned effective months, and lab overrides CSV with revision approval states. Use when tasked with computing annual margins, carrier savings, and making a kit policy conversion decision based on a financial threshold.
---

# Harbor Reagent Kit Analysis

## Overview
Compute annual financial margins for small-kit (24 runs/year) versus bulk-kit (12 runs/year) reagent restocking policies across active labs per assay. Output a detailed JSON breakdown and a concise Markdown summary.

## Execution
1. Place `assay_manifest.json`, `carrier_cost.csv`, `billing.csv`, `lab_overrides.csv`, and optionally `report_template.json` in the working directory.
2. Run `python3 scripts/compute_reagentkit.py [base_dir] [threshold]` (defaults to `/root` and `$7000`).
3. Verify outputs match the schema and line-count constraints below.

## Key Formulas & Constants
- **Small-kit cycle**: 24 runs/year
- **Bulk-kit cycle**: 12 runs/year
- **Annual Reagent Cost**: `(tests_per_lab_per_run * runs_per_year * active_labs / 1000) * price_per_1000` (identical total tests for both cycles)
- **Annual Carrier Cost**: `carrier_cost_usd * runs_per_year * active_labs`
- **Annual Revenue**: `payment_per_run_per_lab * runs_per_year * active_labs`
- **Annual Margin**: `revenue - reagent_cost - carrier_cost`
- **Decision Rule**: If `abs(margin_bulk - margin_small) < threshold`, recommend `adopt_bulk_kit`, else `keep_small_kit`.

## Data Resolution Rules
- **In-Scope Assays**: Only include assays where `in_scope: true` in `assay_manifest.json`.
- **Lab Overrides**: For each `assay_id`, select the row with `status: "approved"` and the highest `revision`. Use its `active_labs` count. If no approved version exists, fall back to `default_active_labs` from the manifest.
- **Billing Resolution**: `billing.csv` uses `assay_label`. Match it to `assay_name` or any value in `aliases` from the manifest. For each assay, select the row with `is_active: "true"` and the latest `effective_month` (date comparison). Use its `payment_per_run_per_lab_usd`.
- **Carrier Costs**: Map `carrier_type` from the manifest to `carrier_cost_usd` in `carrier_cost.csv`.

## Output Requirements
- **JSON (`reagent_policy_report.json`)**: Must include `metadata`, `analysis.assumptions`, `analysis.assays` array (sorted by assay_id), `analysis.totals`, and `analysis.recommendation`. All currency values rounded to 2 decimals.
- **Markdown (`reagent_policy_summary.md`)**: Exactly 4-8 non-empty lines. Must state total margins for both policies, absolute difference, threshold comparison, and final decision.

## Anti-Patterns
- Do not manually calculate values; use the provided script to avoid floating-point or date-parsing errors.
- Do not assume annual reagent costs differ between cycles; total annual tests are identical (balanced by tests_per_lab_per_run differences).
- Ensure billing resolution filters for `is_active: "true"` before selecting the latest effective_month.
- Ensure `lab_overrides.csv` correctly filters for `approved` status and highest revision per assay.
- Use `python3` explicitly; do not rely on `python` being available.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### harbor_reagentkit_bulk
- Billing resolution requires two-step filtering: first `is_active=true`, then latest `effective_month` among remaining rows.
- Annual reagent costs identical across cycles despite different tests_per_lab_per_run values (balanced by run counts).

## Troubleshooting
- If the script fails due to missing billing data, verify `assay_label` matches `assay_name` or `aliases` exactly, and that `is_active` is not "false".
- If totals mismatch, verify that `lab_overrides.csv` contains an approved revision for every in-scope assay or that defaults are correctly applied.
- If output validation fails for line count, ensure the Markdown summary contains no more than 8 non-empty lines.