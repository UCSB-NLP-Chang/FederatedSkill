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

### Order/Invoice Dates
```python
r'ORDER\s*DATE[:\s]+(\d{1,2})[/-](\d{1,2})[/-](\d{4})'
r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})'
```

### Date Priority & ISO Output
When multiple dates exist in the same image, prioritize in this order:
1. `EXP`/`EXPIRY` (expiry date)
2. `EXPIRES`
3. `MFG`/`MANUFACTURED` (manufacture date)
4. `ORDER DATE` / `INVOICE DATE`

Always normalize to `YYYY-MM-DD`. For partial dates (month/year only), use day 1.

## Prices & Totals

### Malaysian Ringgit (RM, MYR)
```python
r'(?:RM|MYR)\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
r'(?:RM|MYR)\s*(\d+\.\d{2})'
```

### US Dollar ($) & Generic Currency
```python
r'\$\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
r'\$\s*(\d+\.\d{2})'
r'(?:PRICE|COST|TOTAL|GRAND TOTAL|AMOUNT)[:\s]+\$?\s*(\d+\.\d{2})'
```

### Totals and Sums
```python
r'(?:GRAND\s+)?TOTAL[:\s]+\$?\s*(\d+\.\d{2})'
r'TOTAL\s*AMOUNT[:\s]+\$?\s*(\d+\.\d{2})'
r'(?:RM|MYR|\$|€|£)\s*(\d+\.?\d*)\s*(?:TOTAL|GRAND)?'
```

### Price Output
Return raw float value (no rounding). Strip thousands separators. Verifier decides precision.

## Order IDs

### Standard Formats
```python
r'(ORD-\d{4}-\d{5})'        # e.g., ORD-2024-00123
r'(SO-\d{4}-\d{3})'         # e.g., SO-2024-001
r'(INV-\d{8})'              # e.g., INV-20240001
r'(INV-\d{6})'              # shorter invoice variant
```

### Generic Labeled Extraction
```python
r'(?:ORDER|INV|ORD|SO|PO)[:\s#]*([A-Z0-9-]{6,20})'
r'ORDER\s*ID[:\s]+([A-Z0-9-]+)'
r'DOCUMENT\s*(?:NO|NUMBER|#)[:\s]+([A-Z0-9-]+)'
```

### Validation & Extraction Logic
```python
def parse_order_id(text, valid_ids=None):
    text_upper = text.upper()
    # Priority: Explicitly labeled first
    for pattern in [r'ORDER\s*ID[:\s]+([A-Z0-9-]{6,20})', r'\b(ORD-\d{4}-\d{5})\b', r'\b(SO-\d{4}-\d{3})\b', r'\b(INV-\d{6,8})\b']:
        match = re.search(pattern, text_upper)
        if match:
            order_id = match.group(1)
            if valid_ids is not None and order_id not in valid_ids:
                return None
            return order_id
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
    # Fix in order IDs: INV-2O24 -> INV-2024
    return re.sub(r'([A-Z]{3}-)(\d)([oO])(\d{3})', r'\g<1>\g<2>0\g<4>', text)
```