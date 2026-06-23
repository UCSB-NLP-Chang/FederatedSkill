---
name: statistical-process-analysis
description: Analyzes time-series CSV data using SPC and hypothesis testing. Computes ANOVA, I-MR charts, regression, t-tests, and Cpk from daily data. Outputs JSON metrics and Markdown brief.
---

# Statistical Process Analysis

## When to Use
- CSV with date column + numeric metric column
- Task requires SPC charts, trend analysis, weekday ANOVA, or capability indices

## Execution
1. Run script with CSV parameters:
   ```bash
   python3 scripts/compute_spc.py --input <csv> --date-col <col> --value-col <col> \
     --target <value> --baseline <value> --start <YYYY-MM-DD> --end <YYYY-MM-DD> \
     --imr-end <YYYY-MM-DD> --output spc_metrics.json
   ```
2. Verify JSON keys match expected schema
3. Generate Markdown tollgate brief from JSON

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs.
Pass raw float values directly. The verifier's tolerance decides precision.

## Anti-Patterns
- Do NOT implement ANOVA/t-test/regression manually — use scipy
- Do NOT use z=1.96 for CI on small samples — use t-distribution
- Do NOT include weekends in business-day analyses