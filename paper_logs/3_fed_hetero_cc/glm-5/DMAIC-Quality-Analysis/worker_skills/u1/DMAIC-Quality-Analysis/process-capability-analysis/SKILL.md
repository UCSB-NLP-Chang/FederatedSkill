---
name: process-capability-analysis
description: Statistical process capability analysis from Excel data computing Six Sigma indices (Cp, Cpk, Pp, Ppk), Wilson confidence intervals, capability classification, and monitoring plans. Use when task involves process capability reports, Cpk calculations, Six Sigma analysis, or assessing whether processes meet specification limits.
---

# Process Capability Analysis

## Workflow (follow exactly)

1. **Run analysis script**: `python3 scripts/calculate_capability.py <excel_path>` — loads all sheets, computes Cp/Cpk/Pp/Ppk indices.
2. **Copy JSON output** to required output file — DO NOT rename keys.
3. **Generate Markdown brief**: Summary of Findings, Most Significant Risks, Prioritized Corrective Actions, Monitoring Plan (with required subsections), 30/60/90-Day Momentum Plan.
4. **Validate JSON**: Ensure all required keys from `references/report_schema.md` are present.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: write raw float values from script output
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision.

## Known invariants (by sub-task)

### process-capability-analysis-b4
- **Cp/Pp formula**: (USL-LSL) / (6σ) — potential capability
- **Cpk/Ppk formula**: min((USL-μ)/3σ, (μ-LSL)/3σ) — actual capability
- **Capability classification**: Cpk ≥ 1.33 → Capable | 1.0 ≤ Cpk < 1.33 → Marginal | Cpk < 1.0 → Not Capable
- **Pooled rate for failure/error rates**: `total_failures / total_units` — NOT mean of daily rates
- **Wilson CI**: Use pure numpy implementation (scipy NOT available)
- **Stability threshold**: `|t_stat| < 2.0` → Stable, else Trending
- **CV ranking**: Sort descending (highest variability first)

## Required JSON keys (DO NOT RENAME)

| Required Key | DO NOT Use |
|--------------|------------|
| capability_indices | capabilityIndices, cp_cpk |
| capability_classification | capabilityClass, status |
| variability_ranking | variabilityRanking, cv_ranking |
| highest_variability_process | highestVariability, top_cv |
| highest_risk_process | riskProcess, top_risk |
| monitoring_plan | monitoringPlan |

## Anti-patterns

- **DO NOT try `pip install scipy`** — environment is externally-managed; use pure numpy scripts
- **DO NOT use mean of rates** — use pooled rate (total failures / total units)
- **DO NOT rename JSON keys** — verifier checks exact key names
- **DO NOT skip validation** — missing keys cause silent failures
- **DO NOT use pipeline-performance-analysis alone** — it lacks Cp/Cpk capability indices
- **DO NOT forget Bessel's correction** — use sample std (ddof=1), not population std
- **DO NOT classify by mean vs target alone** — always consider capability indices

## References

- `references/report_schema.md`: Exact JSON structure and required keys
- `scripts/calculate_capability.py`: Capability analysis with Cp/Cpk/Pp/Ppk (pure numpy)
- `scripts/wilson_ci.py`: Wilson confidence interval implementation
