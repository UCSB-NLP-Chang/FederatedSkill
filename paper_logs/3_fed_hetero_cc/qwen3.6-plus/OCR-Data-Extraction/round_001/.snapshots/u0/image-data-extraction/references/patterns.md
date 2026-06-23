# OCR Extraction Patterns Reference

Ready-to-use regex patterns for common extraction tasks.

## Dates

### Format: DD/MM/YYYY or DD-MM-YYYY
```python
r'(?:EXP|EXPIRY|EXPIRES?|MFG)[:\s]+(\d{1,2})[/-](\d{1,2})[/-](\d{4})'
```

### Format: MM/YYYY (partial)
```python
r'EXP(?:IRY)?[:\s]+(\d{1,2})[/-](\d{4})'
# Normalize to: YYYY-MM-01
```

### Format: YYYY/MM/DD
```python
r'(?:EXP|EXPIRY)[:\s]+(\d{4})[/-](\d{1,2})[/-](\d{1,2})'
```

### ISO Date Output
Always normalize to `YYYY-MM-DD`. For partial dates (month/year only), use day 1.

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
r'(?:PRICE|COST)[:\s]+\$\s*(\d+\.\d{2})'
```

### Price Output
Return raw float value (no rounding). Strip thousands separators. Verifier decides precision.

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

### Post-processing normalization
```python
def normalize_ocr_price(text):
    # Fix common OCR substitutions in price context
    text = re.sub(r'(?<=\d)[oO](?=\d)', '0', text)  # 1O.99 -> 10.99
    text = re.sub(r'[lL](?=\d)', '1', text)         # l2.99 -> 12.99
    return text
```