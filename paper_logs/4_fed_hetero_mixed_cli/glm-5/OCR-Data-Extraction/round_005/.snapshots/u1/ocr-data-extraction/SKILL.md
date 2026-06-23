---
name: ocr-data-extraction
description: Extract structured data (dates, prices, text fields, IDs) from images using OCR. Use when processing scanned documents, product labels, receipts, invoices, utility bills, order confirmations, travel claims, or any image containing text that needs to be parsed into structured formats like Excel or CSV. Supports duplicate detection, reference validation, roster matching, invoice total extraction, multi-line keyword handling, and date format disambiguation.
---

# Image OCR Data Extraction

Extract structured data from images using OCR with robust preprocessing and parsing strategies.

## When to Use
- Processing product labels, receipts, shelf tags, or order confirmations
- Extracting dates, prices, IDs, or other structured fields from images
- Batch processing multiple images into a spreadsheet
- Processing invoices with total amounts (GRAND TOTAL, TOTAL DUE, etc.)
- Processing utility bills with multi-line keywords (PAY THIS AMOUNT, CURRENT CHARGES)
- When images contain text that needs structured extraction
- When duplicate records need detection and handling
- When extracted values need validation against a reference list
- When merging image data with external reference files (rosters, catalogs)
- When date formats are ambiguous (DD/MM vs MM/DD in same batch)

## Workflow

1. **Always use OCR for image extraction** - never manually transcribe image content. Use `scripts/extract_to_excel.py` as a template.

2. **Preprocess images** for better OCR accuracy:
   - Convert to grayscale
   - Enhance contrast (2.0x typically works well)
   - Apply sharpening filter

3. **Try multiple OCR strategies** - combine results:
   - Default pytesseract configuration
   - Preprocessed image
   - Multiple PSM modes (4, 6, 11, 12 are most useful for structured text)

4. **Parse dates with priority rules and format disambiguation**:
   - EXP/EXPIRY dates take priority over MFG (manufacture) dates
   - Support formats: DD/MM/YYYY, DD-MM-YYYY, MM/YYYY, YYYY-MM-DD
   - For month/year only (e.g., 04/2026), convert to first day of month
   - **Handle date ambiguity**: Same batch may mix DD/MM/YYYY and MM/DD/YYYY formats.
     Try DD/MM first, validate calendar feasibility (day ≤ 31, month ≤ 12), then fall back to MM/DD if invalid.
     Example: `02/14/2024` → day=14 > month=12 max, so must be MM/DD → `2024-02-14`.
     See `references/regex_patterns.md` for `extract_date_with_fallback()` function.

5. **Extract prices and invoice totals**:
   - Strip currency symbols (RM, MYR, $, etc.)
   - Handle formats like "RM 10.99", "$15.99 EACH", "MYR 18.49"
   - **Invoice total priority**: When extracting totals from invoices or utility bills, use this order:
     1. `GRAND TOTAL` (highest priority, most specific)
     2. `TOTAL DUE` or `TOTAL AMOUNT`
     3. `PAY THIS AMOUNT` (common on utility bills)
     4. `CURRENT CHARGES` (utility bills when no total due shown)
     5. `TOTAL` (generic, but exclude lines with `SUBTOTAL`, `TAX`, `VAT`, `SHIPPING`, `DISCOUNT`)
     If multiple total keywords appear, pick the highest priority match.
     **Multi-line keywords**: OCR frequently splits compound keywords across lines with blank lines in between (e.g., `TOTAL\n\nDUE: 120.75` or `PAY THIS AMOUNT\n\n1234.56`). When a keyword is found but no amount follows on the same line, search the next 3-5 lines for the amount pattern. For compound keywords like "TOTAL DUE", check if "TOTAL" appears on one line and "DUE" on a subsequent line, then extract from the "DUE" line. See `references/parsing_patterns.md` for `extract_amount_multiline()` function.
     See `references/regex_patterns.md` for total extraction patterns with priority.

6. **Handle duplicates** (when extracting IDs):
   - Track seen IDs/values in a set as you process
   - For duplicate occurrences, set all extractable fields to null/empty
   - Keep the filename/identifier but null the data fields

7. **Validate against reference files** (when available):
   - Load known valid values from CSV or reference file
   - Flag or reject extracted values not in the reference set
   - Useful for validating order IDs, product codes, SKUs

8. **Merge with external data** (rosters, catalogs, etc.):
   - Load reference file early (CSV, JSON)
   - Join on common key (claim_code, order_id, etc.)
   - For unmatched keys, leave join fields as empty/null cells
   - See `references/roster_matching_patterns.md` for patterns

9. **Output to Excel**:
   - Use openpyxl for .xlsx files
   - Include columns: filename, date, price (or relevant fields)
   - Sort by filename for consistency
   - Remove any trailing empty rows before saving

## Output Precision (CRITICAL)

**Never round, truncate, or fixed-format numeric values when writing outputs.**

This is the most common error. Pass raw float values directly to Excel cells:

