---
name: ocr-data-extraction
description: Extract structured data (dates, prices, IDs, line items) from images using OCR, parse into normalized formats, validate against reference files, handle duplicates, and export to Excel. Use when tasks require reading text from product labels, receipts, shipping orders, travel claims, utility bills, construction forms, or similar documents and converting them into tabular data with validation, deduplication, roster matching, or multi-item extraction.
---

# OCR Data Extraction & Normalization

## Workflow
1. **Inspect & List**: Identify target images and verify resolution/format. Check for any reference files (CSV, JSON) that define valid values, expected schemas, or roster mappings.
2. **Probe OCR Quality**: Run a quick OCR pass on 2-3 images using `--psm 6` (single uniform block). Inspect the raw output.
   - If output is clean and structured, proceed with single-strategy OCR.
   - If output is noisy, missing fields, or garbled, escalate to multi-strategy OCR (see below).
3. **Multi-Strategy OCR** (only if needed): Run Tesseract with multiple PSM modes and preprocessing.
   - Use `--psm 6` (single uniform block) and `--psm 11` (sparse text).
   - Apply preprocessing: thresholding, contrast enhancement, 2x upscaling.
   - **Deduplicate results**: Multiple strategies may return the same items. Track seen items with a set keyed by unique identifier (e.g., item description per document).
4. **Extract & Parse**: Extract target fields using regex. Normalize dates to ISO format, prices to raw floats. For tabular/line-item data, clean OCR artifacts first and use context-aware quantity extraction (see Tabular Extraction section).
5. **Validate or Match Against Reference**: If a reference file is provided:
   - For validation: check extracted keys against valid set, flag or null unknowns.
   - For roster matching: join extracted keys (e.g., claim codes) to reference rows to populate additional fields (e.g., employee_id, trip_id). Leave fields empty for unmatched keys.
6. **Deduplicate**: If the task requires handling duplicates, identify duplicate key fields across the batch. Keep the first occurrence (by filename sort order), null out subsequent duplicates.
7. **Export**: Write to Excel with exact column names, sheet name, and sorting as specified. For multi-item extraction, create separate sheets for details and summary.
8. **Verify**: Cross-check extracted values against raw OCR dumps for 2-3 images. Verify row count, duplicate handling, and reference validation.

## Key Decision Rules
- **OCR Strategy Selection**: Start simple. If `--psm 6` yields clean, parseable text, do not over-engineer with preprocessing or multiple PSM modes. Escalate only when fields are missing or garbled.
- **Date Ambiguity**: If format is `DD/MM` or `MM/DD`, check the first number. If `> 12`, it must be the day. If both `<= 12`, default to `DD/MM` for non-US contexts or infer from currency/locale.
- **Partial Dates**: If OCR yields `MM/YYYY`, default day to `01`.
- **Invoice Total Extraction**: Invoices often contain multiple monetary values. Prioritize extraction in this order: `GRAND TOTAL` > `TOTAL DUE` > `PAY THIS AMOUNT` > `CURRENT CHARGES` > `TOTAL`. Explicitly ignore lines containing `SUBTOTAL`, `TAX`, `VAT`, `SHIPPING`, or `DISCOUNT`. If multiple total keywords appear, use the highest priority match.
- **Multi-Line Keywords**: OCR frequently splits compound keywords across lines with blank lines in between (e.g., `TOTAL\n\nDUE: 120.75` or `PAY THIS AMOUNT\n\n1234.56`). When a keyword is found but no amount follows on the same line, search the next 3-5 lines for the amount pattern. For compound keywords like "TOTAL DUE", check if "TOTAL" appears on one line and "DUE" on a subsequent line, then extract from the "DUE" line.
- **Price Extraction**: Strip currency symbols and whitespace. Match numeric patterns. Keep raw float values; do not round or format to fixed decimals unless the task explicitly requires string formatting.
- **Duplicate Detection**: When multiple images may contain the same logical record (e.g., same order ID), sort by filename, track seen keys, and null out data for duplicates while preserving the filename row.
- **Reference Validation vs Roster Matching**: Validation checks if extracted keys exist in a reference set. Roster matching joins extracted keys to reference rows to populate additional columns. For roster matching, leave joined fields empty (not null-string) when the key has no match.
- **openpyxl Row Writing**: Always capture `row_num = ws.max_row + 1` once before iterating columns. Never call `ws.max_row + 1` inside a column loop, as it increments after each cell write and scatters values across rows.

