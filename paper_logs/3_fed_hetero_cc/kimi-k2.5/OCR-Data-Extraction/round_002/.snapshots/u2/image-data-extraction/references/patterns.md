# OCR Extraction Patterns Reference

Ready-to-use regex patterns for common extraction tasks.

## Order IDs and Document Numbers

### Standard formats
```python
# ORD-YYYY-NNNNN (e.g., ORD-2024-00123)
r'\b(ORD-\d{4}-\d{5})\b'

# SO-YYYY-NNN (Sales Order)
r'\b(SO-\d{4}-\d{3})\b'

# INV-YYYYMMDD (Invoice)
r'\b(INV-\d{8})\b'
r'\b(INV-\d{6})\b'  # shorter variant

# Generic labeled
r'ORDER\s*ID[:\s#]+([A-Z0-9-]+)'
r'DOCUMENT\s*(?:NO|NUMBER|#)[:\s]+([A-Z0-9-]+)'
```

### Extract with label priority
```python
def parse_order_id(text):
    """Extract order ID, preferring explicitly labeled values."""
    text_upper = text.upper()
    
    # Priority 1: Labeled ORDER ID
    match = re.search(r'ORDER\s*ID[:\s#]+([A-Z0-9-]+)', text_upper)
    if match:
        return match.group(1)
    
    # Priority 2: Known prefixes with context
    for pattern in [r'\b(ORD-\d{4}-\d{5})\b', r'\b(SO-\d{4}-\d{3})\b', r'\b(INV-\d{6,8})\b']:
        match = re.search(pattern, text_upper)
        if match:
            return match.group(1)
    
    return None
```

## Dates

### Format: DD/MM/YYYY or DD-MM-YYYY
```python
r'(?:EXP|EXPIRY|EXPIRES?|MFG|DATE|ORDERED|INVOICE)[:\s]+(\d{1,2})[/-](\d{1,2})[/-](\d{4})'
```

### Format: MM/YYYY (partial)
```python
r'EXP(?:IRY)?[:\s]+(\d{1,2})[/-](\d{4})'
# Normalize to: YYYY-MM-01
```

### Format: YYYY/MM/DD
```python
r'(?:EXP|EXPIRY|DATE)[:\s]+(\d{4})[/-](\d{1,2})[/-](\d{1,2})'
```

### ISO Date Output
Always normalize to `YYYY-MM-DD`. For partial dates (month/year only), use day 1.
For ambiguous `DD-MM-YYYY`, use `>12` heuristic: if first component > 12, it's a day.

## Prices

### Malaysian Ringgit (RM, MYR)
```python
r'(?:RM|MYR)\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
r'(?:RM|MYR)\s*(\d+\.\d{2})'
```

### US Dollar ($)
```python
r'\$\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
r'\$\s*(\d+\.\d{2})'
```

### Generic with currency words
```python
r'(?:PRICE|COST|TOTAL|GRAND TOTAL|AMOUNT DUE|BALANCE)[:\s]+\$?\s*(\d+\.\d{2})'
r'\$\s*(\d+\.?\d*)\s*(?:TOTAL|GRAND)?'
```

### Price Output
Return raw float value (no rounding). Strip thousands separators before converting.
Pass directly to Excel/JSON; let verifier decide precision tolerance.

## Product Codes

### Alphanumeric codes
```python
r'(?:SKU|CODE|PRODUCT)[:\s]+([A-Z0-9-]+)'
```

### Barcode/EAN patterns
```python
r'\b(\d{8,13})\b'  # 8-13 digit numbers
```

## OCR Cleanup

### Common substitutions to handle
| OCR Error | Likely Intended |
|-----------|-----------------|
| `O` (letter) | `0` (digit) in numeric context |
| `l` (lowercase L) | `1` (digit) |
| `S` | `5` in prices |
| `B` | `8` in dates |
| `|` (pipe) | `1` or `I` |

### Post-processing normalization
```python
def normalize_ocr_price(text):
    # Fix common OCR substitutions in price context
    text = re.sub(r'(?<=\d)[oO](?=\d)', '0', text)  # 1O.99 -> 10.99
    text = re.sub(r'[lL](?=\d)', '1', text)         # l2.99 -> 12.99
    return text

def normalize_ocr_id(text):
    # Fix in order IDs: INV-2O24 → INV-2024
    return re.sub(r'([A-Z]{3}-)(\d)([oO])(\d{3})', r'\g<1>\g<2>0\g<4>', text)
```