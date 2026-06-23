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
- **Do not parse PDFs as raw text when they contain structured tables**. Extract the table data properly.
- **Type mismatch between PDF and Excel**: PDF extraction returns all cell values as strings (e.g., `'123'`, `'4.56'`), while Excel preserves native numeric types (e.g., `123`, `4.56`). Always normalize types before comparison to avoid false positives.
- **Do not trust PDF-extracted IDs without validation**: PDF table extraction can capture header rows as data, introducing invalid IDs (e.g., literal "ID" string). Always filter IDs against the expected pattern.

## Workflow

1. **Identify Primary Key**: Determine the unique identifier field (e.g., `ID`) that exists in both datasets.

2. **Extract Source Data (Baseline/Archive)**
   - **PDF with tables**: Use `pdfplumber` library (see references)
   - **Excel (.xlsx)**: Use `pandas.read_excel()`
   - **CSV**: Use `pandas.read_csv()`

3. **Extract Target Data (Current State)** using the appropriate method above.

4. **Normalize Types for Comparison**: 
   - Convert numeric strings to native int/float (especially critical when comparing PDF to Excel)
   - Strip whitespace from string values
   - Handle null representations consistently (None, NaN, empty string)
   - See references for `normalize_for_comparison()` helper

5. **Execute Comparison**:
   - **Retired**: IDs present in source but missing in target
   - **Added**: IDs present in target but missing in source
   - **Changed**: For IDs present in both, compare field-by-field and record differences where `old_value != new_value`

6. **Prepare for Output**: Convert numpy types (int64, float64) to Python native types (int, float) to ensure JSON serializability. See references for conversion helper.

7. **Output**: Write structured JSON with keys like `retired_ids`, `added_ids`, `changed_fields` (containing id, field, old_value, new_value).

## Quick Start (Automated)

For standard comparisons, use the provided script instead of writing custom extraction code:

```bash
python3 cross-format-data-diff/scripts/cross_format_diff.py \
  /path/to/source.pdf \
  /path/to/target.xlsx \
  --key ID \
  --output diff_report.json
```

The script handles extraction, type normalization, and JSON output automatically.

### Customizing Output Keys

When the task requires domain-specific terminology (e.g., `retired_schools` instead of `retired_ids`), use the key customization options:

```bash
python3 cross-format-data-diff/scripts/cross_format_diff.py \
  archive.pdf \
  current.xlsx \
  --key ID \
  --retired-key retired_schools \
  --changed-key revised_schools \
  --added-key new_schools \
  --omit-empty \
  --output report.json
```

This eliminates the need for manual post-processing of the JSON structure.

## Validation Steps

- Print column names immediately after extraction to verify field alignment
- Check record counts match expectations before comparison
- **Type check**: Compare a sample record from both sources to ensure numeric fields have consistent types (not string vs number)
- **Verify JSON serializability**: Before writing output, ensure all values are Python native types, not numpy scalars
- **Verify output schema**: If the task requires specific JSON keys (e.g., `revised_records` vs `changed_fields`), use the `--*-key` arguments or transform the output accordingly

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: Write raw float values directly into output
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### cross-format-tabular-diff
- **Output JSON keys vary by task domain**: `retired_ids`/`retired_service_ids`/`retired_schools`, `added_ids`/`added_service_ids`, `changed_records`/`changed_services`/`revised_schools` — always check the task's expected key names. Use `--*-key` CLI args to match.
- **Archive→current comparisons often omit "added" keys**: When comparing an archived baseline against a current snapshot, records typically only retire or revise — not add. The task may not expect an `added_*` key.
- PDF table extraction must use `pdfplumber` — do not use Read tool on PDFs containing tables.
- Always strip whitespace from ID columns and normalize headers before comparison.
- **Validate extracted IDs**: Filter against expected pattern (e.g., `r'SVR\d{4}$'`) to exclude header row artifacts.

## Troubleshooting

- **PEP 668 "externally-managed-environment" error**: Modern Debian/Ubuntu systems block system-wide pip installs. Use `--break-system-packages` flag:
  ```bash
  pip install pandas openpyxl pdfplumber --break-system-packages
  ```
  Or create a virtual environment: `python3 -m venv venv && source venv/bin/activate`
- If `pdfplumber` fails to detect tables, try `extract_text()` and parse manually, or check if the PDF is scanned/image-based (requires OCR).
- If Excel has multiple sheets, explicitly specify `sheet_name` parameter in `read_excel()`.
- **IDs don't match**: Check for leading/trailing spaces, type mismatches (string vs int), or hidden characters. Cast IDs to strings and strip whitespace.
- **False positives in numeric fields**: If diff shows every number as changed, check that PDF-extracted strings were converted to numbers before comparison.
- **Wrong output key names**: Use `--retired-key`, `--added-key`, `--changed-key` arguments to match domain terminology instead of manually editing the JSON afterwards.
- **Invalid IDs in output (e.g., "ID" literal string)**: PDF extraction captured the header row as data. Add regex validation to filter IDs against the expected pattern before processing.

## Fallback Strategies

- If `pdfplumber` fails to detect tables, try `extract_text()` and parse manually, or check if the PDF is scanned/image-based (requires OCR).
- If Excel has multiple sheets, explicitly specify `sheet_name` parameter in `read_excel()`.

## References

- [Extraction Patterns by Format](references/extraction_patterns.md) - Copy-paste Python snippets for PDF, Excel, and CSV extraction, including type normalization and JSON serialization helpers
- [`scripts/cross_format_diff.py`](scripts/cross_format_diff.py) - Full automation script for standard diff workflows with customizable output keys
