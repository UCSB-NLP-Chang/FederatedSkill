---
name: dataset-diff
description: Compare two versions of a structured dataset across formats (PDF, Excel, CSV, JSON) to detect added, removed, and modified records. Use when comparing archived vs current data, reconciling cross-format datasets, or generating change reports.
---

# Dataset Diff

## Workflow
1. **Extract Data**: Read both source files into structured lists of dictionaries. Use parallel subagents for PDF/Excel extraction if needed. Ensure column names are normalized (strip whitespace, standardize casing).
2. **Identify Primary Key**: Determine the unique identifier column (e.g., `ID`, `Name`, `SKU`). If not explicit, infer from data patterns.
3. **Compute Diff**: Save extracted data as `old.json` and `new.json`. Run `python3 scripts/compute_diff.py old.json new.json --key <PRIMARY_KEY>` to generate a structured diff. **Always use the provided script**; it handles type normalization automatically.
4. **Transform Output**: The script outputs a standard schema (`removed_ids`, `added_ids`, `changed_records`). If the task requires different field names (e.g., `dropped_categories`, `adjusted_categories`), transform the script's JSON output rather than re-implementing comparison logic.
5. **Validate**: Spot-check a few changed records against raw data to ensure extraction accuracy.
6. **Output**: Write the resulting JSON to the requested path.

## Type Handling

When comparing numeric fields from different sources:
- **Excel/CSV**: Pandas reads as `int64` or `float64`
- **PDF**: Extracts as strings (e.g., `"9284"`)

**Comparison rule**: Normalize to float for accurate comparison (handles `"4.09" == 4.09`).
**Output rule**: Convert float whole numbers back to integers to avoid `9284.0` in JSON output.

```python
def format_output(val):
    """Convert float whole numbers to int for clean JSON output."""
    if isinstance(val, float) and val.is_integer():
        return int(val)
    return val
```

## Environment & Tooling
- Always use `python3` (not `python`) for execution.
- If `pip install` fails with "externally managed", use `pip install --break-system-packages <package>`.
- Prefer `pdfplumber` for PDF extraction. Avoid `tabula-py` (requires Java) or `csvkit in2csv` (often fails on PDFs).

## Column Name Cleanup

Excel files often contain hidden whitespace or newlines in column headers (e.g., `'Planner\n'`). Always strip column names after reading:

```python
df.columns = [c.strip() for c in df.columns]
```

## Anti-Patterns
- Do not manually compare large tables row-by-row; use `scripts/compute_diff.py`.
- Do not assume identical column names across files; map them explicitly before diffing.
- Avoid writing custom type-conversion logic for diffing; the script's `normalize()` and `format_output()` functions safely handle string-vs-number mismatches.
- **Do not re-implement comparison logic** when transforming output formats. Run `compute_diff.py` first, then rename/reshape its JSON output to match task requirements.
- Do not manually normalize types before saving JSON; save raw extracted data and let the script's `normalize()` handle it.

## Troubleshooting
- **`python: command not found`**: Use `python3` instead.
- **Missing rows after extraction**: PDFs often split tables across pages or use merged cells. Request explicit row-by-row extraction from the subagent.
- **False positives in diff**: Check for trailing whitespace or formatting differences in text fields. Strip and lowercase text fields before comparison if appropriate.
- **`9284.0` instead of `9284` in output**: Ensure the script's `format_output()` is applied before JSON serialization.
- **Column mismatch after extraction**: Hidden whitespace or newlines in Excel headers. Strip all column names: `df.columns = [c.strip() for c in df.columns]`.

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
- Integer values should not have `.0` suffix in output.

## Scripts
- `scripts/compute_diff.py` — Reusable Python script for JSON-based diff computation. Run with `python3`.

## References
- `references/pdf-extraction.md` — PDF extraction patterns and anti-patterns
- `references/diff-schema.md` — Output JSON schema documentation