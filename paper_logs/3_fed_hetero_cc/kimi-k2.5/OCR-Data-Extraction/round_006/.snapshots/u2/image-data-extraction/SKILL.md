---
name: image-data-extraction
description: Extract structured data (dates, prices, codes, order IDs, totals, tabular line items) from image batches using OCR with multi-pass preprocessing, regex parsing, deduplication handling, and Excel output. Handles variable image quality, multiple document types (receipts, invoices, labels, claims, utility bills, measurement forms with tables), and batch processing requirements with reference/roster merging.
---

# Image Data Extraction

Extract structured data from image collections using Tesseract OCR with robust preprocessing, regex parsing, pattern matching, and reference data merging. Outputs normalized data to Excel/CSV.

## When to Use
- Processing batches of receipt/invoice/label/claim/bill images
- Extracting dates, prices, codes, order IDs, claim references, or totals from visual documents
- **Processing forms with repeating line items** (measurement forms, itemized bills, BOMs) - see [Tabular Form Patterns](references/tabular-form-patterns.md)
- Converting image-based tabular data to structured formats (Excel, CSV, JSON)
- Input contains variable image quality, multiple text orientations, or mixed formats
- Deduplication required: multiple images may contain the same logical record
- **Merging with reference data**: images contain codes that link to roster/master lists (employee IDs, trip IDs, etc.)
- **Template workbook filling**: updating existing Excel templates while preserving sheets/headers
- **Multi-sheet output needed**: detail + summary views, aggregated by project/code

## Workflow
1. **Enumerate images** - Use glob patterns to discover all target images
2. **Load reference data** (if applicable) - Load CSV/JSON roster or master list for lookup/validation
3. **Configure OCR** - Use `pytesseract` with multiple fallback preprocessing strategies (see OCR Strategy)
4. **Define extraction patterns** - Create regex patterns for each field type with priority ordering
5. **Parse with fallbacks** - Try multiple patterns per field; log unmatched entries for review
6. **Handle multi-line patterns** - For labels split across lines (e.g., "TOTAL\n\nDUE"), use line window search
7. **Extract tabular items** (if applicable) - For forms with line items, use [line-by-line parsing](references/tabular-form-patterns.md) with quantity/price disambiguation
8. **Merge with reference** - Link extracted codes to reference data (roster lookup)
9. **Handle unmatched records** - Leave fields empty/None when reference lookup fails
10. **Validate against reference** - If external validation data exists, check extracted values
11. **Handle duplicates** - Decide strategy: first-wins (mark subsequent empty), keep-all, or merge based on task requirements
12. **Preserve template structure** (if applicable) - Keep original sheets, headers, cover pages unchanged
13. **Generate summary sheet** (if applicable) - Aggregate by project/code: latest date, total/latest amount
14. **Output validation** - Verify output format, check for missing values, validate data types
15. **Export** - Write to required format (Excel, CSV, JSON). Sort by filename. Verify row count matches image count or item count.
16. **Spot-check** - Print raw OCR output for 3-5 random images to confirm parsing.

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

## Multi-Line Keyword Handling
For labels split across lines or with blank lines between:
```python
def extract_with_window(lines, keyword, window=3):
    """Search for keyword in line, look for value in next N non-empty lines."""
    for i, line in enumerate(lines):
        if keyword.lower() in line.lower():
            # Skip distractors
            if should_exclude(line): continue
            # Check same line first
            match = re.search(r'[\$]?\s*([\d,]+\.\d{2})', line)
            if match: return match.group(1)
            # Check subsequent lines (skipping empty ones)
            for j in range(i+1, min(len(lines), i+window)):
                next_line = lines[j].strip()
                if not next_line: continue
                match = re.search(r'[\$]?\s*([\d,]+\.\d{2})', next_line)
                if match: return match.group(1)
    return None
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

## Tabular/Line Item Extraction
For forms with repeating line items (measurement forms, itemized documents):
- See [`references/tabular-form-patterns.md`](references/tabular-form-patterns.md) for detailed patterns
- Key challenge: Disambiguating quantity vs price vs item code numbers
- Use priority-ordered pattern matching for item types
- Validate: quantity as integer in 1-9999 range, price with 2 decimals
- Output: One row per line item (not per image)

## Multi-Sheet Output Pattern
For detail + summary requirements:
```python
# Sheet 1: Details - one row per extracted item
for item in all_items:
    ws_details.append([filename, project, item_desc, qty, price])

# Sheet 2: Summary - aggregated per project
from collections import defaultdict
projects = defaultdict(lambda: {'dates': [], 'totals': []})
# ... populate from extraction ...
for code in sorted(projects.keys()):
    latest = max(projects[code]['dates'])
    total = projects[code]['totals'][-1]  # or sum()
    ws_summary.append([code, latest, total])
