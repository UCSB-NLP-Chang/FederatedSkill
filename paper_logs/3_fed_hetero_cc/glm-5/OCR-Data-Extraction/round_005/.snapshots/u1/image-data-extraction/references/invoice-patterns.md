# Invoice Extraction Patterns

Complete patterns for extracting data from invoice/receipt images.

## Column Requirements

Standard invoice output format:
| Column | Type | Notes |
|--------|------|-------|
| filename | string | Original image filename |
| date | string | ISO format YYYY-MM-DD |
| total_amount | float | Raw number, no formatting |

## Date Extraction

### Priority Order
1. `YYYY-MM-DD` or `YYYY/MM/DD` - unambiguous, use directly
2. `DD/MM/YYYY` - prefer over MM/DD when ambiguous
3. `MM/DD/YYYY` - fallback when first number > 12

### Patterns
```python
DATE_PATTERNS = [
    # Unambiguous: YYYY-MM-DD or YYYY/MM/DD
    (r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b', 'ymd'),
    # Ambiguous: needs disambiguation
    (r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', 'dmy_or_mdy'),
]
```

### Disambiguation Logic
```python
def parse_ambiguous_date(num1, num2, year):
    """Handle DD/MM/YYYY vs MM/DD/YYYY ambiguity."""
    n1, n2 = int(num1), int(num2)
    if n1 > 12:
        # Must be DD/MM/YYYY
        return f"{year}-{n2:02d}-{n1:02d}"
    elif n2 > 12:
        # Must be MM/DD/YYYY
        return f"{year}-{n1:02d}-{n2:02d}"
    else:
        # Ambiguous - prefer DD/MM/YYYY (common outside US)
        return f"{year}-{n2:02d}-{n1:02d}"
```

## Total Amount Extraction

### Keyword Priority (highest to lowest)
```python
TOTAL_KEYWORDS = [
    'GRAND TOTAL',
    'TOTAL DUE',
    'AMOUNT DUE',
    'BALANCE DUE',
    'TOTAL',
    'AMOUNT',
]
```

### Exclusion Keywords (skip lines containing these)
```python
EXCLUSION_KEYWORDS = [
    'SUBTOTAL',
    'SUB TOTAL',
    'TAX',
    'GST',
    'VAT',
    'DISCOUNT',
    'CHANGE',
    'TENDERED',
]
```

### Amount Patterns
```python
AMOUNT_PATTERNS = [
    # Currency symbol + amount
    r'[\$€£RM]\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    r'[\$€£RM]\s*(\d+\.\d{2})',
    # Amount + currency symbol
    r'(\d+\.\d{2})\s*[\$€£RM]',
    # Bare amount with decimal
    r'\b(\d{1,3}(?:,\d{3})*\.\d{2})\b',
    r'\b(\d+\.\d{2})\b',
]
```

### Complete Extraction Function
```python
import re

def extract_invoice_total(text):
    """Extract total amount using keyword priority with exclusions."""
    lines = [l.strip().upper() for l in text.split('\n') if l.strip()]
    
    TOTAL_KEYWORDS = ['GRAND TOTAL', 'TOTAL DUE', 'AMOUNT DUE', 
                      'BALANCE DUE', 'TOTAL', 'AMOUNT']
    EXCLUSIONS = ['SUBTOTAL', 'SUB TOTAL', 'TAX', 'GST', 'VAT', 
                  'DISCOUNT', 'CHANGE']
    
    for keyword in TOTAL_KEYWORDS:
        for line in lines:
            if keyword in line:
                # Skip if line contains exclusion keyword
                if any(ex in line for ex in EXCLUSIONS):
                    continue
                
                # Extract amount
                match = re.search(r'[\$€£RM]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})', 
                                  text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    return float(amount_str)
    
    return None
```

## Multi-line Amount Formats

Some invoices place keyword and amount on separate lines:

```
GRAND TOTAL
$368.44
```

Or OCR splits keywords across lines:

```
TOTAL
DUE: 120.75
```

