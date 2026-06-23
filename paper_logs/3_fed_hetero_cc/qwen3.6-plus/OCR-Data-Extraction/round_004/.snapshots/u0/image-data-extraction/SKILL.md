---
name: image-data-extraction
description: Extract structured data (dates, prices, order IDs, totals) from images using Tesseract OCR with robust multi-pass preprocessing, regex parsing, and Excel output. Use when tasks require reading text from product labels, receipts, invoices, orders, travel claims, or scanned documents with varying formats and image quality, especially when merging with reference/roster CSVs.
---

# Image OCR Data Extraction

## Overview
Extract structured fields from images using `pytesseract`. This workflow handles inconsistent image quality, varied formats, and outputs normalized data to Excel/CSV. It supports label/receipt extraction, order/invoice processing, and roster/reference merging.

## Workflow
1. **Enumerate & Inspect**: List all image files in the target directory. Note format variations and fields to extract.
2. **Run Multi-Pass OCR**: Apply multiple preprocessing modes and PSM configs. Aggregate extracted text or stop when length exceeds a minimum threshold.
3. **Parse & Normalize**:
   - **Dates**: Match various formats, normalize to `YYYY-MM-DD`. Use day `01` for month-only. Prioritize expiry over manufacture. Apply disambiguation logic for `DD/MM` vs `MM/DD`.
   - **Prices/Totals**: Match currency symbols or keywords. Strip non-numeric chars except `.`. Extract using keyword priority for invoices.
   - **IDs/Codes**: Match patterns like `CLM-YYYY-NNN`, `INV-YYYYNNNN`, `ORD-YYYY-NNNNN`.
4. **Reference/Roster Merging**: Load reference CSV into a dictionary keyed by extracted ID/code. Lookup matching fields. Leave unmatched fields as `None`.
5. **Handle Duplicates & Validation**: Track seen identifiers. Apply first-wins or keep-all strategy based on task. Validate against reference if provided.
6. **Output**: Write to Excel with appropriate columns. Sort by filename. Verify row count matches image count.
7. **Spot-check**: Print raw OCR output for 3-5 random images to confirm parsing.

## OCR Preprocessing Strategy
Always apply multiple preprocessing approaches to handle variable image quality:
```python
import pytesseract
from PIL import Image, ImageEnhance

def extract_with_fallbacks(image_path):
    img = Image.open(image_path)
    # Strategy 1: Original
    text = pytesseract.image_to_string(img)
    if len(text.strip()) > 10: return text
    # Strategy 2: Grayscale
    text = pytesseract.image_to_string(img.convert('L'))
    if len(text.strip()) > 10: return text
    # Strategy 3: High Contrast / Binarization
    gray = img.convert('L')
    text = pytesseract.image_to_string(gray.point(lambda x: 0 if x < 100 else 255, '1'))
    if len(text.strip()) > 10: return text
    # Strategy 4: PSM Fallbacks
    for psm in [6, 3, 4, 11]:
        text = pytesseract.image_to_string(img, config=f'--psm {psm}')
        if len(text.strip()) > 10: return text
    return text
```

## Date Disambiguation Logic
When regex captures two numeric components and a year, determine format:
```python
def normalize_date(g1, g2, year):
    num1, num2 = int(g1), int(g2)
    if num1 > 12:
        return f"{year}-{num2:02d}-{num1:02d}"  # DD/MM/YYYY
    elif num2 > 12:
        return f"{year}-{num1:02d}-{num2:02d}"  # MM/DD/YYYY
    else:
        return f"{year}-{num2:02d}-{num1:02d}"  # Default DD/MM/YYYY
```

## Total Amount Extraction with Keyword Priority
For documents with multiple monetary values (invoices, receipts):
```python
TOTAL_KEYWORDS = ["GRAND TOTAL", "TOTAL DUE", "AMOUNT DUE", "TOTAL", "AMOUNT"]
EXCLUSION_KEYWORDS = ["SUBTOTAL", "SUB TOTAL", "TAX", "GST", "DISCOUNT", "CHANGE"]

def extract_total(text):
    lines = text.upper().split('\n')
    for keyword in TOTAL_KEYWORDS:
        for line in lines:
            if any(excl in line for excl in EXCLUSION_KEYWORDS):
                continue
            if keyword in line:
                match = re.search(r'\$?\s*([\d,]+\.\d{2})', line)
                if match:
                    return float(match.group(1).replace(',', ''))
    return None
```

