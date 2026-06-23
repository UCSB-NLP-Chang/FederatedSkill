---
name: ocr-structured-data
description: Extract structured tabular data (dates, prices, IDs) from batches of images using OCR. Use when tasked with converting image labels, receipts, invoices, or forms into Excel/CSV, especially when dates and prices appear in mixed formats or require filling an existing template.
---

# OCR Structured Data Extraction

## Workflow
1. **Inventory & Sort**: List all target images. Sort filenames explicitly *before* processing to guarantee row alignment.
2. **OCR & Preprocessing**: Run OCR (`pytesseract`). **Immediately filter out empty/whitespace-only lines** from the raw output. This prevents blank-line separation failures during keyword matching.
3. **Field Parsing & Normalization**:
   - **Multi-line values**: After filtering blanks, search for keywords. If a keyword lacks a value on the same line, check the next non-blank line.
   - **Amount Priority**: Documents often contain multiple numbers. Use a strict priority order: `PAY THIS AMOUNT` > `AMOUNT DUE` > `TOTAL DUE` > `CURRENT CHARGES`. Explicitly ignore distractors (`PREVIOUS BALANCE`, `LATE FEE`, `USAGE`).
   - **Dates**: Convert all variants (`DD/MM/YYYY`, `DD-MM-YYYY`, `MM/YYYY`, `MM/DD/YYYY`) to `YYYY-MM-DD`. Default missing days to `01`. Disambiguate `DD/MM` vs `MM/DD` by checking if day > 12.
   - **Prices/Amounts**: Strip currency symbols and whitespace. Format to exactly two decimal places.
4. **Template Filling**: Load the existing Excel template with `openpyxl.load_workbook()`. Preserve all original sheets. Write extracted data to the target sheet (e.g., `bills`). Ensure headers match exactly. Save to a new path.
5. **Validation**: Cross-check 2-3 random samples against raw OCR output. Verify final Excel/CSV schema (headers, row count, column types). Ensure row count matches image count exactly.

## Critical Anti-Patterns
- **NEVER hardcode extracted values.** Always automate with a processing loop over sorted files.
- **Do not rely on `line[i+1]` for multi-line values without filtering blanks first.** OCR frequently inserts empty lines between labels and values.
- **Do not assume uniform date/price formats.** Invoices often mix separators and omit days.
- **Do not overwrite or drop template sheets.** Load the workbook, modify only the target sheet, and save.
- **Do not skip validation.** OCR can misread `0` as `O` or `1` as `I`. Spot-check outputs.

## Date Normalization Rules
- `DD/MM/YYYY` or `DD-MM-YYYY` -> `YYYY-MM-DD`
- `MM/YYYY` -> `YYYY-MM-01`
- If day > 12 and month <= 12, assume `DD/MM/YYYY`. If ambiguous, check context or default to `DD/MM/YYYY`.
- `MM/DD/YYYY` -> `YYYY-MM-DD` (only if day <= 12 and month > 12, or explicitly formatted).

## Troubleshooting
- **Missing fields after initial extraction**: Print raw OCR lines for failing images. Check for blank lines between keywords and values. Apply blank-line filtering before re-running.
- **Wrong amount extracted**: Verify keyword priority logic. Ensure distractor keywords are explicitly excluded or ranked lower.
- **Misaligned rows**: Ensure `sorted(glob.glob(...))` is used directly in the processing loop.
- **Verifier mismatch**: If tests fail, check column names, sheet names, and date formats against exact task requirements. Run a quick row-count check: `len(data_rows) == len(images)`.