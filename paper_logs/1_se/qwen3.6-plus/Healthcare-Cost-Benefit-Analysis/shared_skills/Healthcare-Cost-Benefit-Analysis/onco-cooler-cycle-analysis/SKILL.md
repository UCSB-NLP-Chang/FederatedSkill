---
name: onco-cooler-cycle-analysis
description: Compares 10-day vs 20-day cooler dispatch cycles for oncology supportive care programs. Use when given a program catalog JSON, cooler cost CSV, contract payment CSV, and site overrides CSV to compute annual margins, resolve active sites, and output structured JSON/Markdown analysis with a threshold-based decision.
---

# Oncology Cooler Dispatch Cycle Analysis

## When to Use
- Task provides `program_catalog.json`, `cooler_cost.csv`, `contract_payment.csv`, and `site_overrides.csv`.
- Goal is to compare annual financial margins between 10-day and 20-day dispatch cycles.
- Output must include per-program breakdowns, total margins, absolute difference, and a threshold-based decision.

## Workflow
1. **Verify Inputs**: Ensure all four files are present. Check that `program_catalog.json` contains `review_flag` fields.
2. **Run Computation**: Execute `scripts/compute_cooler_margin.py` with the input paths.
   ```bash
   python3 scripts/compute_cooler_margin.py --catalog program_catalog.json --cooler cooler_cost.csv --payment contract_payment.csv --overrides site_overrides.csv --threshold 10000
   ```
3. **Validate Outputs**: Check that `onco_cooler_analysis.json` and `onco_cooler_summary.md` are generated. Verify JSON structure matches `references/formulas_and_schema.md`.
4. **Review Decision**: The script determines `keep_10_day` or `switch_to_20_day` based on whether the absolute margin difference exceeds the threshold.

## Key Formulas & Assumptions
- **Dispatches/year**: 36 (10-day), 18 (20-day)
- **Days covered/year**: 360 (Identical for both cycles)
- **Annual Drug Cost**: `(cost_per_1000 / 1000) * units_per_day * 360 * active_sites`
- **Annual Cooler Cost**: `cooler_cost * dispatches_per_year * active_sites`
- **Annual Revenue**: `payment_per_dispatch * dispatches_per_year * active_sites`
- **Annual Margin**: `Revenue - Drug Cost - Cooler Cost`
- See `references/formulas_and_schema.md` for detailed derivations, site override resolution, and exact JSON schema.

## Anti-Patterns & Troubleshooting
- **Site Override Resolution**: Do not use the first row. Filter `approval_state == 'approved'` and pick the highest `version_no` per `program_code`. Fallback to `default_active_sites` if no approved override exists.
- **Label Matching**: Payments are keyed by program labels, not codes. Map `known_labels` from the catalog to `program_label` in the payment CSV before joining.
- **In-Scope Filter**: Only process programs where `review_flag` is `"review"`. Exclude `"archive"` or other flags.
- **Drug Cost Invariance**: Total annual drug cost is identical for both cycles (360 days/year). Only cooler costs and revenue scale with dispatch frequency.
- **Threshold Logic**: Decision triggers only if `abs(margin_20 - margin_10) > threshold`. If triggered, pick the higher margin cycle. Otherwise, default to `keep_10_day`.
- **CSV Parsing**: Inputs may be tab or comma separated. The bundled script uses `csv.Sniffer` to handle both automatically.
