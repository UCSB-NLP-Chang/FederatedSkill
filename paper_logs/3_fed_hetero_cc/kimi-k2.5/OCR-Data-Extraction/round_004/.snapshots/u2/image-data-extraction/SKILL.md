---
name: image-data-extraction
description: Extract structured data (dates, prices, codes, order IDs, totals) from image batches using OCR with multi-pass preprocessing, regex parsing, deduplication handling, and Excel output. Handles variable image quality, multiple document types (receipts, invoices, labels, claims), and batch processing requirements with reference/roster merging.
---

# Image Data Extraction

Extract structured data from image collections using Tesseract OCR with robust preprocessing, regex parsing, pattern matching, and reference data merging. Outputs normalized data to Excel/CSV.

## When to Use
- Processing batches of receipt/invoice/label/claim images
- Extracting dates, prices, codes, order IDs, claim references, or totals from visual documents
- Converting image-based tabular data to structured formats (Excel, CSV, JSON)
- Input contains variable image quality, multiple text orientations, or mixed formats
- Deduplication required: multiple images may contain the same logical record
- **Merging with reference data**: images contain codes that link to roster/master lists (employee IDs, trip IDs, etc.)

## Workflow
1. **Enumerate images** - Use glob patterns to discover all target images
2. **Load reference data** (if applicable) - Load CSV/JSON roster or master list for lookup/validation
3. **Configure OCR** - Use `pytesseract` with multiple fallback preprocessing strategies (see OCR Strategy)
4. **Define extraction patterns** - Create regex patterns for each field type with priority ordering
5. **Parse with fallbacks** - Try multiple patterns per field; log unmatched entries for review
6. **Merge with reference** - Link extracted codes to reference data (roster lookup)
7. **Handle unmatched records** - Leave fields empty/None when reference lookup fails
8. **Validate against reference** - If external validation data exists, check extracted values
9. **Handle duplicates** - Decide strategy: first-wins (mark subsequent empty), keep-all, or merge based on task requirements
10. **Output validation** - Verify output format, check for missing values, validate data types
11. **Export** - Write to required format (Excel, CSV, JSON). Sort by filename. Verify row count matches image count.
12. **Spot-check** - Print raw OCR output for 3-5 random images to confirm parsing.

## OCR Preprocessing Strategy
Always apply multiple preprocessing approaches in order of success probability:
```python
def extract_with_fallbacks(image_path):
    img = Image.open(image_path)
    # Strategy 1: Original
    text = pytesseract.image_to_string(img)
    # Strategy 2: Grayscale
    text = pytesseract.image_to_string(img.convert('L'))
    # Strategy 3: Contrast enhancement (binarization)
    img_gray = img.convert('L')
    text = pytesseract.image_to_string(img_gray.point(lambda x: 0 if x < 100 else 255, '1'))
    # Strategy 4: Inverted
    text = pytesseract.image_to_string(Image.eval(img_gray, lambda x: 255 - x))
    # Strategy 5: Page segmentation modes
    for psm in [6, 3, 4, 11]:
        text = pytesseract.image_to_string(img, config=f'--psm {psm}')
```
Stop when extracted text exceeds minimum length threshold (e.g., 10 chars).

## Date Disambiguation Logic
When extracting dates with ambiguous DD/MM vs MM/DD format:
```python
def normalize_date(g1, g2, year):
    num1, num2 = int(g1), int(g2)
    if num1 > 12: return f"{year}-{num2:02d}-{num1:02d}"  # DD/MM
    if num2 > 12: return f"{year}-{num1:02d}-{num2:02d}"  # MM/DD
    return f"{year}-{num2:02d}-{num1:02d}"  # Ambiguous -> prefer DD/MM
```

## Reference Data Merging (Roster Lookup)
When images contain codes that link to external data:
```python
import csv
roster = {}
with open('roster.csv', newline='') as f:
    for row in csv.DictReader(f):
        key = row['claim_code'].strip().upper()
        roster[key] = {'employee_id': row['employee_id'], 'trip_id': row['trip_id']}

# During extraction
if claim_code and claim_code.upper() in roster:
    employee_id = roster[claim_code.upper()]['employee_id']
    trip_id = roster[claim_code.upper()]['trip_id']
else:
    employee_id = None  # Empty cell in Excel
    trip_id = None
```
**Rule**: Leave as `None` when lookup fails—do not invent or default values.