Handle with whitespace normalization and line lookahead:
```python
def extract_multiline_total(text):
    # Normalize whitespace first - handles OCR line splits
    text_normalized = ' '.join(text.split())
    
    TOTAL_KEYWORDS = ['GRAND TOTAL', 'TOTAL DUE', 'AMOUNT DUE', 'PAY THIS AMOUNT']
    
    # Try normalized text first
    for keyword in TOTAL_KEYWORDS:
        pattern = keyword.replace(' ', r'\s*') + r'[:\s]*\$?\s*([\d,]+\.\d{2})'
        match = re.search(pattern, text_normalized, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', ''))
    
    # Fallback: check line-by-line with lookahead
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for i, line in enumerate(lines):
        line_upper = line.upper()
        for keyword in TOTAL_KEYWORDS:
            if keyword in line_upper:
                # Check same line first
                match = re.search(r'[\$€£]?\s*([\d,]+\.\d{2})', line)
                if match:
                    return float(match.group(1).replace(',', ''))
                
                # Check next line
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    match = re.search(r'[\$€£]?\s*([\d,]+\.\d{2})', next_line)
                    if match:
                        return float(match.group(1).replace(',', ''))
    
    return None
```

## Invoice Number Extraction

```python
INVOICE_PATTERNS = [
    r'Invoice\s*No\.?\s*:?\s*([A-Z0-9-]+)',
    r'Invoice\s*#?\s*:?\s*([A-Z0-9-]+)',
    r'INV[ -]?([A-Z0-9-]+)',
    r'INV-?(\d{4}-\d{4,})',  # INV-YYYY-NNNN
    r'INV-?(\d{8})',         # INV-YYYYMMDD
]
```

## Common OCR Errors to Handle

| Error | Correction | Pattern |
|-------|-----------|---------|
| `O` (letter) → `0` | Digit zero | `re.sub(r'(?<=\d)O(?=\d)', '0', text)` |
| `l` → `1` | Digit one | `re.sub(r'\bl(?=\d)', '1', text)` |
| `S` → `5` | Digit five | Context-dependent |
| `B` → `8` | Digit eight | Context-dependent |
| `$` + space → amount | `$ 368.44` | Handle optional whitespace |
| Comma thousands | `1,234.56` | Strip comma before float conversion |

## Currency Handling

```python
CURRENCY_PATTERNS = {
    'USD': r'\$',
    'EUR': r'[€]|EUR',
    'GBP': r'[£]|GBP',
    'MYR': r'RM|MYR',
    'JPY': r'[¥]|JPY|yen',
}

def strip_currency(text):
    """Remove currency symbols, return clean number string."""
    text = re.sub(r'[\$€£RM]', '', text, flags=re.IGNORECASE)
    return text.strip()
```

## Validation Rules

1. **Amount sanity check**: Total should be > 0 and reasonable for context
2. **Date range**: Verify date is not in future, not too old
3. **Consistency**: Same total appearing across many invoices may indicate template data
4. **Currency consistency**: All amounts should use same currency (unless multi-currency invoice)

## Example: Complete Invoice Extractor

```python
import os
import re
import glob
from PIL import Image
import pytesseract
from openpyxl import Workbook

def process_invoices(image_dir, output_file):
    image_paths = sorted(glob.glob(os.path.join(image_dir, '*.jpg')))
    
    results = []
    for path in image_paths:
        text = pytesseract.image_to_string(Image.open(path))
        
        date = extract_invoice_date(text)
        total = extract_invoice_total(text)
        
        results.append({
            'filename': os.path.basename(path),
            'date': date,
            'total_amount': total  # Raw float
        })
    
    # Write Excel - None becomes empty cell
    wb = Workbook()
    ws = wb.active
    ws.title = 'invoices'
    ws.append(['filename', 'date', 'total_amount'])
    
    for r in results:
        ws.append([r['filename'], r['date'], r['total_amount']])
    
    wb.save(output_file)
    return results
```

## Utility Bill Specifics

Utility bills often use different terminology than invoices:

### Amount Keywords (priority order)
```python
UTILITY_AMOUNT_KEYWORDS = [
    'PAY THIS AMOUNT',   # Most explicit - what customer must pay
    'AMOUNT DUE',        # Standard billing term
    'TOTAL DUE',         # Alternative standard term
    'CURRENT CHARGES',   # Fallback - may not include fees
]
```

### Date Labels
```python
DATE_LABELS = [
    'STATEMENT DATE',
    'BILL DATE', 
    'DATE',
]
```

### Extraction Pattern
```python
def extract_utility_amount(text):
    """Extract payment amount from utility bill."""
    # Normalize whitespace to handle OCR line splits
    text_norm = ' '.join(text.upper().split())
    
    for keyword in ['PAY THIS AMOUNT', 'AMOUNT DUE', 'TOTAL DUE', 'CURRENT CHARGES']:
        # Allow flexible whitespace in keyword matching
        pattern = keyword.replace(' ', r'\s*') + r'[:\s]*\$?\s*([\d,]+\.\d{2})'
        match = re.search(pattern, text_norm)
        if match:
            return float(match.group(1).replace(',', ''))
    
    return None
```