---
name: image-data-extraction
description: Extract structured data (dates, prices, labels) from images using Tesseract OCR with robust multi-pass preprocessing, regex parsing, and Excel output. Use when tasks require reading text from product labels, receipts, or scanned documents with varying formats and image quality.
---

# Image OCR Data Extraction

## Overview
Extract structured fields (dates, prices, identifiers) from images using `pytesseract`. This workflow handles inconsistent image quality, varied date/price formats, and outputs normalized data to Excel.

## Workflow
1. **Inspect Images**: Identify target fields (e.g., `EXP:`, `MFG:`, `PRICE:`, currency symbols). Note format variations across the dataset.
2. **Run Multi-Pass OCR**: Use `scripts/extract_ocr_data.py` or replicate its logic. Run Tesseract with multiple preprocessing modes (`grayscale`, `high_contrast`, `threshold`, `upscale`) and PSM configs (`6`, `4`, `3`, `1`). Aggregate all extracted text.
3. **Parse & Normalize**:
   - **Dates**: Match `DD/MM/YYYY`, `MM-DD-YYYY`, `MM/YYYY`, etc. Normalize to `YYYY-MM-DD`. Use day `01` for month-only dates. Prioritize expiry dates over manufacture dates if both appear.
   - **Prices**: Match currency symbols (`RM`, `MYR`, `$`, `€`) followed by digits. Strip non-numeric chars except `.`. Pass raw float value.
4. **Output**: Write to Excel with columns `filename`, `date`, `price`. Sort by filename. Verify row count matches image count.
5. **Validate**: Spot-check 3-5 random images by printing raw OCR output. Confirm parsed values match visual inspection.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Decision Rules
- **If OCR returns empty or garbled text**: Switch to multi-pass preprocessing. Thresholding and upscaling often fix low-contrast or small text.
- **If date format is ambiguous (e.g. 02-04-2025)**: Check surrounding context or dataset conventions. If `DD-MM-YYYY` is standard, parse accordingly. Use `>12` heuristic: if first component > 12, it's a day.
- **If multiple dates exist**: Prioritize `EXP`/`EXPIRY` over `MFG`/`MANUFACTURED` per typical spec requirements.
- **If price extraction fails**: Look for currency codes (`RM`, `MYR`) or symbols (`$`, `€`). Ignore suffixes like `EACH` or `PER UNIT`.

## Anti-Patterns
- Do not rely on a single Tesseract `--psm` mode. Layouts vary; `psm 6` (block) and `psm 4` (column) often complement each other.
- Do not hardcode date parsing for one format. Use regex with fallbacks.
- Do not skip validation. OCR hallucinates; always cross-check a subset of raw outputs.

## Script Usage
Run `scripts/extract_ocr_data.py` to process a directory of images. Update `IMG_DIR`, `OUTPUT`, and regex patterns as needed. The script handles preprocessing, multi-pass OCR, parsing, and Excel generation automatically.

## Known invariants (by sub-task)

### pharmacy-shelf-label
- Output Excel must have exactly 3 columns: `filename`, `date`, `price`
- Row count must equal input image count
- Dates normalized to ISO YYYY-MM-DD; use day `01` for month-only dates
- Price extraction handles RM, MYR, $, EUR currencies

## Reference Files
- `references/patterns.md`: Ready-to-use regex patterns for dates, prices, codes