---
name: tabular-data-diff
description: Compare structured tabular data between different file formats (PDF, Excel, CSV) to identify retired records, new records, and field-level changes. Use when asked to diff, compare, reconcile, or find changes between two data snapshots, especially when sources are in different formats (e.g., archived PDF vs current Excel).
---

# Tabular Data Diff Across Formats

Compare two versions of structured data stored in different file formats to produce a structured change report.

## Critical Anti-Patterns

- **Never use the `Read` tool on binary files** (e.g., `.xlsx` Excel files). The tool will fail with "cannot read binary files". Always use Python with appropriate libraries instead.
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

6. **Output**: Write structured JSON with keys like `retired_service_ids`, `changed_services` (containing id, field, old_value, new_value).

## Validation Steps

- Print column names immediately after extraction to verify field alignment
- Check record counts match expectations before comparison
- Spot-check a few records to ensure data types are consistent (especially numbers vs strings)

## Fallback Strategies

- If `pdfplumber` fails to detect tables, try `extract_text()` and parse manually, or check if the PDF is scanned/image-based (requires OCR).
- If Excel has multiple sheets, explicitly specify `sheet_name` parameter in `read_excel()`.

## References

- [Extraction Patterns by Format](references/extraction_patterns.md) - Copy-paste Python snippets for PDF, Excel, and CSV extraction