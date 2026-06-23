---
name: pharmacy-mailer-cycle-analysis
description: Compares 45-day vs 90-day medication refill cycles for pharmacies using mailer costs, base payments, and service fees. Use when given compound cost, mailer cost, base payment, and service fee CSVs to compute annual margins, apply a financial threshold, and output structured JSON/Markdown analysis.
---

# Pharmacy Mailer Refill Cycle Margin Analysis

## When to Use
- Task provides four CSVs: `compound_cost.csv`, `mailer_cost.csv`, `base_payment.csv`, `service_fee.csv`.
- Goal is to compare annual financial margins between 45-day and 90-day refill cycles.
- Output must include per-medication breakdowns, total margins, absolute difference, and a threshold-based decision.

## Workflow
1. **Verify Inputs**: Ensure all four CSVs are present. Check column names match expected schema.
2. **Run Computation**: Execute `scripts/compute_mailer_margin.py` with the input CSV paths.
   ```bash
   python3 scripts/compute_mailer_margin.py --compound compound_cost.csv --mailer mailer_cost.csv --base base_payment.csv --fee service_fee.csv --threshold 8500
   ```
3. **Validate Outputs**: Check that `mailer_policy_analysis.json` and `mailer_policy_summary.md` are generated. Verify JSON structure matches the expected schema in `references/formulas_and_schema.md`.
4. **Review Decision**: The script determines `keep_45_day` or `switch_to_90_day` based on whether the absolute margin difference exceeds the threshold.

## Key Formulas & Assumptions
- **Patients per medication**: 150
- **Fills/year**: 8 (45-day), 4 (90-day)
- **Doses/fill**: Equals cycle days (45 or 90)
- **Annual Drug Cost**: `(price_per_1000 / 1000) * doses_per_fill * fills_per_year * 150` (Identical for both cycles)
- **Annual Mailer Cost**: `mailer_cost * fills_per_year * 150`
- **Annual Payment**: `(base_payment + service_fee) * fills_per_year`
- **Annual Margin**: `Annual Payment - Annual Drug Cost - Annual Mailer Cost`
- See `references/formulas_and_schema.md` for detailed derivations and exact JSON schema.

## Anti-Patterns & Troubleshooting
- **Do not compute manually**: The patient multiplier on mailer costs and payment scaling frequently causes manual arithmetic errors. Always use the bundled script.
- **Mailer cost scaling**: Mailer cost scales with both fill frequency and patient count. Do not forget the `* 150` multiplier.
- **Drug cost invariance**: Total annual drug cost is identical for both cycles (same total doses/year). Only mailer costs and payment revenue change.
- **Threshold logic**: Decision triggers only if `abs(margin_90 - margin_45) > threshold`. If triggered, pick the higher margin cycle. Otherwise, default to `keep_45_day`.
- **CSV Parsing**: Inputs may be tab or comma separated. The bundled script uses `csv.Sniffer` to handle both automatically.
