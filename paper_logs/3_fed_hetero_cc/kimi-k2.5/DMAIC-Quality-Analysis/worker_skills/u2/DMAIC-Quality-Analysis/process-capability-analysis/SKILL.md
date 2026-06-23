---
name: process-capability-analysis
description: Calculate Six Sigma process capability indices (Cp, Cpk, Pp, Ppk) from Excel data and classify processes. Use when task requires capability indices, specification limits (USL/LSL), or Cpk classification.
---

# Process Capability Analysis

## Workflow (execute in order)

1. **Run analysis**: `python3 scripts/calculate_capability.py <excel_path>`
2. **Copy output**: Save JSON output to required file - DO NOT rename keys
3. **Generate brief**: Create Markdown with Summary, Capability Assessment table, Risk Ranking, Monitoring Plan
4. **Validate**: Ensure JSON has all keys in `references/report_schema.md`

## STOP: Before writing any Python code

**The library has scripts. Run them. Do NOT write custom analysis code.**

## Output precision

Never round, truncate, or fixed-format numeric values.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: Pass raw float values directly

## Capability classification (use script output)

| Cpk Range | Classification |
|-----------|----------------|
| Cpk ≥ 1.33 | Capable |
| 1.0 ≤ Cpk < 1.33 | Marginal |
| Cpk < 1.0 | Not Capable |

## Anti-patterns

- **DO NOT write custom Python** - use `scripts/calculate_capability.py`
- **DO NOT try `pip install scipy`** - environment is externally-managed
- **DO NOT use pipeline-performance-analysis** for Cpk requirements
- **DO NOT pool rates then calculate std** - use per-point proportions

## Scripts

- `scripts/calculate_capability.py` — Computes Cp/Cpk, Pp/Ppk, CV, Wilson CI

## References

- `references/report_schema.md` — Required JSON keys