## Deduplication Patterns
When multiple images may represent the same logical record:
- **Preserve All (Default)**: Each image is a separate row. Keep all rows with extracted data.
- **First-Wins (Mark Subsequent Empty)**: Keep first occurrence with full data. Subsequent images with same ID get row preserved but other fields set to `None`.
- **Filter Mode**: Only if task says "output unique records only".

```python
seen_ids = set()
results = []
for img_path in image_files:
    record = extract_from_image(img_path)
    if record and record['id'] not in seen_ids:
        seen_ids.add(record['id'])
        results.append({'filename': os.path.basename(img_path), 'id': record['id'], 'date': record['date'], 'amount': record['amount']})
    else:
        results.append({'filename': os.path.basename(img_path), 'id': None, 'date': None, 'amount': None})
```

## Total Amount Extraction with Keyword Priority
For invoice/receipt total extraction, use priority-based keyword matching with exclusions:
```python
TOTAL_KEYWORDS = ['GRAND TOTAL', 'TOTAL DUE', 'AMOUNT DUE', 'BALANCE DUE', 'TOTAL', 'AMOUNT']
EXCLUSION_KEYWORDS = ['SUBTOTAL', 'SUB TOTAL', 'TAX', 'GST', 'VAT', 'DISCOUNT', 'CHANGE', 'TENDERED']

def extract_total(text):
    lines = text.upper().split('\n')
    for keyword in TOTAL_KEYWORDS:
        for line in lines:
            if keyword in line:
                if any(ex in line for ex in EXCLUSION_KEYWORDS): continue
                match = re.search(r'[\$€£RM]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})', line)
                if match: return float(match.group(1).replace(',', ''))
    return None
```

## Output Precision
**Critical rule**: Pass numeric values in their natural type. Do not preemptively format.
- Excel: Use raw `float` or `int`. `None` writes as empty cell.
- CSV/JSON: Use number type or ISO string for dates.
- **Anti-pattern**: `round(x, 2)`, `format(x, ".2f")`, f-strings before writing to Excel.
- **Exception**: Task explicitly requires string formatting.
- Verifier tolerance decides precision; your job is full precision.

## Known invariants (by sub-task)
### pharmacy-shelf-label
- Columns: `filename`, `date`, `price` in exact order
- Row count = image count
- Dates: ISO YYYY-MM-DD, day `01` for month-only
- Prices: RM, MYR, $, EUR

### ecommerce-orders
- Columns: `filename`, `order_id`, `date`, `total_amount` in exact order
- Row count = image count
- Order IDs validated against reference if provided; invalid -> `None`
- Duplicates: first-wins, mark subsequent `None`
- Amounts: raw floats. Sort by filename.

### invoices / invoice-extraction
- Columns: `filename`, `date`, `total_amount` in exact order
- Row count = image count. Sheet name: `invoices` (if requested)
- Dates: DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD. Disambiguate using >12 rule.
- Total extraction: Priority `GRAND TOTAL` > `TOTAL DUE` > `AMOUNT DUE` > `TOTAL` > `AMOUNT`
- Exclude lines with: `SUBTOTAL`, `SUB TOTAL`, `TAX`, `GST`, `DISCOUNT`, `CHANGE`
- Amounts: raw floats. Sort by filename.

### travel-claims
- Columns: `filename`, `claim_code`, `employee_id`, `trip_id`, `date`, `total_amount` in exact order
- Roster merge on `claim_code`. Unmatched -> `None` for roster fields.
- Amount exclusions: ADVANCE, TIP, DEPOSIT
- Amounts: raw floats. Sort by filename.

## Validation Checklist
- [ ] Row count = image count
- [ ] Dates normalized to ISO YYYY-MM-DD
- [ ] Numeric fields are raw floats
- [ ] Duplicate handling matches requirements
- [ ] Roster/lookup merge applied (`None` for missing)
- [ ] All images processed
- [ ] Sorted by filename

## Anti-Patterns
- Do not rely on single OCR/PSM mode
- Do not format prices/amounts with fixed decimals
- Do not hardcode data; use OCR automation
- Do not filter duplicates unless explicitly requested
- Do not use `''` for missing values when `None` is correct
- Do not use `python` command; use `python3` explicitly
- Do not skip validation; OCR hallucinates
- Do not assume date format without disambiguation

## Script & Reference Files
- `scripts/extract_from_images.py`: Batch extraction template
- `scripts/extract_order_data.py`: Order/invoice with validation
- `scripts/extract_travel_claims.py`: Travel claims with roster merge
- `references/patterns.md`: Regex collections for dates, prices, IDs
- `references/invoice-patterns.md`: Complete invoice extraction patterns