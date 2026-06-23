# Utility Bill Extraction Patterns

Patterns for extracting data from utility bill images and filling template workbooks.

## Column Requirements

Standard utility bill output format:
| Column | Type | Notes |
|--------|------|-------|
| scan_name | string | Original image filename |
| bill_date | string | ISO format YYYY-MM-DD |
| amount_due | float | Raw number, no formatting |

## Multi-Line Keyword Extraction

OCR frequently splits compound keywords like "TOTAL DUE" across lines:
```
Line 11: 'TOTAL'
Line 12: ''
Line 13: 'DUE: 120.75'
```

### Implementation
```python
import re

def extract_amount_multiline(text):
    """Extract amount when keyword is split across OCR lines."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    keyword_parts = ['TOTAL', 'AMOUNT', 'GRAND', 'BALANCE', 'PAY', 'CURRENT']
    continuation_parts = ['DUE', 'TOTAL', 'AMOUNT', 'CHARGES']
    
    for i, line in enumerate(lines):
        line_upper = line.upper().strip()
        # Check if line contains a keyword part (exact or near-exact match)
        for part in keyword_parts:
            if part in line_upper and len(line_upper) <= len(part) + 2:
                # Look at next 1-2 non-empty lines for continuation
                for j in range(i + 1, min(i + 3, len(lines))):
                    next_line = lines[j]
                    next_upper = next_line.upper()
                    if any(c in next_upper for c in continuation_parts):
                        match = re.search(r'[\$€£]?\s*(\d+\.?\d*)', next_line)
                        if match:
                            return float(match.group(1))
    return None
```

### Whitespace Normalization Alternative
Normalize whitespace before pattern matching to handle OCR line splits:
```python
def extract_total_normalized(text):
    """Extract total with whitespace normalization for multi-line keywords."""
    text_normalized = ' '.join(text.split())  # Collapse all whitespace
    BILL_KEYWORDS = ['PAY THIS AMOUNT', 'CURRENT CHARGES', 'TOTAL DUE', 'AMOUNT DUE']
    
    for keyword in BILL_KEYWORDS:
        # Allow flexible whitespace in keyword matching
        pattern = keyword.replace(' ', r'\s*') + r'[:\s]*[\$€£]?\s*([\d,]+\.\d{2})'
        match = re.search(pattern, text_normalized, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', ''))
    return None
```

### Usage Pattern
Try single-line extraction first. If amount is None for >20% of images, fall back to multi-line:
```python
def extract_total_robust(text):
    amount = extract_total_normalized(text)  # Try whitespace normalization first
    if amount is None:
        amount = extract_amount_multiline(text)  # Fallback to line-by-line search
    return amount
```

## Template Workbook Filling

When a task provides a template workbook with placeholder rows:

### Implementation
```python
import openpyxl

def fill_template_workbook(template_path, output_path, data_rows, sheet_name='bills'):
    """Fill a template workbook, preserving all sheets and removing placeholders."""
    wb = openpyxl.load_workbook(template_path)
    
    if sheet_name not in wb.sheetnames:
        raise ValueError(f"Sheet '{sheet_name}' not found in template")
    
    ws = wb[sheet_name]
    
    # Remove placeholder rows (keep header at row 1)
    # Delete from bottom up to avoid index shifting
    for row in range(ws.max_row, 1, -1):
        ws.delete_rows(row)
    
    # Write data rows starting at row 2
    for i, row_data in enumerate(data_rows, start=2):
        for j, value in enumerate(row_data, start=1):
            ws.cell(row=i, column=j, value=value)
    
    wb.save(output_path)
    return wb
```

### Validation
```python
def verify_template_fill(wb, expected_sheet_names, expected_row_count, sheet_name='bills'):
    """Verify template was filled correctly."""
    # Check all sheets preserved
    assert set(wb.sheetnames) == set(expected_sheet_names), f"Sheet mismatch: {wb.sheetnames}"
    
    # Check data sheet
    ws = wb[sheet_name]
    actual_data_rows = ws.max_row - 1  # Subtract header
    assert actual_data_rows == expected_row_count, f"Row count mismatch: {actual_data_rows} vs {expected_row_count}"
    
    # Check cover sheet unchanged (if exists)
    if 'cover' in wb.sheetnames:
        cover = wb['cover']
        assert cover['A1'].value is not None, "Cover sheet appears modified"
```

