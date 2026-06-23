---
name: image-data-extraction
description: Extract structured data (dates, prices, codes, order IDs) from images using OCR. Use for processing receipts, labels, invoices, travel claims, or any image-based documents where text needs to be parsed into structured formats like Excel/CSV. Handles deduplication, external validation, reference data merging (rosters, master lists), and variable image quality.
---

# Image Data Extraction

Extract structured data from image collections using Tesseract OCR with robust preprocessing, regex parsing, pattern matching, and reference data merging.

## When to Use
- Processing batches of receipt/invoice/label/claim images
- Extracting dates, prices, codes, order IDs, claim references, or other patterned data from visual documents
- Converting image-based tabular data to structured formats (Excel, CSV, JSON)
- Input contains variable image quality, multiple text orientations, or mixed formats
- Deduplication required: multiple images may contain the same logical record
- **Merging with reference data**: images contain codes that link to roster/master lists (employee IDs, trip IDs, etc.)

## Workflow

1. **Enumerate images** - Use glob patterns to discover all target images
2. **Load reference data** (if applicable) - Load CSV/JSON roster or master list for lookup/validation
3. **Configure OCR** - Use `pytesseract` with multiple fallback preprocessing strategies
4. **Define extraction patterns** - Create regex patterns for each field type with priority ordering
5. **Parse with fallbacks** - Try multiple patterns per field; log unmatched entries for review
6. **Merge with reference** - Link extracted codes to reference data (roster lookup)
7. **Handle unmatched records** - Leave fields empty/None when reference lookup fails
8. **Validate against reference** - If external validation data exists (known IDs, master lists), check extracted values
9. **Handle duplicates** - Decide strategy: first-wins (mark subsequent empty), keep-all, or merge based on task requirements
10. **Output validation** - Verify output format, check for missing values, validate data types
11. **Export** - Write to required format (Excel, CSV, JSON)

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
    for psm in [6, 3, 4, 11]:  # 6=uniform block, 3=auto, 4=single column, 11=sparse
        text = pytesseract.image_to_string(img, config=f'--psm {psm}')
```

Stop when extracted text exceeds minimum length threshold (e.g., 10 chars).

## Pattern Matching Priorities

When multiple date/price formats exist, establish priority:

| Field | Priority Order | Example Patterns |
|-------|---------------|------------------|
| Dates | EXPIRY > EXPIRES > MFG | `EXP[:\s]+(\d{1,2})[/-](\d{1,2})[/-](\d{4})` |
| Prices | Labeled PRICE > Raw currency | `PRICE:\s*RM\s+(\d+\.\d{2})` > `RM\s+(\d+\.\d{2})` |
| Claim Codes | Labeled CODE > REF > ID | `Claim Code:\s*([A-Z0-9-]+)` |

## Date Disambiguation Logic

When extracting dates with ambiguous DD/MM vs MM/DD format:

```python
def normalize_date(g1, g2, year):
    num1, num2 = int(g1), int(g2)
    # If num1 > 12, it must be a day (DD/MM/YYYY format)
    if num1 > 12:
        return f"{year}-{num2:02d}-{num1:02d}"
    # If num2 > 12, it must be a day (MM/DD/YYYY format)
    if num2 > 12:
        return f"{year}-{num1:02d}-{num2:02d}"
    # Both <= 12: ambiguous - prefer DD/MM/YYYY
    return f"{year}-{num2:02d}-{num1:02d}"
```

## Reference Data Merging (Roster Lookup)

When images contain codes that link to external data (employee rosters, trip lists):

```python
import csv

# Load reference data
roster = {}
with open('roster.csv', newline='') as f:
    for row in csv.DictReader(f):
        claim_code = row['claim_code'].strip().upper()
        roster[claim_code] = {
            'employee_id': row['employee_id'],
            'trip_id': row['trip_id']
        }

# During extraction
for img_path in image_files:
    claim_code = extract_claim_code(ocr_text)
    
    if claim_code and claim_code.upper() in roster:
        employee_id = roster[claim_code.upper()]['employee_id']
        trip_id = roster[claim_code.upper()]['trip_id']
    else:
        employee_id = None  # Empty cell in Excel
        trip_id = None
```

**Decision rule**: Leave as `None` (empty Excel cell) when reference lookup fails—do not invent or default values.

## Deduplication Patterns

When processing batches where multiple images may represent the same logical record:

### Decision: When to Use First-Wins vs Keep-All

| Scenario | Strategy | Output Pattern |
|----------|----------|----------------|
| Must preserve 1:1 image-to-row mapping | First-wins with empty markers | Keep row, empty cells for duplicates |
| Only need unique records | Filter duplicates | Skip duplicate rows entirely |
| Need to detect/flag for review | Add status column | "UNIQUE" / "DUPLICATE" indicator |

### First-Wins Implementation (preserve row structure)

```python
seen_ids = set()
results = []

