---
name: logistics-reliability-analysis
description: Analyze multi-sheet Excel logistics/operational data (delivery times, damage rates, error rates) to compute statistical summaries, Wilson CIs, and generate structured JSON/Markdown reports. Use when task involves supply chain reliability reporting, Excel data analysis with statistical validation, or operational performance benchmarking.
---

# Logistics Reliability Analysis

## Workflow (follow exactly)

1. **Load Excel**: Run `python3 scripts/analyze_logistics.py <excel_path>` to load all sheets and compute statistics.
2. **Check output**: The script prints JSON to stdout. Verify all keys match `references/report_schema.md`.
3. **Map to schema**: Copy values from script output to the required JSON structure. Do not rename keys.
4. **Generate Markdown**: Create sections: Summary of Findings, Most Significant Risks, Prioritized Corrective Actions, Variance Diagnostic, Action Plan (with 30/60/90-day milestones and 7-item checklist).
5. **Validate**: Run `python3 scripts/validate_logistics.py <json_file>` before submission.

## Output precision

Never round, truncate, or fixed-format numeric values. Pass raw float values directly.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: write raw float values from script output
- The verifier's tolerance decides acceptable precision.

## Column mapping & invariants

- **Delivery Times**: Single numeric column → compute mean, std, cv, slope, t_stat, stability.
- **Damage Rates**: Two columns (`Shipments`, `Damaged`) → compute pooled rate (`total_damaged / total_shipments`), Wilson CI, capability vs target (default 1.5%).
- **Order Accuracy**: Single numeric column (`Error Rate`) → compute mean, std, cv, slope, t_stat, stability.
- **Stability threshold**: `|t_stat| < 2.0` → Stable, else Unstable/Trending.
- **CV ranking**: Sort descending (highest variability first).
- **All JSON keys must match schema exactly** - DO NOT RENAME.

## Anti-patterns

- **DO NOT write custom computation code** - use the provided scripts.
- **DO NOT assume scipy is available** - scripts use pure numpy.
- **DO NOT use mean of daily rates** - use pooled rate for damage/error rates.
- **DO NOT rely on self-validation alone** - always run the provided validator script. Verifier failures often stem from exact key mismatches or missing nested fields.

## References

- `references/report_schema.md`: Exact JSON structure and required keys
- `scripts/analyze_logistics.py`: Statistical analysis (invoke with python3)
- `scripts/validate_logistics.py`: JSON schema validator