## Amount Extraction Priority

### Keyword Priority (highest to lowest)
```python
BILL_KEYWORDS = [
    'PAY THIS AMOUNT',     # Most explicit - what customer must pay
    'CURRENT CHARGES',     # Main billing amount
    'TOTAL DUE',           # Standard billing term
    'AMOUNT DUE',          # Alternative standard term
    'BALANCE DUE',         # Remaining balance
    'TOTAL',               # Generic fallback
    'AMOUNT'               # Last resort
]
```

### Exclusion Keywords (skip lines containing these)
```python
BILL_EXCLUSIONS = [
    'PREVIOUS BALANCE',
    'LATE FEE',
    'TAX',
    'GST',
    'VAT',
    'CREDIT',
    'SUBTOTAL',
    'SUB TOTAL',
    'DISCOUNT'
]
```

## Date Patterns for Utility Bills

Utility bills typically contain dates in these formats:
- `YYYY-MM-DD` (most common, unambiguous)
- `MM/DD/YYYY`
- `DD/MM/YYYY`

### Keywords to Search
```python
DATE_KEYWORDS = ['DATE', 'BILL DATE', 'STATEMENT DATE', 'DUE DATE', 'INVOICE DATE']

def find_date_lines(text):
    """Find lines likely containing the bill date."""
    lines = text.split('\n')
    return [line for line in lines if any(kw in line.upper() for kw in DATE_KEYWORDS)]
```

### Extraction
```python
def extract_bill_date(text):
    """Extract and normalize bill date."""
    # Try YYYY-MM-DD first (unambiguous)
    match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', text)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    
    # Try MM/DD/YYYY or DD/MM/YYYY
    match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', text)
    if match:
        a, b, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if a > 12:
            return f"{year}-{b:02d}-{a:02d}"  # DD/MM/YYYY
        elif b > 12:
            return f"{year}-{a:02d}-{b:02d}"  # MM/DD/YYYY
        else:
            return f"{year}-{b:02d}-{a:02d}"  # Default DD/MM/YYYY
    
    return None
```

## Complete Utility Bill Extractor

```python
import os
import re
import glob
from PIL import Image
import pytesseract
import openpyxl

def process_utility_bills(image_dir, template_path, output_path):
    image_paths = sorted(glob.glob(os.path.join(image_dir, '*.jpg')))
    
    results = []
    for path in image_paths:
        text = pytesseract.image_to_string(Image.open(path))
        
        date = extract_bill_date(text)
        amount = extract_total_robust(text)
        
        results.append([
            os.path.basename(path),  # scan_name
            date,                    # bill_date
            amount                   # amount_due (raw float)
        ])
    
    # Fill template
    fill_template_workbook(template_path, output_path, results, sheet_name='bills')
    return results
```

## Common OCR Errors in Utility Bills

| Error | Correction | Context |
|-------|-----------|---------|
| `O` → `0` | Digit zero in amounts | `1O.75` → `10.75` |
| `l` → `1` | Digit one in amounts | `l20.75` → `120.75` |
| `S` → `5` | Digit five in amounts | Context-dependent |
| Split keywords | Multi-line lookup | `TOTAL` / `DUE: amount` |
| Currency symbols | Strip before parsing | `$`, `€`, `£` |
| Comma thousands | Strip before float | `1,234.56` → `1234.56` |

## Validation Rules

1. **Row count**: Must equal number of input images
2. **Sheet preservation**: All original sheets must exist unchanged
3. **Placeholder removal**: No empty/example rows in data sheet
4. **Sort order**: Rows sorted by `scan_name` ascending
5. **Date format**: All dates in `YYYY-MM-DD`
6. **Amount precision**: Raw floats, no formatting - pass full precision to verifier