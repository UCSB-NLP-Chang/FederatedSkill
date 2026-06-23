---
name: ocr-structured-data
description: Extract structured tabular data (dates, prices, IDs) from batches of images using OCR. Use when tasked with converting image labels, receipts, invoices, or forms into Excel/CSV, especially when dates and prices appear in mixed formats.
---

# OCR Structured Data Extraction

## Workflow
1. **Inventory & Sort**: List all target images. Sort filenames explicitly *before* processing to guarantee row alignment.
2. **Script Generation**: Write a single Python script that loops over the sorted images, runs OCR (`pytesseract`), parses fields via regex, normalizes values, and writes to Excel/CSV. **Do not manually extract data and hardcode it.**
3. **Field Parsing & Normalization**:
   - Dates: Convert all variants (`DD/MM/YYYY`, `DD-MM-YYYY`, `MM/YYYY`, `MM/DD/YYYY`) to `YYYY-MM-DD`. Default missing days to `01`. Disambiguate `DD/MM` vs `MM/DD` by checking if day > 12.
   - Prices/Amounts: Strip currency symbols and whitespace. Format to exactly two decimal places.
   - Multi-line values: If a keyword lacks a value on the same line, check the immediately following line.
4. **Validation**: Cross-check 2-3 random samples against raw OCR output. Verify final Excel/CSV schema (headers, row count, column types).
5. **Export**: Write to the requested format (e.g., `.xlsx` with `openpyxl`). Ensure row count matches image count exactly.

## Critical Anti-Patterns
- **NEVER hardcode extracted values.** Manually reading images and typing values into a script is brittle and error-prone. Always automate with a processing loop.
- **Do not sort file lists separately from processing results.** Process files in a single sorted loop to prevent index misalignment.
- **Do not assume uniform date/price formats.** Invoices often mix separators and omit days.
- **Do not skip validation.** OCR can misread `0` as `O` or `1` as `I`. Spot-check outputs.

## Date Normalization Rules
- `DD/MM/YYYY` or `DD-MM-YYYY` -> `YYYY-MM-DD`
- `MM/YYYY` -> `YYYY-MM-01`
- If day > 12 and month <= 12, assume `DD/MM/YYYY`. If ambiguous, check context or default to `DD/MM/YYYY`.
- `MM/DD/YYYY` -> `YYYY-MM-DD` (only if day <= 12 and month > 12, or explicitly formatted).

## Troubleshooting
- **Misaligned rows**: Ensure `sorted(glob.glob(...))` is used directly in the processing loop.
- **Missing fields**: If regex fails, print raw OCR text for that file and adjust patterns.
- **Currency confusion**: Extract numeric value first, then strip non-numeric chars except `.`.
- **Verifier mismatch**: If tests fail, check column names, sheet names, and date formats against exact task requirements. Run a quick row-count check: `len(data_rows) == len(images)`.
