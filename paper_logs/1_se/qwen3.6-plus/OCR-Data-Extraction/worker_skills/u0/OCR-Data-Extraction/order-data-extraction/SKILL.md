---
name: order-data-extraction
description: Extract structured fields (IDs, dates, amounts) from batches of document images, merge with a reference/roster CSV, handle missing matches, and export to Excel. Use for invoices, receipts, travel claims, or any form-based extraction requiring cross-referencing with a known list.
---

# Order & Claim Data Extraction

## Workflow
1. **Inventory & Sort**: `sorted(glob(...))` all target images. Process in a single loop to guarantee row alignment.
2. **OCR Extraction**: Run Tesseract/OCR on every image. Do not skip or assume duplicates.
3. **Field Parsing**:
   - Extract target fields using regex.
   - **Multi-line values**: If a keyword (e.g., `AMOUNT CLAIMED`) appears without a value on the same line, check the immediately following line for the numeric value.
   - Normalize dates to `YYYY-MM-DD` (prefer `DD/MM` when ambiguous). Format amounts to exactly 2 decimal places.
4. **Reference/Roster Merge**:
   - Load reference CSV (e.g., `roster.csv`, `known_orders.csv`). Map primary key (e.g., `claim_code`, `order_id`) to supplementary fields.
   - For each extracted record, lookup the key. If found, populate supplementary fields. If not found, leave them empty (`None`/blank). **Do not halt or flag as error unless explicitly required.**
5. **Export**: Write to Excel with exact required schema and column order. Ensure row count matches image count.
6. **Verification**: Run `scripts/verify_output.py <output.xlsx> <img_dir> [ref_csv] [col1,col2,...]` after export to validate schema, row counts, and empty-cell handling.

## Critical Anti-Patterns
- **Do not skip images.** Process every file.
- **Do not assume single-line values.** Document layouts often split labels and values across lines. Always check `line[i+1]` if a keyword line lacks a value.
- **Do not hardcode extraction results.** Use loops over sorted files.
- **Do not treat missing roster matches as failures.** Unless instructed otherwise, leave supplementary fields blank for unmatched records.

## Troubleshooting
- **Missing data**: Print raw OCR for failing images. Adjust regex to handle multi-line splits or OCR artifacts.
- **Row misalignment**: Ensure `sorted()` is applied directly to the file list before processing.
- **Validation failures**: Check for OCR misreads (`O` vs `0`). Apply fuzzy matching if allowed.
