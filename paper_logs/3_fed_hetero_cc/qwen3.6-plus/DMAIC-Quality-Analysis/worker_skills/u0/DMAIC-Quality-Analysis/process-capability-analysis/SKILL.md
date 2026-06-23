---
name: process-capability-analysis
description: Statistical process capability analysis from Excel data computing CV, Wilson confidence intervals, trend analysis, capability assessment, and monitoring plans. Use when task involves process capability reports, quality benchmarking, or operational metrics with targets and CIs.
---

# Process Capability Analysis

## Workflow (follow exactly)

1. **Run analysis script**: `python3 scripts/process_capability.py <excel_path>` — loads all sheets, computes statistics.
2. **Copy JSON output** to required output file — DO NOT rename keys.
3. **Generate Markdown brief**: Summary of Findings, Most Significant Risks, Prioritized Corrective Actions, Monitoring Plan (with required subsections), 30/60/90-Day Momentum Plan.
4. **Validate JSON**: Run `python3 scripts/validate_capability.py <json_file>` before submission.

## Output precision

Never round, truncate, or fixed-format numeric values. Pass raw float values directly.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: write raw float values from script output

## Key invariants

- **Pooled rate for failure/error rates**: `total_failures / total_units` — NOT mean of daily rates
- **Wilson CI**: Use pure numpy implementation (scipy NOT available)
- **Stability threshold**: `|t_stat| < 2.0` → Stable, else Trending
- **CV ranking**: Sort descending (highest variability first)
- **Capability**: Upper CI ≤ target → Capable, else Not Capable

## Known invariants (by sub-task)

### process-capability-report
- `checklist` must have exactly 7 items — verifier checks count
- `project_codename` must be in format "Project <NAME>"
- `highest_risk_statement` must appear as exact sentence in Markdown brief
- `momentum_plan_30_60_90` must have keys: `30_day`, `60_day`, `90_day`

## Required JSON keys (DO NOT RENAME)

- `task_duration`, `failure_rate`, `system_errors` (or process-specific names)
- `variability_ranking` — list of `{process, coefficient_of_variation}`
- `highest_variability_process` — string
- `highest_risk_statement` — exact sentence
- `monitoring_plan` — with required subsections

## Anti-patterns

- **DO NOT try `pip install scipy`** — environment is externally-managed; use pure numpy
- **DO NOT use mean of rates** — use pooled rate (total failures / total units)
- **DO NOT rename JSON keys** — verifier checks exact key names
- **DO NOT skip validation** — missing keys cause silent failures

## References

- `references/report_schema.md`: Exact JSON structure and required keys
- `scripts/process_capability.py`: Statistical analysis (pure numpy, no scipy)
- `scripts/wilson_ci.py`: Wilson confidence interval implementation
- `scripts/validate_capability.py`: JSON schema validator (run before submission)