```python
# WRONG - causes test failures:
ws.cell(row=r, column=c, value=f"{price:.2f}")  # String, not number
ws.cell(row=r, column=c, value=round(price, 2))
ws.cell(row=r, column=c, value=format(price, ".2f"))

# CORRECT - pass raw float:
ws.cell(row=r, column=c, value=price)  # Let Excel handle display
```

Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Validation Steps

Before finalizing output:

1. **Verify numeric types**: Check that price/amount columns contain floats, not formatted strings
   ```python
   from openpyxl import load_workbook
   wb = load_workbook('output.xlsx')
   ws = wb.active
   for row in ws.iter_rows(min_row=2, max_row=5):
       for cell in row:
           if 'amount' in ws.cell(row=1, column=cell.column).value.lower():
               assert isinstance(cell.value, (int, float, type(None))), \
                   f"Expected number, got {type(cell.value)}"
   ```
2. **Verify row count** matches image count
3. **Check all dates parsed** successfully (no None values unless expected)
4. **Confirm prices are numeric** and reasonable
5. **Spot-check a few images** against extracted values
6. **If using reference validation**, confirm all valid IDs were accepted

## Anti-Patterns

- **Don't manually transcribe image content** - always use OCR
- Don't rely on single OCR pass - always try multiple strategies
- Don't assume date format - detect DD/MM vs MM/DD contextually; validate calendar feasibility and use fallback
- **Don't grab SUBTOTAL/TAX instead of GRAND TOTAL** on invoices — use the priority order
- Don't skip preprocessing for low-quality images
- Don't ignore date type labels (EXP vs MFG matter for interpretation)
- **Don't round or truncate numeric values in output files** - this is the #1 cause of test failures
- Don't format numbers as strings in Excel cells
- Don't forget to clean up empty trailing rows in Excel output
- **Don't use `ws.cell(row=ws.max_row + 1, column=col, value=...)` inside a column loop.** This writes each cell to a new row. Capture the row number once: `row_num = ws.max_row + 1` before the loop.
- **Don't assume keywords and values are on the same line.** OCR splits compound keywords across lines (e.g., `TOTAL\n\nDUE: 120.75`). When a keyword is found without an immediate value, search the next 3-5 lines.

## Troubleshooting

- If OCR returns empty or garbled text, try different PSM modes
- If dates fail to parse, check for OCR misreads (O→0, l→1, etc.)
- If prices have wrong values, verify currency symbol stripping
- If duplicate detection fails, ensure ID extraction is consistent across OCR passes
- If reference validation rejects valid IDs, check for whitespace/formatting differences
- **If tests fail on numeric precision**, check that you're passing raw floats, not formatted strings

## Known invariants (by sub-task)

### B1: Image OCR → Excel with date/price extraction
- Output Excel must have columns exactly as specified (e.g., {filename, date, price})
- Dates must be ISO format YYYY-MM-DD; partial MM/YYYY → YYYY-MM-01
- Prices as float with full precision (no rounding in script)
- Row count must match image count
- Sorted by filename
- **Invoice total priority**: `GRAND TOTAL` > `TOTAL DUE` > `PAY THIS AMOUNT` > `CURRENT CHARGES` > `TOTAL`. Explicitly exclude `SUBTOTAL`, `TAX`, `VAT`, `SHIPPING`, `DISCOUNT` lines. (R3 u0/u1/u2: all workers validated this priority.)
- **Date disambiguation**: Try DD/MM first, validate calendar, fall back to MM/DD. Do not assume consistent format across batch. (R3 u2: initial failure on `02/14/2024`, fixed by validation fallback.)
- **Utility bills**: Use `PAY THIS AMOUNT` or `CURRENT CHARGES` when `TOTAL DUE` not present. (R4 u1: utility bill extraction validated.)
- **Multi-line keywords**: OCR splits compound keywords across lines (e.g., `TOTAL\n\nDUE: 120.75`). Search next 3-5 lines when keyword found without immediate value. (R4 u0: multi-line handling validated.)

### B2: OCR with duplicate handling & reference validation
- When duplicate keys exist across images, keep first occurrence by filename sort order
- Null out data fields for duplicate rows (preserve filename)
- Validate extracted keys against reference file if provided
- Output must include all input files as rows, even if data is null

### B3: OCR with roster matching (e.g., travel claims)
- Extract key field (e.g., claim_code) from each image
- Load roster/reference CSV into a dict keyed by the extracted field
- For each image, populate additional columns (e.g., employee_id, trip_id) from the roster dict
- If key not in roster, leave those columns empty (None in openpyxl → empty cell in Excel)
- All input files must appear as rows, even if unmatched

## References
- `scripts/extract_to_excel.py` - Complete implementation template
- `references/regex_patterns.md` - Extended regex library for dates, prices, codes, order IDs, invoice totals, utility bill patterns, and date disambiguation functions
- `references/parsing_patterns.md` - Multi-line keyword handling patterns, invoice total extraction with priority, date disambiguation logic, and OCR artifact corrections
- `references/dedup_validation_patterns.md` - Patterns for duplicate detection and reference file validation
- `references/roster_matching_patterns.md` - Roster-matching workflows and openpyxl row-writing best practices
