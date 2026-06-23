---
name: image-data-extraction
description: Extract structured data (dates, prices, order IDs, totals) from images using Tesseract OCR with robust multi-pass preprocessing, regex parsing, and Excel output. Use when tasks require reading text from product labels, receipts, invoices, orders, or scanned documents with varying formats and image quality.
---

# Image OCR Data Extraction

## Overview
Extract structured fields from images using `pytesseract`. This workflow handles inconsistent image quality, varied formats, and outputs normalized data to Excel/CSV. It supports both label/receipt extraction and order/invoice processing.

## Workflow
1. **Inspect & Enumerate Images**: Identify target directory and fields (e.g., `EXP:`, `PRICE:`, `ORDER ID:`, `TOTAL:`). Note format variations.
2. **Run Multi-Pass OCR**: Use `scripts/extract_ocr_data.py` (labels) or `scripts/extract_order_data.py` (orders/invoices). Run Tesseract with multiple preprocessing modes (`grayscale`, `high_contrast`, `threshold`, `upscale`, `inverted`) and PSM configs (`6`, `4`, `3`, `1`, `11`). Aggregate extracted text.
3. **Parse & Normalize**:
   - **Dates**: Match `DD/MM/YYYY`, `MM-DD-YYYY`, `MM/YYYY`, etc. Normalize to `YYYY-MM-DD`. Use day `01` for month-only. Prioritize expiry over manufacture dates.
   - **Prices/Totals**: Match currency symbols (`RM`, `MYR`, `$`, `€`) or keywords (`TOTAL`, `AMOUNT`). Strip non-numeric chars except `.`.
   - **Order IDs**: Match patterns like `INV-YYYYNNNN`, `ORD-YYYY-NNNNN`, `SO-YYYY-NNN`. Validate against reference file if provided.
4. **Handle Duplicates & Validation**: Decide strategy based on task spec (see below). Validate extracted values against reference data if available.
5. **Output**: Write to Excel with appropriate columns. Sort by filename. Verify row count matches image count.
6. **Spot-check**: Print raw OCR output for 3-5 random images to confirm parsing.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Duplicate Handling & Reference Validation
Duplicate handling depends on task requirements. Choose explicitly:
- **Preserve All (Default for 1:1 image-to-row mapping)**: Each image is a separate record. DO NOT null out duplicate rows or filter them out. Preserve all rows with their extracted data, even if order IDs repeat.
- **First-Wins (Mark Subsequent Empty)**: If the task explicitly requires deduplication, keep the first occurrence with full data. For subsequent images with the same identifier, preserve the row but write `None` (empty cell) for other fields. Do not skip rows.
- **Reference Validation**: If a reference file (e.g., `known_orders.csv`) is provided, validate extracted IDs against it. Keep extracted values if they match; set to `None` only if they fail validation.

## Anti-Patterns
- **Do not manually read images and hardcode data.** Always use OCR automation to extract text programmatically.
- **Do not rely on a single Tesseract `--psm` mode.** Layouts vary; combine `psm 6`, `4`, `3`, etc.
- **Do not hardcode date/price parsing for one format.** Use regex with fallbacks.
- **Do not skip validation.** OCR hallucinates; cross-check raw outputs.
- **Do not format prices with fixed decimal places.** Pass raw floats.
- **Do not deduplicate rows unless explicitly requested.** Each image represents a physical record.

## Script Usage
- Run `scripts/extract_ocr_data.py` for product labels (columns: `filename`, `date`, `price`).
- Run `scripts/extract_order_data.py` for orders/invoices (columns: `filename`, `order_id`, `date`, `total_amount`). Supports reference file validation and multi-pass OCR.
- Update `IMG_DIR`, `OUTPUT`, `REFERENCE_FILE`, and regex patterns as needed.

## Known invariants (by sub-task)

### pharmacy-shelf-label
- Output Excel must have exactly 3 columns: `filename`, `date`, `price`
- Row count must equal input image count
- Dates normalized to ISO YYYY-MM-DD; use day `01` for month-only dates
- Price extraction handles RM, MYR, $, EUR currencies

### ecommerce-orders
- Output Excel must have 4 columns: `filename`, `order_id`, `date`, `total_amount`
- Row count must equal input image count
- Order IDs validated against reference file if provided; invalid IDs set to `None`
- Dates normalized to ISO YYYY-MM-DD
- Total amounts as raw floats (no fixed formatting)
- **All rows preserved** unless task explicitly mandates deduplication (then mark subsequent duplicates empty)

## Reference Files
- `references/patterns.md`: Ready-to-use regex patterns for dates, prices, order IDs, codes, and OCR cleanup.