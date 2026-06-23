---
name: ocr-data-extraction
description: Extract structured data (dates, prices, text fields) from images using OCR. Use when processing scanned documents, product labels, receipts, or any image containing text that needs to be parsed into structured formats like Excel or CSV.
---

# Image OCR Data Extraction

Extract structured data from images using OCR with robust preprocessing and parsing strategies.

## When to Use
- Processing product labels, receipts, or shelf tags
- Extracting dates, prices, or other structured fields from images
- Batch processing multiple images into a spreadsheet
- When images contain text that needs structured extraction

## Workflow

1. **Preprocess images** for better OCR accuracy:
   - Convert to grayscale
   - Enhance contrast (2.0x typically works well)
   - Apply sharpening filter

2. **Try multiple OCR strategies** - combine results:
   - Default pytesseract configuration
   - Preprocessed image
   - Multiple PSM modes (4, 6, 11, 12 are most useful for structured text)

3. **Parse dates with priority rules**:
   - EXP/EXPIRY dates take priority over MFG (manufacture) dates
   - Support formats: DD/MM/YYYY, DD-MM-YYYY, MM/YYYY, YYYY-MM-DD
   - For month/year only (e.g., 04/2026), convert to first day of month

4. **Extract prices**:
   - Strip currency symbols (RM, MYR, $, etc.)
   - Handle formats like "RM 10.99", "$15.99 EACH", "MYR 18.49"
   - Format to 2 decimal places

5. **Output to Excel**:
   - Use openpyxl for .xlsx files
   - Include columns: filename, date, price (or relevant fields)
   - Sort by filename for consistency

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Validation Steps
- Verify row count matches image count
- Check all dates parsed successfully (no None values)
- Confirm prices are numeric and reasonable
- Spot-check a few images against extracted values

## Anti-Patterns
- Don't rely on single OCR pass - always try multiple strategies
- Don't assume date format - detect DD/MM vs MM/DD contextually
- Don't skip preprocessing for low-quality images
- Don't ignore date type labels (EXP vs MFG matter for interpretation)
- Don't round or truncate numeric values in output files

## Troubleshooting
- If OCR returns empty or garbled text, try different PSM modes
- If dates fail to parse, check for OCR misreads (O→0, l→1, etc.)
- If prices have wrong values, verify currency symbol stripping

## References
- `scripts/extract_to_excel.py` - Complete implementation template
- `references/regex_patterns.md` - Extended regex library for dates, prices, codes
