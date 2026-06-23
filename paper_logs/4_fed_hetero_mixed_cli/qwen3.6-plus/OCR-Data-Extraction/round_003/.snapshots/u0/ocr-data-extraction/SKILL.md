---
name: ocr-data-extraction
description: Extract structured data (dates, prices, IDs) from images using OCR, parse into normalized formats, validate against reference files, handle duplicates, and export to Excel. Use when tasks require reading text from product labels, receipts, shipping orders, travel claims, or similar documents and converting them into tabular data with validation, deduplication, or roster matching.
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
4. **Extract & Parse**: Extract target fields using regex. Normalize dates to ISO format, prices to raw floats.
5. **Validate or Match Against Reference**: If a reference file is provided:
   - For validation: check extracted keys against valid set, flag or null unknowns.
   - For roster matching: join extracted keys (e.g., claim codes) to reference rows to populate additional fields (e.g., employee_id, trip_id). Leave fields empty for unmatched keys.
6. **Deduplicate**: If the task requires handling duplicates, identify duplicate key fields across the batch. Keep the first occurrence (by filename sort order), null out subsequent duplicates.
7. **Export**: Write to Excel with exact column names, sheet name, and sorting as specified.
8. **Verify**: Cross-check extracted values against raw OCR dumps for 2-3 images. Verify row count, duplicate handling, and reference validation.

## Key Decision Rules
- **OCR Strategy Selection**: Start simple. If `--psm 6` yields clean, parseable text, do not over-engineer with preprocessing or multiple PSM modes. Escalate only when fields are missing or garbled.
- **Date Ambiguity**: If format is `DD/MM` or `MM/DD`, check the first number. If `> 12`, it must be the day. If both `<= 12`, default to `DD/MM` for non-US contexts or infer from currency/locale.
- **Partial Dates**: If OCR yields `MM/YYYY`, default day to `01`.
- **Price Extraction**: Strip currency symbols and whitespace. Match numeric patterns. Keep raw float values; do not round or format to fixed decimals unless the task explicitly requires string formatting.
- **Duplicate Detection**: When multiple images may contain the same logical record (e.g., same order ID), sort by filename, track seen keys, and null out data for duplicates while preserving the filename row.
- **Reference Validation vs Roster Matching**: Validation checks if extracted keys exist in a reference set. Roster matching joins extracted keys to reference rows to populate additional columns. For roster matching, leave joined fields empty (not null-string) when the key has no match.
- **openpyxl Row Writing**: Always capture `row_num = ws.max_row + 1` once before iterating columns. Never call `ws.max_row + 1` inside a column loop, as it increments after each cell write and scatters values across rows.

## Anti-Patterns
- Do not rely on a single PSM or preprocessing step when OCR output is noisy.
- Do not assume date formats are consistent across all images in a batch.
- Do not skip verification. OCR can hallucinate or misread digits.
- Do not over-engineer OCR when initial output is clean. Start simple, escalate only when needed.
- Do not round, truncate, or fixed-format numeric values when writing outputs unless explicitly required.
- Do not ignore reference files. They define valid values and should be used for validation or roster matching.
- **Do not use `ws.cell(row=ws.max_row + 1, column=col, value=...)` inside a column loop.** This writes each cell to a new row. Capture the row number once: `row_num = ws.max_row + 1` before the loop.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

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

## Scripts & References
- Run `scripts/ocr_extract.py` to perform multi-strategy OCR on a directory of images and output a CSV. Use it as a baseline or debugging tool.
- Run `scripts/extract_to_excel.py` as a template for end-to-end OCR → Excel pipelines. Adapt the parse functions for your specific fields.
- Read `references/parsing_patterns.md` for robust regex templates and disambiguation logic for dates and prices.
- Read `references/dedup_validation_patterns.md` for duplicate detection logic and reference file validation patterns.
- Read `references/roster_matching_patterns.md` for roster-matching workflows and openpyxl row-writing best practices.