## Tabular & Line-Item Extraction
When OCR output contains table rows with mixed text, numbers, and units (e.g., construction forms, measurement sheets):
1. **Clean Artifacts First**: Strip `=`, `~`, `§`, `«`, `»`, `—`, `–` that act as column separators or noise before parsing.
2. **Context-Aware Quantity Extraction**: When item names contain numbers (e.g., "Concrete C30 50 m³ $150.00"), match quantities AFTER the item name, not just any `\d+` on the line. Naive regex will match "30" from "C30" instead of quantity "50". See `references/parsing_patterns.md` for `extract_quantity_with_context()`.
3. **Parse with Priority Regex**: Match description (allowing digits like `C30`), then quantity, then skip units, then price.
4. **Fallback to Number Positioning**: If regex fails, extract all numbers. Assume last = price, second-to-last = quantity, prefix = description.
5. **Deduplicate Across OCR Strategies**: Multiple OCR passes may return the same items. Use a set keyed by item identifier (description) to deduplicate.
6. **Write Raw Floats**: Always write prices/quantities as raw floats to Excel. Do not format as strings unless explicitly required.

## Anti-Patterns
- Do not rely on a single PSM or preprocessing step when OCR output is noisy.
- Do not assume date formats are consistent across all images in a batch.
- Do not skip verification. OCR can hallucinate or misread digits.
- Do not over-engineer OCR when initial output is clean. Start simple, escalate only when needed.
- Do not round, truncate, or fixed-format numeric values when writing outputs unless explicitly required.
- Do not ignore reference files. They define valid values and should be used for validation or roster matching.
- **Do not use `ws.cell(row=ws.max_row + 1, column=col, value=...)` inside a column loop.** This writes each cell to a new row. Capture the row number once: `row_num = ws.max_row + 1` before the loop.
- **Do not assume keywords and values are on the same line.** Always check subsequent lines when a keyword is found but no value follows immediately.
- **Do not parse tabular lines without cleaning OCR artifacts first.** Characters like `=`, `~`, `§` will break naive regex splits.
- **Do not use naive `\d+` regex for quantities when item names contain numbers.** Match quantities after the item name, not anywhere on the line.
- **Do not forget to deduplicate across OCR strategies.** Multiple strategies can return the same items.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### B1: Image OCR → Excel with date/price extraction
- Output Excel must have columns exactly as specified (e.g., {filename, date, price})
- Dates must be ISO format YYYY-MM-DD; partial MM/YYYY → YYYY-MM-01
- Prices as float with full precision (no rounding in script)
- Row count must match image count
- Sorted by filename

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

### B4: Multi-item extraction per document (e.g., construction forms)
- Each document may contain multiple line items (description, quantity, unit price)
- Deduplicate items across OCR strategies using a set keyed by item identifier (description)
- Use context-aware regex for quantities when item names contain numbers
- Output details sheet with one row per item, summary sheet with aggregated totals
- Group by project/order code for summaries

## Scripts & References
- Run `scripts/ocr_extract.py` to perform multi-strategy OCR on a directory of images and output a CSV. Use it as a baseline or debugging tool.
- Run `scripts/extract_to_excel.py` as a template for end-to-end OCR → Excel pipelines. Adapt the parse functions for your specific fields.
- Read `references/parsing_patterns.md` for robust regex templates, invoice total keyword priority, multi-line keyword handling, tabular line-item parsing, context-aware quantity extraction, and multi-item deduplication.
- Read `references/dedup_validation_patterns.md` for duplicate detection logic and reference file validation patterns.
- Read `references/roster_matching_patterns.md` for roster-matching workflows and openpyxl row-writing best practices.
