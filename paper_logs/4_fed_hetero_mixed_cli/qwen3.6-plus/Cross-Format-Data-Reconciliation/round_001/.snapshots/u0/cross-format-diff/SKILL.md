---
name: cross-format-diff
description: Compare tabular datasets across different file formats (PDF, Excel, CSV) to identify added, retired, and modified records. Use when tasked with finding differences between two versions of a dataset, especially when sources use different formats or require extraction.
---

# Cross-Format Diff

## Workflow
1. **Extract Data**: Read both source files into structured lists of dictionaries. Use parallel subagents for PDF/Excel extraction if needed. Ensure column names are normalized (strip whitespace, standardize casing).
2. **Identify Primary Key**: Determine the unique identifier column (e.g., `ID`, `Name`, `SKU`). If not explicit, infer from data patterns.
3. **Compute Diff**: Save extracted data as `old.json` and `new.json`. Run `scripts/compute_diff.py old.json new.json --key <PRIMARY_KEY>` to generate a structured diff.
4. **Validate**: Spot-check a few changed records against raw data to ensure extraction accuracy. Verify numeric vs string type consistency before diffing.
5. **Output**: Write the resulting JSON to the requested path.

## Anti-Patterns
- Do not manually compare large tables row-by-row; use the provided script.
- Do not assume identical column names across files; map them explicitly before diffing.
- Avoid string-vs-number mismatches during comparison (e.g., `"10128"` vs `10128`). The script normalizes types automatically, but verify extraction consistency.

## Troubleshooting
- **Missing rows after extraction**: PDFs often split tables across pages or use merged cells. Request explicit row-by-row extraction from the subagent.
- **False positives in diff**: Check for trailing whitespace or formatting differences in text fields. Strip and lowercase text fields before comparison if appropriate.
- **Script fails on JSON input**: Ensure both inputs are valid JSON arrays of objects with consistent keys.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### portfolio-comparison
- Output arrays must be sorted by ID for deterministic output.
- Numeric fields must be JSON numbers, not quoted strings.

## Scripts
- `scripts/compute_diff.py` — Reusable Python script for JSON-based diff computation

## References
- `references/pdf-extraction.md` — PDF extraction patterns and anti-patterns
- `references/diff-schema.md` — Output JSON schema documentation