## Reference Data Merging (Roster Lookup)
```python
import csv
roster = {}
with open(reference_file, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        roster[row['key_field'].strip().upper()] = row

# During extraction:
record = {'filename': fname, 'extracted_key': value}
if record['extracted_key'] in roster:
    record.update(roster[record['extracted_key']])
else:
    record['field1'] = None  # openpyxl renders None as empty cell
```

## Deduplication Strategy
- **Default (1:1 Row Mapping)**: Keep first occurrence with full data. For subsequent images with the same ID, write a row with `filename` populated but `None` for other fields.
- **Filter Mode**: Only use if task explicitly says "output unique records only".
- Track seen IDs in a `set()` during iteration. Normalize IDs before comparison.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Anti-Patterns
- **Do not manually read images and hardcode data.** Always use OCR automation.
- **Do not rely on a single Tesseract `--psm` mode.** Layouts vary; combine multiple.
- **Do not hardcode date/price parsing for one format.** Use regex with fallbacks.
- **Do not skip validation.** OCR hallucinates; cross-check raw outputs.
- **Do not format prices with fixed decimal places.** Pass raw floats.
- **Do not deduplicate rows unless explicitly requested.** Each image represents a physical record.
- **Do not panic over `None` in openpyxl readbacks.** `None` is standard for empty cells.
- **Do not use `python` command.** Use `python3` explicitly; `python` is often unavailable.
- **Do not assume date format without disambiguation logic.** Check if either component > 12.
- **Do not skip rows when roster lookup fails.** Write row with `None` for missing fields.

## Script Usage
- Run `scripts/extract_ocr_data.py` for product labels (columns: `filename`, `date`, `price`).
- Run `scripts/extract_order_data.py` for orders/invoices (columns: `filename`, `order_id`, `date`, `total_amount`). Supports reference file validation and multi-pass OCR.
- For invoice-only extraction (columns: `filename`, `date`, `total_amount`), adapt `extract_order_data.py` by removing `order_id` column and using keyword-priority total extraction (see `references/patterns.md` or `references/invoice-patterns.md`).
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

### invoice-extraction
- Output Excel must have exactly 3 columns: `filename`, `date`, `total_amount`
- Row count must equal input image count
- Sheet name: `invoices`
- Dates normalized to ISO YYYY-MM-DD (handle DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD)
- **Date disambiguation**: When parsing `A/B/YYYY`, try DD/MM first. If month > 12, fall back to MM/DD. If both valid, prefer DD/MM.
- Total amounts extracted using keyword priority: `GRAND TOTAL` > `TOTAL DUE` > `AMOUNT DUE` > `TOTAL` > `AMOUNT`
- Exclude lines containing `SUBTOTAL`, `SUB TOTAL`, `TAX`, `GST`, `DISCOUNT`, `CHANGE` when extracting totals
- Total amounts as raw floats (no fixed formatting)
- Sort rows by `filename` ascending

### travel-claims
- Output Excel must have exactly 6 columns: `filename`, `claim_code`, `employee_id`, `trip_id`, `date`, `total_amount`
- Row count must equal input image count
- Sort rows by `filename` ascending
- Dates normalized to ISO YYYY-MM-DD (handle DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD)
- Match `claim_code` against roster/reference CSV to populate `employee_id` and `trip_id`
- Unmatched claims: keep `claim_code`, `date`, `total_amount`; set `employee_id` and `trip_id` to `None` (empty cell)
- Total amounts as raw floats

## Validation Checklist
- [ ] Row count = number of images processed
- [ ] No empty rows between data
- [ ] Dates normalized to ISO `YYYY-MM-DD`
- [ ] Numeric fields are raw floats, not formatted strings
- [ ] Duplicate handling matches requirements (empty markers vs filter)
- [ ] Roster/lookup merge applied correctly (None for missing matches)
- [ ] External validation passed (if reference data provided)
- [ ] All input images processed (no silent skips)

## Reference Files
- `references/patterns.md`: Ready-to-use regex patterns for dates, prices, order IDs, codes, and OCR cleanup.
- `references/invoice-patterns.md`: Complete invoice extraction patterns, multi-line total handling, and currency formatting.