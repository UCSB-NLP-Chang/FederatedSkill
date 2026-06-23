---
name: image-data-extraction
description: Extract structured data (dates, prices, order IDs, totals) from image batches using OCR with multi-pass preprocessing, regex parsing, deduplication handling, and Excel output. Handles variable image quality, multiple document types, and batch processing requirements.
---

# Image Data Extraction

Extract structured data from multiple images and write to a formatted Excel file. Handles variable image quality, multiple document types, and batch processing requirements.

## When to Use
- Processing shelf labels, receipts, invoices, orders, claims, or scanned documents
- Extracting consistent fields (dates, prices, IDs, totals) across multiple images
- Converting visual data to structured tabular formats
- Tasks requiring 1:1 image-to-row mapping, duplicate handling, or external validation
- Merging extracted data with reference/roster CSV files

## Workflow
1. **Enumerate images**: List all image files in the target directory.
2. **Load reference data** (if applicable): Load CSV/JSON roster for lookup/validation.
3. **Preprocess & OCR**: Apply multi-pass preprocessing strategies with fallback PSM configs.
4. **Parse & Normalize**:
   - Dates: Normalize to `YYYY-MM-DD`. Use day `01` for month-only dates. Apply disambiguation logic.
   - Prices/Totals: Extract raw floats, strip thousands separators. Do not format/round.
   - IDs/Codes: Match known patterns, validate against reference files if provided.
5. **Handle Duplicates & Reference Merge**: Track seen identifiers. Join extracted records on key field. Leave fields as `None` when no match found.
6. **Output**: Write Excel with header row and one row per image. Sort by filename.
7. **Validate**: Check row count matches image count, verify formatting, spot-check OCR output.

## OCR Preprocessing Strategy
Always apply multiple preprocessing approaches to handle variable image quality:
- **Grayscale**: `image.convert('L')`
- **High Contrast**: `ImageEnhance.Contrast(gray).enhance(2.0-2.5)`
- **Threshold/Binarization**: `gray.point(lambda x: 0 if x < threshold else 255)`
- **Upscale**: `image.resize((w*2, h*2), Image.LANCZOS)`
- **PSM Fallbacks**: Try `--psm 6` (block), `4` (column), `3` (auto), `1` (sparse text)
- Stop when extracted text exceeds minimum length threshold.

## Date Disambiguation Logic
When extracting dates with ambiguous DD/MM vs MM/DD format:
```python
def normalize_date(g1, g2, year):
    num1, num2 = int(g1), int(g2)
    if num1 > 12:
        return f"{year}-{num2:02d}-{num1:02d}"  # DD/MM/YYYY
    if num2 > 12:
        return f"{year}-{num1:02d}-{num2:02d}"  # MM/DD/YYYY
    return f"{year}-{num2:02d}-{num1:02d}"      # Ambiguous: prefer DD/MM
```

## Total Amount Extraction with Priority Keywords
When extracting totals from documents with multiple monetary values:
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

## Roster/Lookup Merge Pattern
When enriching extracted data with a reference CSV:
```python
import csv
roster = {}
with open(reference_file, 'r') as f:
    for row in csv.DictReader(f):
        roster[row['key_field'].strip().upper()] = row
# During extraction:
# if key in roster: record.update(roster[key])
# else: record['field1'] = None
```

## Deduplication Strategy
- **Default (1:1 Row Mapping)**: First-wins with empty markers. Write first occurrence with full data. Subsequent images with same ID get a row with `filename` populated, other fields `None`.
- **Filter Mode**: Only if task explicitly says "output unique records only".
- Track seen IDs in a `set()`. Normalize IDs before comparison.

## Output precision
Never round, truncate, or fixed-format numeric values. Pass raw floats directly.
- DO NOT: `round(x, N)`, `format(x, ".2f")`
- DO: `ws.cell(row=r, column=c, value=x)`
- `openpyxl` treats `None` as an empty cell. Use `None` for missing/invalid lookups.

## Known invariants (by sub-task)

### pharmacy-shelf-label
- Output columns: `{filename, date, price}`
- Date priority: `EXP`/`EXPIRY` > `EXPIRES` > `MFG`/`MANUFACTURED`
- Price priority: labeled `PRICE:` > raw currency (`RM`, `MYR`, `$`)

### ecommerce-orders
- Output columns: `{filename, order_id, date, total_amount}`
- Order ID patterns: `ORD-YYYY-NNNNN`, `SO-YYYY-NNN`, `INV-YYYYMMDD`
- Validate IDs against reference if provided; set to `None` if invalid.

### invoice-processing
- Output columns: `{filename, date, total_amount}`
- Total extraction: Priority keywords with exclusion filtering.
- Dates: Handle DD/MM/YYYY, MM/DD/YYYY (disambiguate), YYYY-MM-DD.
- Sheet name: `invoices` (if specified).

### travel-claims
- Output columns: `{filename, claim_code, employee_id, trip_id, date, total_amount}`
- Claim code patterns: `CLM-YYYY-NNN`
- Roster merge: Join on `claim_code`. Leave lookup fields as `None` if unmatched.

## Validation Checklist
- [ ] Row count = number of images processed
- [ ] Dates normalized to ISO `YYYY-MM-DD`
- [ ] Numeric fields are raw floats
- [ ] Duplicate handling matches requirements
- [ ] Roster merge applied correctly (`None` for missing)
- [ ] All input images processed (no silent skips)

## Anti-Patterns
- **Do not** rely on a single OCR mode/PSM config.
- **Do not** format prices with fixed decimals at extraction time.
- **Do not** manually read/hardcode image data.
- **Do not** filter duplicates when 1:1 mapping is required.
- **Do not** write `''` for missing values when `None` is correct.
- **Do not** skip validation; OCR hallucinates.
- **Do not** assume date format without disambiguation logic.
- **Do not** extract first monetary value as total; use keyword priority.
- **Do not** use `python` command; use `python3`.

## Reference Scripts & Files
- `scripts/extract_order_data.py`: Full pipeline template.
- `references/patterns.md`: Ready-to-use regex collections.
- `references/invoice-patterns.md`: Complete invoice extraction patterns & multi-line handling.