---
name: ocr-structured-data
description: Extract structured tabular data (dates, prices, IDs) from batches of images using OCR. Use when tasked with converting image labels, receipts, or forms into Excel/CSV, especially when dates and prices appear in mixed formats.
---

# OCR Structured Data Extraction

## Workflow
1. **Inventory & Sort**: List all target images. Sort filenames explicitly *before* processing to guarantee row alignment.
2. **OCR Extraction**: Use `pytesseract` or equivalent to extract raw text per image.
3. **Field Parsing**: Apply regex to isolate target fields (dates, prices, product names).
4. **Normalization**:
   - Dates: Convert all variants (`DD/MM/YYYY`, `DD-MM-YYYY`, `MM/YYYY`) to `YYYY-MM-DD`. Default missing days to `01`.
   - Prices: Strip currency symbols (`$`, `RM`, `MYR`, etc.) and format to exactly two decimal places.
5. **Validation**: Cross-check 2-3 random samples against raw OCR output. Verify final Excel/CSV schema (headers, row count, column types).
6. **Export**: Write to the requested format (e.g., `.xlsx` with `openpyxl`).

## Critical Anti-Patterns
- **Do not sort file lists separately from processing results.** Process files in a single sorted loop to prevent index misalignment.
- **Do not assume uniform date/price formats.** Labels often mix separators (`/`, `-`) and omit days (`MM/YYYY`).
- **Do not skip validation.** OCR can misread `0` as `O` or `1` as `I`. Spot-check outputs.

## Date Normalization Rules
- `DD/MM/YYYY` or `DD-MM-YYYY` -> `YYYY-MM-DD`
- `MM/YYYY` -> `YYYY-MM-01`
- If day > 12 and month <= 12, assume `DD/MM/YYYY`. If ambiguous, check context or default to `DD/MM/YYYY`.

## Troubleshooting
- **Misaligned rows**: Ensure `sorted(glob.glob(...))` is used directly in the processing loop.
- **Missing fields**: If regex fails, print raw OCR text for that file and adjust patterns.
- **Currency confusion**: Extract numeric value first, then strip non-numeric chars except `.`.