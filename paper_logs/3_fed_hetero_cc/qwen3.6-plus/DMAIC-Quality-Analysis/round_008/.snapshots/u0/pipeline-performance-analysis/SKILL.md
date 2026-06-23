---
name: pipeline-performance-analysis
description: Analyze multi-sheet Excel CI/CD pipeline data (build duration, bug rates, deployment failures) to compute statistical summaries and generate structured JSON/Markdown reports. Use when task involves DevOps pipeline performance reporting or Excel data analysis with statistical validation.
---

# Pipeline Performance Analysis

## Workflow (follow exactly)

1. **Load Excel**: Run `python3 scripts/pipeline_stats.py <excel_path>` to load all sheets and compute statistics.
2. **Check output**: The script prints JSON to stdout. Verify all keys are present.
3. **Map to schema**: Copy values from script output to the required JSON structure. Use `references/report_schema.md` for exact key names.
4. **Generate Markdown**: Create sections: Summary of Findings (table), Most Significant Risks, Prioritized Corrective Actions (5 items), Improvement Plan (5 subsections + 30/60/90-day milestones).
5. **Validate**: Run `python3 scripts/validate_output.py <json_file>` before submission.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: write raw float values from script output
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give full precision.

## Known invariants (by sub-task)

### pipeline-performance-analysis
- Use pooled bug rate: `total_bugs / total_lines`, NOT mean of daily rates
- Wilson CI uses pure numpy (no scipy dependency)
- Stability threshold: `|t_stat| < 2.0` → Stable
- CV ranking must be descending (highest variability first)
- All JSON keys must match schema exactly - DO NOT RENAME

## Anti-patterns

- **DO NOT write custom computation code** - use the provided scripts
- **DO NOT assume scipy is available** - scripts use pure numpy
- **DO NOT call `.date` on string columns** - check dtype first, parse if needed
- **DO NOT use mean of bug rates** - use pooled rate (total_bugs/total_lines)

## References

- `references/report_schema.md`: Exact JSON structure and required keys
- `scripts/pipeline_stats.py`: Statistical analysis (invoke with python3)
- `scripts/wilson_ci.py`: Wilson CI helper (imported by pipeline_stats.py)
- `scripts/validate_output.py`: JSON schema validator
