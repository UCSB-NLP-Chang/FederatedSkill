---
name: cross-format-data-diff
description: Compare tabular datasets across different file formats (Excel, PDF, CSV, JSON) and generate a structured JSON diff of retired, added, and changed records. Use when tasked with comparing snapshots of data in binary or mixed formats, or when plain text reading fails on structured files.
---

# Cross-Format Tabular Data Diff

## When to Use
- Compare two versions of a dataset provided in different formats (e.g., `.xlsx` vs `.pdf`, `.csv` vs `.xlsx`).
- Generate a structured JSON report of added, removed, and modified records.
- The `Read` tool fails on binary files or returns raw base64/metadata instead of structured tables.

## Tool Selection Rules
- **`.xlsx`, `.xls`, `.docx`, `.bin`**: Do NOT use `Read`. It will fail. Use Python (`pandas`, `openpyxl`) or `scripts/diff_datasets.py`.
- **`.pdf`**: `Read` may succeed but returns raw base64/metadata, not parsed tables. Always use Python (`pdfplumber`) or the helper script for table extraction.
- **`.csv`**: `Read` works, but Python/pandas is faster for comparison.

## Workflow
1. **Identify formats**: Check file extensions. Skip `Read` for binary/mixed formats.
2. **Install dependencies** (if missing): `pip install pandas openpyxl pdfplumber --break-system-packages`
3. **Extract & Compare**: Run the helper script to automate loading, normalization, and diffing.
   ```bash
   python3 scripts/diff_datasets.py <old_file> <new_file> --id-col <ID_COLUMN> --output diff.json
   ```
4. **Validate**: Verify the output JSON matches the expected schema and spot-check a few changed records.

### When to Write Custom Code Instead
Use inline Python instead of the helper script when:
- **Output keys must match specific names** (e.g., `closed_departments` vs `retired_ids`). The helper uses generic keys.
- **Column names must be preserved exactly**. The helper normalizes to lowercase.
- **Custom comparison logic is needed** (e.g., ignoring certain fields, tolerance-based numeric comparison).

In these cases, copy the extraction patterns from `references/extraction_patterns.md` and write a tailored comparison.

## Anti-Patterns
- **Do not use `Read` on binary files**: It will fail or return unusable base64. Always use Python or CLI tools.
- **Do not assume column names match exactly**: The script normalizes headers (lowercase, strip spaces) automatically.
- **Do not hardcode field names**: The script dynamically detects changed fields across all columns.
- **Do not round or truncate numbers**: Pass raw float values. The verifier decides tolerance.
- **Do not assume pandas dtypes are JSON-compatible**: Numpy types (int64, float64) need conversion. Use the NumpyEncoder or `convert_for_json()` helper.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs (JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: Write raw float values — the script's NumpyEncoder preserves native types
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### cross-format-tabular-diff
- Output JSON keys typically follow pattern: `retired_ids`/`retired_service_ids`, `added_ids`/`added_service_ids`, `changed_records`/`changed_services` — check the task's expected key names.
- PDF table extraction must use `pdfplumber` — do not use Read tool on PDFs containing tables.
- Always strip whitespace from ID columns and normalize headers before comparison.

## Troubleshooting
- **PEP 668 "externally-managed-environment" error**: Modern Debian/Ubuntu systems block system-wide pip installs. Use `--break-system-packages` flag:
  ```bash
  pip install pandas openpyxl pdfplumber --break-system-packages
  ```
  Or create a virtual environment: `python3 -m venv venv && source venv/bin/activate`
- **PDF extraction fails**: Ensure `pdfplumber` is installed. If the PDF contains scanned images, use OCR (`pytesseract`) or manual extraction.
- **IDs don't match**: Check for leading/trailing spaces, type mismatches (string vs int), or hidden characters. The script casts IDs to strings and strips whitespace.
- **Missing dependencies**: Run `pip install pandas openpyxl pdfplumber --break-system-packages` before executing the script.
- **JSON TypeError on numpy types**: Use `NumpyEncoder` or `convert_for_json()` from references.

## References
- [Extraction Patterns by Format](references/extraction_patterns.md) — Copy-paste Python snippets for PDF, Excel, CSV extraction, including JSON serialization helpers
