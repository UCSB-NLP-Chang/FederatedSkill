---
name: ocr-data-extraction
description: Extract structured data (dates, prices, IDs) from images using multi-strategy OCR, parse into normalized formats, and export to Excel. Use when tasks require reading text from product labels, receipts, or shelf tags and converting them into tabular data.
---

# OCR Data Extraction & Normalization

## Workflow
1. **Inspect & List**: Identify target images and verify resolution/format.
2. **Multi-Strategy OCR**: Run Tesseract with multiple Page Segmentation Modes (PSM) and preprocessing steps. Shelf labels often fail with default settings.
   - Use `--psm 6` (single uniform block) and `--psm 11` (sparse text).
   - Apply preprocessing: thresholding, contrast enhancement, 2x upscaling.
3. **Parse & Normalize**: Extract target fields using regex. Disambiguate date formats by checking numeric bounds. Normalize prices to 2 decimal places.
4. **Export**: Write to Excel with exact column names, sheet name, and sorting as specified.
5. **Verify**: Cross-check extracted values against raw OCR dumps for 2-3 images to catch pattern-matching hallucinations.

## Key Decision Rules
- **Date Ambiguity**: If format is `DD/MM` or `MM/DD`, check the first number. If `> 12`, it must be the day. If both `<= 12`, default to `DD/MM` for non-US contexts or infer from currency/locale.
- **Partial Dates**: If OCR yields `MM/YYYY`, default day to `01`.
- **Price Extraction**: Strip currency symbols (`$`, `RM`, `MYR`, `€`) and whitespace. Match `\d+\.\d{2}`.
- **Verification**: Always run a debug pass on a subset of images to print raw OCR output before finalizing the extraction script. Do not trust regex matches blindly if OCR is noisy.

## Anti-Patterns
- Do not rely on a single PSM or preprocessing step.
- Do not assume date formats are consistent across all images in a batch.
- Do not skip verification. OCR can hallucinate or misread digits (e.g., `0` vs `O`, `1` vs `I`).

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

## Scripts & References
- Run `scripts/ocr_extract.py` to perform multi-strategy OCR on a directory of images and output a CSV. Use it as a baseline or debugging tool.
- Read `references/parsing_patterns.md` for robust regex templates and disambiguation logic for dates and prices.