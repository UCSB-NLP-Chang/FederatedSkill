# OCR Extraction Patterns Reference

Ready-to-use regex patterns for common extraction tasks.

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

### Date Priority Order
When multiple dates exist in the same image:
1. `EXP`/`EXPIRY` (expiry date) - highest priority
2. `EXPIRES` - second priority
3. `MFG`/`MANUFACTURED` (manufacture date) - lowest priority

## Prices & Totals

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

### Generic with currency/label
```python
r'(?:PRICE|COST|TOTAL|GRAND TOTAL|AMOUNT DUE)[:\s]+\$?\s*(\d+\.\d{2})'
r'TOTAL\s*AMOUNT[:\s]+\$?\s*(\d+\.\d{2})'
```

### Price Output
Return raw float values. Strip thousands separators. Do NOT format to fixed decimals at extraction time. Verifier decides precision.

## Order IDs

### Standard formats
```python
r'(ORD-\d{4}-\d{5})'          # e.g., ORD-2024-00123
r'(SO-\d{4}-\d{3})'           # e.g., SO-2024-001
r'(INV-\d{8})'                # e.g., INV-20240001
```

### Generic labeled extraction
```python
r'(?:ORDER|INV|ORD|SO|PO)[:\s#]*([A-Z0-9-]{6,20})'
r'ORDER\s*ID[:\s]+([A-Z0-9-]+)'
```

### Extraction logic with priority
```python
def extract_order_id(text, valid_ids=None):
    text_upper = text.upper()
    for pattern in [r'ORDER\s*ID[:\s]+([A-Z0-9-]+)', r'\b(ORD-\d{4}-\d{5})\b', r'\b(SO-\d{4}-\d{3})\b', r'\b(INV-\d{6,8})\b']:
        match = re.search(pattern, text_upper)
        if match:
            oid = match.group(1)
            return oid if valid_ids is None or oid in valid_ids else None
    return None
```

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

### Common substitutions
| OCR Error | Likely Intended |
|-----------|-----------------|
| `O` (letter) | `0` (digit) in numeric context |
| `l` (lowercase L) | `1` (digit) |
| `S` | `5` in prices |
| `B` | `8` in dates |

### Post-processing normalization
```python
def normalize_ocr_price(text):
    text = re.sub(r'(?<=\d)[oO](?=\d)', '0', text)  # 1O.99 -> 10.99
    text = re.sub(r'[lL](?=\d)', '1', text)         # l2.99 -> 12.99
    return text

def normalize_ocr_id(text):
    return re.sub(r'([A-Z]{3}-)(\d)([oO])(\d{3})', r'\g<1>\g<2>0\g<4>', text)
```