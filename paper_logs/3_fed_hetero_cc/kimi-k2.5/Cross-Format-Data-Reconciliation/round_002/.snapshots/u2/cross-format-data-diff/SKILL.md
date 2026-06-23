---
name: cross-format-data-diff
description: Compare structured tabular data between different file formats (PDF, Excel, CSV) to identify retired records, new records, and field-level changes. Use when asked to diff, compare, reconcile, or find changes between two data snapshots, especially when sources are in different formats (e.g., archived PDF vs current Excel).
---

# Cross-Format Tabular Data Diff

Compare two versions of structured data stored in different file formats to produce a structured change report.

## Critical Anti-Patterns

- **Never use the `Read` tool on binary files** (e.g., `.xlsx` Excel files). The tool will fail with "cannot read binary files". Always use Python with appropriate libraries instead.
- **Read tool on PDF returns raw base64/metadata, not parsed tables**. Always use Python (`pdfplumber`) for table extraction from PDFs.
- **Pandas/numpy scalar types are not JSON serializable**: DataFrame columns containing `int64`, `float64`, or other numpy types will raise `TypeError: Object of type int64 is not JSON serializable`. Convert to Python native types before `json.dump()`.
- Do not parse PDFs as raw text when they contain structured tables. Extract the table data properly.

## Workflow

1. **Identify Primary Key**: Determine the unique identifier field (e.g., `ID`) that exists in both datasets.

2. **Extract Source Data (Baseline/Archive)**
   - **PDF with tables**: Use `pdfplumber` library (see references)
   - **Excel (.xlsx)**: Use `pandas.read_excel()`
   - **CSV**: Use `pandas.read_csv()`

3. **Extract Target Data (Current State)** using the appropriate method above.

4. **Normalize**: Convert both datasets to lists of dictionaries with matching keys.

5. **Execute Comparison**:
   - **Retired**: IDs present in source but missing in target
   - **Added**: IDs present in target but missing in source
   - **Changed**: For IDs present in both, compare field-by-field and record differences where `old_value != new_value`

6. **Prepare for Output**: Convert numpy types (int64, float64) to Python native types (int, float) to ensure JSON serializability. See references for conversion helper.

7. **Output**: Write structured JSON with keys like `retired_service_ids`, `changed_services` (containing id, field, old_value, new_value).

## Validation Steps

- Print column names immediately after extraction to verify field alignment
- Check record counts match expectations before comparison
- Spot-check a few records to ensure data types are consistent (especially numbers vs strings)
- **Verify JSON serializability**: Before writing output, ensure all values are Python native types, not numpy scalars

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: Write raw float values directly into output
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Troubleshooting

- **PEP 668 "externally-managed-environment" error**: Modern Debian/Ubuntu systems block system-wide pip installs. Use `--break-system-packages` flag:
  ```bash
  pip install pandas openpyxl pdfplumber --break-system-packages
  ```
  Or create a virtual environment: `python3 -m venv venv && source venv/bin/activate`
- If `pdfplumber` fails to detect tables, try `extract_text()` and parse manually, or check if the PDF is scanned/image-based (requires OCR).
- If Excel has multiple sheets, explicitly specify `sheet_name` parameter in `read_excel()`.
- **IDs don't match**: Check for leading/trailing spaces, type mismatches (string vs int), or hidden characters. Cast IDs to strings and strip whitespace.

## Fallback Strategies

- If `pdfplumber` fails to detect tables, try `extract_text()` and parse manually, or check if the PDF is scanned/image-based (requires OCR).
- If Excel has multiple sheets, explicitly specify `sheet_name` parameter in `read_excel()`.

## References

- [Extraction Patterns by Format](references/extraction_patterns.md) - Copy-paste Python snippets for PDF, Excel, and CSV extraction, including JSON serialization helpers