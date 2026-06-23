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
3. **Extract & Inspect**: Load both files. Print headers and first row to verify structure and dtypes.
4. **Normalize Types Before Comparison**: `pdfplumber` extracts all cells as strings, while `pandas` reads Excel/CSV as native types (int/float). Direct `!=` checks will yield false positives. Always cast both sides to a common type before comparing:
   ```python
   def safe_equal(a, b):
       try:
           return float(a) == float(b)
       except (ValueError, TypeError):
           return str(a).strip() == str(b).strip()
   ```
5. **Compare & Output**: Run the helper script or write inline Python.
   ```bash
   python3 scripts/diff_datasets.py <old_file> <new_file> --id-col <ID_COLUMN> --output diff.json
   ```
6. **Validate**: Verify the output JSON matches the expected schema and spot-check a few changed records.

### In-Memory Single-Script Pattern (Recommended)
Do not write extracted PDF/Excel data to intermediate `.txt` or `.csv` files before comparing. This causes `FileNotFoundError` and state-sync issues. Instead, run one Python script that extracts both, normalizes, compares, and outputs the final JSON in memory. See `references/extraction_patterns.md` for a complete combined template.

### When to Write Custom Code Instead
Use inline Python instead of the helper script when:
- **Output keys must match specific names** (e.g., `closed_departments` vs `retired_ids`). The helper uses generic keys.
- **Column names must be preserved exactly**. The helper normalizes to lowercase.
- **Custom comparison logic is needed** (e.g., ignoring certain fields, tolerance-based numeric comparison).
- **Verifier expects exact keys**: Always extract the exact JSON keys from the task prompt (e.g., `decommissioned_servers`, `updated_records`) and use them in your output dict. The helper script uses generic keys (`retired_ids`, `changed_records`) which will fail strict verifiers.

**Example - Output key mismatch:**
```
Task expects:     {"dropped_categories": [...], "adjusted_categories": [...]}
Helper produces:  {"retired_ids": [...], "changed_records": [...]}
→ Write custom code to match task's expected key names.
```

In these cases, read `references/extraction_patterns.md` for safe comparison logic and write a tailored comparison.

#### Custom Output Schema Template
When the task requires domain-specific keys (e.g., `retired_schools`, `revised_programs`), adapt the diff loop:
```python
retired = sorted(list(old_ids - new_ids))
added = sorted(list(new_ids - old_ids))
revised = []
for idx in sorted(old_ids & new_ids):
    changes = []
    for col in old_df.columns:
        old_val, new_val = old_df.loc[idx, col], new_df.loc[idx, col]
        if not safe_equal(old_val, new_val):
            changes.append({"field": col, "old_value": old_val, "new_value": new_val})
    if changes:
        revised.append({"id": idx, "changes": changes}) # Flatten or restructure as task requires

result = {
    "retired_schools": retired,
    "added_schools": added,
    "revised_schools": revised
}
```

### Change Record Structure Decision Rule
- **Flat format** (default if unspecified): `[{"id": "X", "field": "Y", "old_value": A, "new_value": B}, ...]`
- **Nested format**: `[{"id": "X", "changes": [{"field": "Y", "old_value": A, "new_value": B}]}, ...]`
- Always check the task prompt or verifier schema. If the prompt says "list each field change as a separate object" or shows flat examples, use the flat format. It is easier to validate and commonly expected.

## Anti-Patterns
- **Do not use `Read` on binary files**: It will fail or return unusable base64. Always use Python or CLI tools.
- **Do not compare raw PDF strings against Excel numbers**: `pdfplumber` returns strings. Direct `!=` checks will flag unchanged numeric fields as changed. Always normalize types first.
- **Do not assume column names match exactly**: The script normalizes headers (lowercase, strip spaces) automatically.
- **Do not hardcode field names**: The script dynamically detects changed fields across all columns.
- **Do not round or truncate numbers**: Pass raw float values. The verifier decides tolerance.
- **Do not assume pandas dtypes are JSON-compatible**: Numpy types (int64, float64) need conversion. Use the NumpyEncoder or `convert_for_json()` helper.
- **Do not trust PDF-extracted IDs without validation**: PDF table extraction can capture header rows as data, introducing invalid IDs (e.g., literal "ID" string). Always filter IDs against the expected pattern (see `references/extraction_patterns.md`).
- **Do not rely on intermediate files for extraction**: Writing PDF text to a temp file before parsing causes `FileNotFoundError` and breaks atomicity. Extract and compare in a single in-memory script.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs (JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: Write raw float values — the script's NumpyEncoder preserves native types
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### cross-format-tabular-diff
- Output JSON keys vary by task domain: `retired_ids`/`retired_service_ids`/`retired_schools`/`deleted_medications`/`missing_containers`, `added_ids`/`added_service_ids`/`new_containers`, `changed_records`/`changed_services`/`revised_schools`/`modified_medications`/`changed_containers` — always check the task's expected key names.
- Archive→current comparisons often omit "added" keys (records only retire or revise, not add).
- PDF table extraction must use `pdfplumber` — do not use Read tool on PDFs containing tables.
- Always strip whitespace from ID columns and normalize headers before comparison.
- **Validate extracted IDs**: Filter against expected pattern (e.g., `r'SVR\d{4}$'`, `r'^MED\d{5}$'`, `r'^CNT\d{4}$'`) to exclude header row artifacts.
- **Modified-record schema**: Some tasks expect flat per-field entries (`{"id": ..., "field": ..., "old_value": ..., "new_value": ...}`) rather than nested `{"id": ..., "changes": [...]}`. Match the structure the task specifies.

## Troubleshooting
- **PEP 668 "externally-managed-environment" error**: Modern Debian/Ubuntu systems block system-wide pip installs. Use `--break-system-packages` flag:
  ```bash
  pip install pandas openpyxl pdfplumber --break-system-packages
  ```
  Or create a virtual environment: `python3 -m venv venv && source venv/bin/activate`
- **PDF extraction fails**: Ensure `pdfplumber` is installed. If the PDF contains scanned images, use OCR (`pytesseract`) or manual extraction.
- **PDF table detection returns empty**: If `pdfplumber` doesn't detect grid lines, fall back to `page.extract_text()` and parse with regex or string splitting. This works reliably for simple, text-based PDFs.
- **IDs don't match**: Check for leading/trailing spaces, type mismatches (string vs int), or hidden characters. The script casts IDs to strings and strips whitespace.
- **Invalid IDs in output (e.g., "ID" literal string)**: PDF extraction captured the header row as data. Add regex validation to filter IDs against the expected pattern before processing (see `references/extraction_patterns.md`).
- **Missing dependencies**: Run `pip install pandas openpyxl pdfplumber --break-system-packages` before executing the script.
- **JSON TypeError on numpy types**: Use `NumpyEncoder` from references or the helper script.

## References
- [Extraction Patterns by Format](references/extraction_patterns.md) — Read this before writing custom diff scripts. Contains copy-paste Python snippets for PDF/Excel/CSV/JSON extraction, JSON serialization helpers, multi-page PDF handling, ID validation patterns, and a complete in-memory combined diff template.