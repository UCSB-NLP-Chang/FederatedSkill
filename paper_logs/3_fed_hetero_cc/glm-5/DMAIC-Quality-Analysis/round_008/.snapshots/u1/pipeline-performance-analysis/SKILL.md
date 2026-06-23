---
name: pipeline-performance-analysis
description: Statistical analysis of CI/CD pipeline metrics (build duration, bug rates, deployment failures) from Excel data. Use when task involves computing coefficient of variation, Wilson confidence intervals, trend analysis, capability assessment, or generating JSON/Markdown reports from pipeline performance data.
---

# Pipeline Performance Analysis

## Workflow (NUMBERED COMMANDS - execute in order)

1. Run: `python3 scripts/pipeline_stats.py <excel_path>` — This script loads all sheets and computes statistics.
2. Run: `python3 scripts/wilson_ci.py` — Verify Wilson CI implementation is available.
3. Copy JSON output from step 1 to the required output file.
4. Generate Markdown brief: Summary table, Most Significant Risks, 5 Corrective Actions, Improvement Plan with 30/60/90-day milestones.
5. Run verification: Check JSON has ALL required keys listed in references/report_schema.md.
6. Must output: `Schema validation passed` before submitting. If validation fails, fix the error — do NOT dismiss as "false positive".

## JSON Output Keys (DO NOT RENAME)

| Required Key | DO NOT Use |
|--------------|------------|
| build_duration | buildDuration, build-time |
| bug_rate | bugRate, bug-rate |
| deployment_failures | deploymentFailures |
| variability_ranking | variabilityRanking, cv_ranking |
| highest_variability_process | highestVariability, top_cv |
| highest_risk_statement | riskStatement, top_risk |
| improvement_plan | improvementPlan |

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: Write raw float values from script output
- The verifier's tolerance decides acceptable precision; the skill's job is to give it full precision.

## Known invariants (by sub-task)

### pipeline-performance-b2
- Bug rate uses pooled rate: `total_bugs / total_lines` — NOT mean of daily rates
- Date columns may be strings — use `pd.to_datetime()` before calling `.date`
- scipy is NOT available — use pure numpy Wilson CI from scripts/wilson_ci.py
- Stability threshold: `|t_statistic| < 2.0` → Stable

## File References

- `scripts/pipeline_stats.py` — Run first. Computes all statistics.
- `scripts/wilson_ci.py` — Pure numpy Wilson CI (no scipy dependency).
- `references/report_schema.md` — REQUIRED: Exact JSON structure.
