---
name: order-data-extraction
description: Extract order details (ID, date, total) from batches of order/invoice images, validate against a known reference list, handle duplicates, and export to Excel. Use when tasked with compiling e-commerce orders or receipts into a structured spreadsheet, especially when a reference CSV is provided or duplicate orders appear across files.
---

# Order Data Extraction & Validation

## Workflow
1. **Inventory & Sort**: List all target images. Sort filenames explicitly (`sorted(glob(...))`) to guarantee row alignment. Count total images.
2. **OCR Extraction**: Run OCR on *every* image. Do not skip or assume duplicates without reading. (Leverage `ocr-structured-data` for raw text extraction if needed.)
3. **Field Parsing**: Extract `order_id`, `date`, `total_amount` using regex. Normalize dates to `YYYY-MM-DD` and totals to exactly 2 decimal places.
4. **Validation & Deduplication**:
   - If a reference file (e.g., `known_orders.csv`) exists, load it. Cross-check extracted IDs.
   - If an ID matches a known order, populate fields. If multiple images share an ID, retain extracted data for all rows or follow explicit task instructions. **Never leave duplicate rows blank** unless explicitly instructed.
   - Flag any extracted IDs not in the reference list for review.
5. **Export**: Write to Excel/CSV with exact required schema (e.g., `filename`, `order_id`, `date`, `total_amount`). Ensure row count matches image count.
6. **Verification**: Run `scripts/verify_output.py` to confirm row counts, null values, and reference list alignment before finalizing.

## Critical Anti-Patterns
- **Do not skip images.** Process every file in the dataset. Assuming duplicates without OCR confirmation causes missing data and test failures.
- **Do not leave duplicate rows blank.** Unless explicitly told to nullify duplicates, fill them with the extracted data or a clear marker. Blank rows fail schema validation.
- **Do not hardcode extraction results.** Always use a loop over sorted files to prevent index misalignment.
- **Do not ignore reference lists.** If provided, they are the ground truth for validation. Use them to catch OCR errors or flag unknowns.

## Troubleshooting
- **Missing data in output**: Verify OCR actually ran on all files. Print raw OCR text for failing images to adjust regex.
- **Row misalignment**: Ensure `sorted()` is applied directly to the file list before processing.
- **Validation failures**: If IDs don't match the reference list, check for OCR misreads (e.g., `O` vs `0`, `I` vs `1`). Apply fuzzy matching or manual correction if allowed.