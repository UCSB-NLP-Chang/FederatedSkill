---
name: excel-report-aggregation
description: Generate multi-sheet Excel reports from extracted document data, separating line-item details from aggregated summaries. Use when tasked with creating a "details" sheet (one row per line item per document) and a "summary" sheet (grouped totals, earliest/latest dates, counts) from batches of forms, invoices, or measurement records.
---

# Excel Report Generation & Aggregation

## Workflow
1. **Extract Programmatically**: Use OCR or vision models to extract data from **every** input file. **Never hardcode values** or assume uniformity across documents.
2. **Structure Data**: Parse each document into a structured record containing a unique identifier (e.g., filename, project code) and a list of line items.
3. **Build Details Sheet**:
   - Flatten all line items into a single list.
   - Columns typically include: `filename`, `group_key` (e.g., project_code), `item_description`, `quantity`, `unit_price`.
   - Sort rows by `filename` (or document order), then by item sequence.
4. **Build Summary Sheet**:
   - Group records by `group_key`.
   - Aggregate metrics: `total_amount` (sum of line item totals or form totals), `date` (earliest or latest measurement date), `item_count`.
   - Sort rows by `group_key` ascending.
   - Columns typically include: `group_key`, `date`, `total_amount`.
5. **Export**: Use `openpyxl` to create a new workbook. Add sheets in the required order. Write headers exactly as specified. Save to the target path.
6. **Verify**: Run `scripts/verify_multi_sheet.py` to validate schema, row counts, and aggregation consistency.

## Critical Anti-Patterns
- **NEVER hardcode extracted values.** Always loop over all input files. Partial sampling leads to missing data and verifier failures.
- **Do not confuse details vs summary.** Details = 1 row per line item. Summary = 1 row per group/project.
- **Do not skip aggregation logic.** If the prompt says "each project should appear only once", you must group and sum/aggregate, not just list forms.
- **Do not assume uniform line items.** Some forms may have 2 items, others 5. Handle variable lengths gracefully.
- **Do not drop or overwrite sheets.** Create a fresh workbook or carefully manage sheet names.

## Troubleshooting
- **Aggregation mismatch**: Verify that totals are summed correctly across all forms for a group. Check date logic (earliest vs latest).
- **Row count mismatch**: `details_rows` should equal `sum(len(items) for doc in docs)`. `summary_rows` should equal `len(unique_groups)`.
- **Schema mismatch**: Check exact column names and order against task requirements. Use the verification script.
- **Missing data**: If OCR misses fields, print raw output for failing images and adjust regex/parsing before re-running.

## Verification
Run `scripts/verify_multi_sheet.py <output.xlsx> <details_col1,col2,...> <summary_col1,col2,...> [img_dir]` to automatically validate sheet structure, row counts, and aggregation consistency.