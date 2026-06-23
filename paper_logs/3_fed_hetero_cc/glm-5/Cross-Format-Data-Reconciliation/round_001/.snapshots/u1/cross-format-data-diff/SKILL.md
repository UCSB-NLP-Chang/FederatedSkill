---
name: cross-format-data-diff
description: Compare tabular datasets across different file formats (Excel, PDF, CSV, JSON) and generate a structured JSON diff of retired, added, and changed records. Use when tasked with comparing snapshots of data in binary or mixed formats, or when plain text reading fails on structured files.
---

# Cross-Format Tabular Data Diff

## When to Use
- Compare two versions of a dataset provided in different formats (e.g., `.xlsx` vs `.pdf`, `.csv` vs `.xlsx`).
- Generate a structured JSON report of added, removed, and modified records.
- The `Read` tool fails on binary files (`.xlsx`, `.pdf`).

## Workflow
1. **Identify formats**: Check file extensions. Do not use `Read` on `.xlsx` or `.pdf`.
2. **Install dependencies** (if missing): `pip install pandas openpyxl pdfplumber`
3. **Extract & Compare**: Run the helper script to automate loading, normalization, and diffing.
4. **Validate**: Verify the output JSON matches the expected schema and spot-check a few changed records.

## Execution
Run the helper script to automate extraction and comparison:
```bash
python3 scripts/diff_datasets.py <old_file> <new_file> --id-col <ID_COLUMN> --output diff.json
```

## Anti-Patterns
- **Do not use `Read` on binary files**: It will fail. Always use Python or CLI tools for `.xlsx`, `.pdf`, `.docx`.
- **Do not assume column names match exactly**: The script normalizes headers (lowercase, strip spaces) automatically.
- **Do not hardcode field names**: The script dynamically detects changed fields across all columns.
- **Do not assume pandas dtypes are JSON-compatible**: The script uses a NumpyEncoder to handle numpy types.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: write raw numeric values from pandas/Python directly into output
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### cross-format-tabular-diff
- Output JSON keys typically follow pattern: `retired_ids`/`retired_service_ids`, `added_ids`/`added_service_ids`, `changed_records`/`changed_services` — check the task's expected key names.
- PDF table extraction must use `pdfplumber` — do not use Read tool on PDFs containing tables.
- Always strip whitespace from ID columns and normalize headers before comparison.

## Troubleshooting
- **PDF extraction fails**: Ensure `pdfplumber` is installed. If the PDF contains scanned images, use OCR (`pytesseract`) or manual extraction.
- **IDs don't match**: Check for leading/trailing spaces, type mismatches (string vs int), or hidden characters. The script casts IDs to strings and strips whitespace.
- **Missing dependencies**: Run `pip install pandas openpyxl pdfplumber` before executing the script.
- **JSON TypeError on numpy types**: The script uses NumpyEncoder; if writing your own code, always handle numpy types explicitly.

## References
- [Extraction Patterns by Format](references/extraction_patterns.md) — Copy-paste Python snippets for PDF, Excel, CSV extraction
