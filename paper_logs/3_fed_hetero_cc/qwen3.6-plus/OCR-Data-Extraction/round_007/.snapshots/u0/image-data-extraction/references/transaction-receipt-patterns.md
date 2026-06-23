# Transaction/Fuel Receipt Extraction Patterns

Patterns for extracting data from fuel/transaction receipts in nested directory structures with document type filtering.

## Trigger Conditions
- Images organized in nested directories (e.g., `batch_north/day1/`, `batch_south/day2/`)
- Mixed document types requiring filtering (receipts vs cover sheets, promos, notes, loyalty forms)
- Output requires `batch_name`, `relative_path`, `txn_ref`, `date`, `total_amount` columns

## Document Type Filtering

### Receipt Indicators (process these)
```python
RECEIPT_INDICATORS = [
    'FUEL RECEIPT',
    'PUMP SALE',
    'TAX INVOICE',
    'TXN REF',
    'TRANSACTION NO',
    'REF NO',
]

def is_receipt(text):
    upper = text.upper()
    return any(ind in upper for ind in RECEIPT_INDICATORS)
```

### Non-Receipt Indicators (skip these)
```python
NON_RECEIPT_INDICATORS = [
    'COVER SHEET',
    'PROMOTION FLYER',
    'ROUTE NOTE',
    'LOYALTY FORM',
    'MEMBER REF',
    'TOTAL SAVINGS',  # Often appears on non-receipt docs
]

def is_non_receipt(text):
    upper = text.upper()
    return any(ind in upper for ind in NON_RECEIPT_INDICATORS)
```

### Filtering Logic
```python
def should_process(text):
    """Return True if document is a receipt, False otherwise."""
    if is_non_receipt(text):
        return False
    return is_receipt(text)
```

## Nested Directory Traversal

```python
import os

def enumerate_images(dataset_root):
    """Walk nested directories and return (full_path, relative_path, batch_name) tuples."""
    results = []
    for root, dirs, files in os.walk(dataset_root):
        for f in sorted(files):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, dataset_root)
                # batch_name is first directory component
                batch_name = rel_path.split(os.sep)[0]
                results.append((full_path, rel_path, batch_name))
    return results
```

## Transaction Reference Extraction

```python
import re

TXN_REF_PATTERNS = [
    r'TXN\s*REF[:\s]+([A-Z0-9-]+)',
    r'TRANSACTION\s*NO[:\s]+([A-Z0-9-]+)',
    r'REF\s*NO[:\s]+([A-Z0-9-]+)',
    r'(FUEL-[A-Z]-[A-Z0-9]+)',  # e.g., FUEL-N-002, FUEL-S-OO1
]

def extract_txn_ref(text):
    for pattern in TXN_REF_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None
```

## Multi-Line Amount Extraction (Blank-Line Safe)

Fuel receipts often have blank lines between keyword and amount:
```
TOTAL AMOUNT

78.10
```

```python
def extract_amount_safe(text):
    """Extract amount, skipping blank lines between keyword and value."""
    lines = [l.strip() for l in text.split('\n')]
    TOTAL_KEYWORDS = ['TOTAL AMOUNT', 'GRAND TOTAL', 'TOTAL DUE', 'AMOUNT DUE', 'AMOUNT PAID']
    EXCLUSIONS = ['SUBTOTAL', 'TAX', 'DISCOUNT', 'SAVINGS']

    for i, line in enumerate(lines):
        upper = line.upper()
        if any(excl in upper for excl in EXCLUSIONS):
            continue
        for kw in TOTAL_KEYWORDS:
            if kw in upper:
                # Look at subsequent non-blank lines
                for j in range(i + 1, len(lines)):
                    next_line = lines[j].strip()
                    if not next_line:
                        continue  # # SKIP BLANK LINES
                    next_upper = next_line.upper()
                    if any(excl in next_upper for excl in EXCLUSIONS):
                        break
                    match = re.search(r'[\$€£]?\s*([\d,]+\.\d{2})', next_line)
                    if match:
                        return float(match.group(1).replace(',', ''))
                    break  # Found non-blank line without amount
    return None
```

## Date Extraction

```python
def extract_date(text):
    """Extract and normalize date from receipt text."""
    # YYYY-MM-DD (unambiguous)
    match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', text)
    if match:
        y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return f"{y:04d}-{m:02d}-{d:02d}"

    # DD/MM/YYYY or MM/DD/YYYY
    match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', text)
    if match:
        a, b, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if a > 12:
            return f"{year}-{b:02d}-{a:02d}"  # DD/MM
        elif b > 12:
            return f"{year}-{a:02d}-{b:02d}"  # MM/DD
        else:
            return f"{year}-{b:02d}-{a:02d}"  # Default DD/MM
    return None
```

## Complete Extraction Workflow

```python
import os
import re
import pytesseract
from PIL import Image
from openpyxl import Workbook

def process_fuel_receipts(dataset_root, output_path):
    images = enumerate_images(dataset_root)

    wb = Workbook()
    ws = wb.active
    ws.title = 'transactions'
    ws.append(['batch_name', 'relative_path', 'txn_ref', 'date', 'total_amount'])

    rows = []
    for full_path, rel_path, batch_name in images:
        text = pytesseract.image_to_string(Image.open(full_path))

        if not should_process(text):
            continue

        txn_ref = extract_txn_ref(text)
        date = extract_date(text)
        amount = extract_amount_safe(text)

        rows.append([batch_name, rel_path, txn_ref, date, amount])

    # Sort by relative_path
    rows.sort(key=lambda x: x[1])

    for row in rows:
        ws.append(row)

    wb.save(output_path)
    return rows
```

## Validation Rules

1. **Row count**: Must equal number of receipt images (non-receipts excluded)
2. **Column order**: `batch_name`, `relative_path`, `txn_ref`, `date`, `total_amount`
3. **Sort order**: Rows sorted by `relative_path` ascending
4. **Date format**: All dates in `YYYY-MM-DD`
5. **Amount precision**: Raw floats, no formatting
6. **Document filtering**: Cover sheets, promos, route notes, loyalty forms excluded
7. **Multi-line amounts**: Blank lines between keyword and value handled correctly