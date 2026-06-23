---
name: image-data-extraction
description: Extract structured data (dates, prices, order IDs, totals) from image batches using OCR with multi-pass preprocessing, regex parsing, deduplication handling, and Excel output.
---

# Image Data Extraction

Extract structured data from multiple images and write to a formatted Excel file. Handles variable image quality, multiple document types, and batch processing requirements.

## When to Use
- Processing shelf labels, receipts, invoices, orders, or scanned documents
- Extracting consistent fields (dates, prices, IDs, totals) across multiple images
- Converting visual data to structured tabular formats
- Tasks requiring 1:1 image-to-row mapping, duplicate handling, or external validation

## Workflow
1. **Enumerate images**: List all image files in the target directory
2. **Preprocess & OCR**: Apply multi-pass preprocessing strategies (see OCR Strategy below) with fallback PSM configs
3. **Parse & Normalize**:
   - Dates: Normalize to `YYYY-MM-DD`. Use day `01` for month-only dates.
   - Prices/Totals: Extract raw floats, strip thousands separators. Do not format/round.
   - Order IDs: Match known patterns, validate against reference files if provided.
4. **Handle Duplicates**: Track seen identifiers. If 1:1 row mapping required, keep first occurrence with full data; write subsequent duplicates with filename only (other fields `None`/empty).
5. **Output**: Write Excel with header row and one row per image. Sort by filename.
6. **Validate**: Check row count matches image count, verify date/price formatting, spot-check OCR output.

## OCR Preprocessing Strategy
Always apply multiple preprocessing approaches to handle variable image quality:
- **Grayscale**: `image.convert('L')`
- **High Contrast**: `ImageEnhance.Contrast(gray).enhance(2.0-2.5)`
- **Threshold/Binarization**: `gray.point(lambda x: 0 if x < threshold else 255)`
- **Upscale**: `image.resize((w*2, h*2), Image.LANCZOS)`
- **PSM Fallbacks**: Try `--psm 6` (block), `4` (column), `3` (auto), `1` (sparse text)
Aggregate all extracted text or stop when length exceeds minimum threshold.

## Deduplication Strategy
When multiple images contain the same logical record (e.g., same order ID):
- **Default (1:1 Row Mapping)**: Use "first-wins with empty markers". Write the first occurrence with full data. For subsequent images with the same ID, write a row with `filename` populated but `None` for other fields. `openpyxl` writes `None` as empty cells automatically.
- **Filter Mode**: Only use if task explicitly says "output unique records only".
- Track seen IDs in a `set()` during iteration. Normalize IDs (strip whitespace, uppercase) before comparison.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## External Validation
If a reference file (e.g., `known_orders.csv`) is provided:
```python
import csv
with open(reference_file) as f:
    valid_ids = set(row['order_id'] for row in csv.DictReader(f) if row.get('order_id'))
# Validate: extracted_id if extracted_id in valid_ids else None
```

## Known invariants (by sub-task)

### pharmacy-shelf-label
- Output Excel columns: `{filename, date, price}` in exact order
- Date extraction priority: `EXP`/`EXPIRY` > `EXPIRES` > `MFG`/`MANUFACTURED`
- Price extraction priority: labeled `PRICE:` > raw currency (`RM`, `MYR`, `$`)
- Row count must exactly match input image count
- Sort by filename ascending

### ecommerce-orders
- Output Excel columns: `{filename, order_id, date, total_amount}` in exact order
- Order ID patterns: `ORD-YYYY-NNNNN`, `SO-YYYY-NNN`, `INV-YYYYMMDD`
- Duplicate handling: First-wins with empty cells for subsequent occurrences
- Row count must exactly match input image count
- Sort by filename ascending

## Validation Checklist
- [ ] Row count = number of images processed
- [ ] No empty rows between data
- [ ] Dates normalized to ISO `YYYY-MM-DD`
- [ ] Numeric fields are raw floats, not formatted strings
- [ ] Duplicate handling matches requirements (empty markers vs filter)
- [ ] External validation passed (if reference data provided)
- [ ] All input images processed (no silent skips)

## Anti-Patterns
- **Do not** rely on a single OCR preprocessing mode or PSM config
- **Do not** format prices with fixed decimal places at extraction time
- **Do not** manually read images and hardcode extracted data
- **Do not** filter out duplicates when task requires preserving row structure
- **Do not** write empty strings `''` for missing values when `None` is semantically correct
- **Do not** skip validation; OCR hallucinates, always cross-check a subset

## Reference Scripts
- `scripts/extract_order_data.py`: Full pipeline template for order/invoice extraction with reference validation.
- `references/patterns.md`: Ready-to-use regex collections for dates, prices, order IDs, and OCR cleanup.