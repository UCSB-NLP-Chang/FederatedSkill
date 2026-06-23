---
name: pipeline-performance-analysis
description: Analyzes multi-sheet Excel pipeline data (build duration, bug rates, deployment failures) to compute statistical summaries, trend stability, variability rankings, and generates structured JSON/Markdown reports. Use when tasked with DevOps pipeline performance reporting, Excel data analysis, or generating performance briefs with statistical validation.
---

# Pipeline Performance Analysis

## Workflow

1. **Load Excel**: Run `python3 scripts/analyze_pipeline.py <excel_path> --output stats.json`
2. **Read JSON**: Load `stats.json` to get computed metrics (mean, std, CV, trend, stability)
3. **Generate JSON report**: Map stats to required schema keys (see `references/output_schema.md`)
4. **Generate Markdown brief**: Create sections per schema reference
5. **Validate**: Run `python3 scripts/analyze_pipeline.py --validate stats.json`

## Key Rules

- **Bug rate**: Use pooled rate `total_bugs / total_lines`, NOT mean of daily rates
- **Stability threshold**: `|t_stat| < 2.0` → Stable, else Unstable
- **CV ranking**: Sort processes by CV descending (highest = most variable = highest risk)
- **Wilson CI**: For bug rate proportions with varying denominators

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. The verifier's tolerance decides acceptable precision; the skill's job is to give it full precision.

## Anti-Patterns

- **Do NOT assume scipy** — scripts use pure numpy
- **Do NOT mean-of-rates for bug rate** — use pooled (total bugs / total lines)
- **Do NOT call `.date` on string columns** — check dtype first

## Scripts

- `scripts/analyze_pipeline.py` — Main analysis script (CLI)
- `scripts/wilson_ci.py` — Pure numpy Wilson CI implementation