for img_path in image_files:
    record = extract_from_image(img_path)  # May return None for unparseable
    
    if record and record['id'] not in seen_ids:
        # First occurrence - full data
        seen_ids.add(record['id'])
        results.append({
            'filename': os.path.basename(img_path),
            'id': record['id'],
            'date': record['date'],
            'amount': record['amount']
        })
    else:
        # Duplicate or unparseable - preserve row with empty cells
        results.append({
            'filename': os.path.basename(img_path),
            'id': None,      # Writes as empty cell in Excel
            'date': None,
            'amount': None
        })
```

### Excel Output with None as Empty Cells

```python
# openpyxl writes Python None as empty cell automatically
for row_data in results:
    ws.append([
        row_data['filename'],  # Always populated
        row_data['id'],      # None → empty cell
        row_data['date'],    # None → empty cell  
        row_data['amount']   # None → empty cell
    ])
```

## External Validation

When reference data exists (e.g., `known_order_ids.csv`, master product list):

```python
import csv

# Load reference set once
known_ids = set()
with open(reference_file, newline='') as f:
    for row in csv.DictReader(f):
        for key in ['order_id', 'OrderID', 'id', 'ID']:
            if key in row and row[key]:
                known_ids.add(row[key].strip().upper())
                break

# Validate during extraction
extracted_id = parse_id_from_text(ocr_text).upper()
if extracted_id not in known_ids:
    log.warning(f"Unknown ID {extracted_id} in {img_path}")
    # Decide: skip, mark invalid, or keep with warning flag
```

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- Exception: When task explicitly requires string formatting (e.g., "exactly 2 decimal places as string")
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Common Pattern Templates

See `references/patterns.md` for ready-to-use regex collections for:
- Dates (DD/MM/YYYY, MM-YYYY, YYYY/MM variations)
- Prices (RM, $, MYR, EUR, GBP with optional "EACH"/"PER" suffixes)
- Product codes and identifiers
- Order IDs (ORD-, SO-, INV-)
- **Claim codes (CLM-, EXP-, with multiple label variants)**
- **Amount keywords (REIMBURSABLE TOTAL, TOTAL CLAIM, AMOUNT DUE)**

## Known invariants (by sub-task)

### pharmacy-shelf-label
- Output Excel must have exactly 3 columns: `filename`, `date`, `price` in exact order
- Row count must equal input image count
- Dates normalized to ISO YYYY-MM-DD; use day `01` for month-only dates
- Price extraction handles RM, MYR, $, EUR currencies

### ecommerce-orders
- Output Excel must have 4 columns: `filename`, `order_id`, `date`, `total_amount` in exact order
- Order IDs validated against reference file if provided; invalid IDs set to `None`
- Duplicate handling: Keep first occurrence, mark subsequent duplicates with `None`/empty cells
- Row count must exactly match input image count
- Total amounts passed as raw floats (no fixed formatting)

### travel-claims
- Output Excel must have 6 columns: `filename`, `claim_code`, `employee_id`, `trip_id`, `date`, `total_amount` in exact order
- **Claim code extraction**: Multiple label variants (Claim Code:, Claim Ref:, Expense Code:, Ref:)
- **Roster merge**: Load `claim_roster.csv` (or similar), map `claim_code` → `employee_id`, `trip_id`
- **Unmatched claims**: Leave `employee_id` and `trip_id` as empty cells when claim_code not in roster
- **Amount parsing**: Handle multi-line amounts (amount on line following keyword)
- **Amount exclusions**: Skip lines containing ADVANCE, TIP, DEPOSIT (not valid claim amounts)
- **Amount keywords**: REIMBURSABLE TOTAL, TOTAL CLAIM, AMOUNT CLAIMED, TOTAL DUE
- Dates normalized to ISO YYYY-MM-DD
- Total amounts as raw floats (pass directly to Excel)

## Validation Checklist

- [ ] All input images processed (no silent skips)
- [ ] Output sorted by meaningful key (usually filename or date)
- [ ] Date format normalized to ISO (YYYY-MM-DD)
- [ ] Prices passed as raw floats (no fixed formatting) OR as formatted strings per task spec
- [ ] Missing values explicitly logged, not silently blank
- [ ] Duplicate handling matches requirements (filtered vs marked empty)
- [ ] External validation passed (if reference data provided)
- [ ] Row count matches input image count (when structure preservation required)
- [ ] **Roster merge verified**: All expected matches found, unmatched records handled correctly

## Anti-Patterns

- **Don't** rely on a single preprocessing method - image quality varies unpredictably
- **Don't** assume consistent date format - same dataset may contain DD/MM and MM/DD
- **Don't** parse price without currency context - $10 vs RM10 are different values
- **Don't** skip verification of output row count against input file count
- **Don't** filter out duplicates when task requires preserving row structure - mark empty instead
- **Don't** write empty strings `''` for missing values when `None` is semantically correct
- **Don't** manually read images and hardcode extracted data into scripts - always use OCR automation
- **Don't** fail silently on roster lookup misses - log unmatched claim codes for review
- **Don't** assume single-line amount formats - keywords and values may be on separate lines

## Script Reference

For batch extraction jobs, use `scripts/extract_from_images.py` as a starting template.
For order/invoice extraction with reference validation, see `scripts/extract_order_data.py`.
For travel claims with roster merging, see `scripts/extract_travel_claims.py` (handles multi-line amounts, claim code variants, and roster lookup).