```

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
For invoice/receipt/bill total extraction, use priority-based keyword matching with exclusions:
```python
TOTAL_KEYWORDS = ['GRAND TOTAL', 'TOTAL DUE', 'AMOUNT DUE', 'BALANCE DUE', 'PAY THIS AMOUNT', 'CURRENT CHARGES', 'TOTAL', 'AMOUNT']
EXCLUSION_KEYWORDS = ['SUBTOTAL', 'SUB TOTAL', 'TAX', 'GST', 'VAT', 'DISCOUNT', 'CHANGE', 'TENDERED', 'PREVIOUS BALANCE', 'LATE FEE', 'CREDIT']

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

## Template Workbook Preservation
When updating an existing Excel template:
1. Load template with `openpyxl.load_workbook()`
2. Identify target sheet by name (don't assume index)
3. Preserve all non-target sheets unchanged
4. Keep header row from template (don't overwrite)
5. Start data insertion at row 2 (after headers)
6. Match column order from template headers
7. Save to new filename, keeping original template intact

```python
from openpyxl import load_workbook

wb = load_workbook('template.xlsx')
ws = wb['bills']  # Access by name, not index
# Keep cover sheet unchanged
cover = wb['cover']
# Update data sheet, preserving headers
for row_idx, record in enumerate(records, start=2):
    ws.cell(row=row_idx, column=1, value=record['scan_name'])
    ws.cell(row=row_idx, column=2, value=record['bill_date'])
    ws.cell(row=row_idx, column=3, value=record['amount_due'])
wb.save('output.xlsx')
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

### utility-bills
- Columns: `scan_name`, `bill_date`, `amount_due` (match template exactly)
- Preserve template sheets: `cover` (unchanged), `bills` (update data)
- Row count = image count
- Dates: multiple formats (DD/MM/YYYY, DD-MM-YYYY, MM/DD/YYYY, YYYY-MM-DD)
- Amount keywords: `PAY THIS AMOUNT`, `CURRENT CHARGES`, `TOTAL DUE`, `AMOUNT DUE`
- Amount exclusions: `PREVIOUS BALANCE`, `LATE FEE`, `TAX`, `CREDIT`
- Handle multi-line keywords (e.g., "TOTAL\n\nDUE")
- Sort by filename ascending

### construction-measurement-forms
- Columns (details): `filename`, `project_code`, `item_description`, `quantity`, `unit_price`
- Columns (summary): `project_code`, `date`, `total_amount`
- Multiple items per image → multiple detail rows per image
- Row count (details) = images × items per form
- Quantity: integer, price: float with 2 decimals
- Summary: latest date per project, totals from latest measurement
- See [tabular-form-patterns.md](references/tabular-form-patterns.md)

## Validation Checklist
- [ ] Row count matches expected (images or images × items)
- [ ] Dates normalized to ISO YYYY-MM-DD
- [ ] Numeric fields are raw floats (unless string format explicitly required)
- [ ] Duplicate handling matches requirements
- [ ] Roster/lookup merge applied (`None` for missing)
- [ ] All images processed
- [ ] Sorted by filename
- [ ] Template sheets preserved (if applicable)
- [ ] Headers unchanged from template (if applicable)
- [ ] Summary aggregates correctly (latest date, proper total calculation)

## Anti-Patterns
- Do not rely on single OCR/PSM mode
- Do not format prices/amounts with fixed decimals (unless task requires)
- Do not hardcode data; use OCR automation
- Do not filter duplicates unless explicitly requested
- Do not use `''` for missing values when `None` is correct
- Do not use `python` command; use `python3` explicitly
- Do not skip validation; OCR hallucinates
- Do not assume date format without disambiguation
- Do not overwrite template headers with custom ones
- Do not assume sheet index; access by name for template workbooks
- Do not mistake item codes for quantities (e.g., "C30" vs "50" qty)
- Do not output formatted strings to Excel cells; use raw numbers

## Script & Reference Files
- `scripts/extract_from_images.py`: Batch extraction template
- `scripts/extract_order_data.py`: Order/invoice with validation
- `scripts/extract_travel_claims.py`: Travel claims with roster merge
- `references/patterns.md`: Regex collections for dates, prices, IDs
- `references/invoice-patterns.md`: Complete invoice extraction patterns
- `references/utility-bill-patterns.md`: Utility bill specific keywords and patterns
- `references/tabular-form-patterns.md`: Line-item extraction from forms/tables, quantity/price disambiguation, multi-sheet output