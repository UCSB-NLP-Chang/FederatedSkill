---
name: pipeline-performance-analysis
description: Analyzes multi-sheet Excel data with time-series metrics to compute statistical summaries, trend stability, variability rankings, and generates structured JSON/Markdown reports. Use when tasked with performance reporting on any operational processes (logistics, DevOps, manufacturing, etc.), Excel data analysis with multiple metric sheets, or generating statistical briefs with CV ranking and trend analysis.
---

# Multi-Sheet Excel Performance Analysis

## Workflow

1. **Identify metric sheets**: List all sheets in the Excel file; each typically represents one process/metric
2. **Run analysis**: `python3 scripts/analyze_pipeline.py <excel_path> --output stats.json`
3. **Map to required schema**: Rename skill output keys to match task-specific schema requirements (see `references/output_schema.md` for common patterns)
4. **Generate deliverables**: Create JSON report and Markdown brief from the stats
5. **Validate**: Ensure all required keys present; check CV ranking is descending

## Key Statistical Rules

- **Pooled rates for proportions**: Use `total_events / total_opportunities`, NOT mean of daily rates
- **CV ranking**: Sort processes by CV descending (highest = most variable = highest risk)
- **Stability threshold**: `|t_stat| < 2.0` → Stable, else Unstable
- **Wilson CI**: For proportions with varying denominators (see `scripts/wilson_ci.py`)

## Schema Compliance

**CRITICAL**: The skill outputs generic keys (`delivery_times`, `damage_rates`, etc.) based on sheet names. You MUST remap these to task-specific schema keys:

| If task requires | Map from skill output |
|------------------|----------------------|
| `build_duration` | Your sheet name for duration metric |
| `bug_rate` | Your sheet name for defect rate |
| `deployment_failures` | Your sheet name for failure counts |

See `references/output_schema.md` for the canonical schema structure.

## Output Precision

Never round numeric values when writing outputs. Pass raw floats; verifier tolerance decides precision.

## Anti-Patterns

- **Do NOT use sheet names directly as JSON keys** without checking schema requirements
- **Do NOT mean-of-rates** for proportional metrics — always pool
- **Do NOT assume scipy** — scripts use pure numpy
- **Do NOT call `.date` on string columns** — check dtype first

## Scripts

- `scripts/analyze_pipeline.py` — Main analysis (handles any numeric sheet)
- `scripts/wilson_ci.py` — Wilson CI for proportions

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Verifier rejects JSON key | Schema mismatch | Remap skill output keys to required schema |
| CV ranking wrong order | Sorted ascending | Reverse to descending (highest CV first) |
| Missing Wilson CI | Sheet not recognized as rate data | Ensure sheet has two numeric columns (events, opportunities) |
