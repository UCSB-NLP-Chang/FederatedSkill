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

### Date Format Disambiguation (DD/MM vs MM/DD)
When regex captures two numeric components and a year, determine format:
```python
def disambiguate_date(num1, num2, year):
    """
    Given two date components (day/month or month/day) and year,
    determine the correct ISO date.
    
    Rules:
    - If num1 > 12: num1 is day, num2 is month (DD/MM/YYYY)
    - If num2 > 12: num2 is day, num1 is month (MM/DD/YYYY)
    - If both <= 12: ambiguous, prefer DD/MM/YYYY
    """
    if num1 > 12:
        return f"{year}-{num2:02d}-{num1:02d}"  # DD/MM/YYYY
    elif num2 > 12:
        return f"{year}-{num1:02d}-{num2:02d}"  # MM/DD/YYYY
    else:
        return f"{year}-{num2:02d}-{num1:02d}"  # Default DD/MM/YYYY
```

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
r'(?:PRICE|COST|TOTAL|GRAND TOTAL|AMOUNT DUE|BALANCE)[:\s]+\$?\s*(\d+\.\d{2})'
r'TOTAL\s*AMOUNT[:\s]+\$?\s*(\d+\.\d{2})'
```

### Price Output
Return raw float values. Strip thousands separators. Do NOT format to fixed decimals at extraction time. Verifier decides precision.

## Invoice Total Extraction

### Keyword Priority Order
When extracting invoice totals, scan lines in this priority order:
1. `GRAND TOTAL`
2. `TOTAL DUE`
3. `AMOUNT DUE`
4. `TOTAL`
5. `AMOUNT`

### Exclusion Keywords
Skip lines containing these keywords even if they match total patterns:
- `SUBTOTAL`, `SUB TOTAL`
- `TAX`, `GST`, `VAT`
- `DISCOUNT`
- `CHANGE`

### Extraction Logic
```python
TOTAL_KEYWORDS = ["GRAND TOTAL", "TOTAL DUE", "AMOUNT DUE", "TOTAL", "AMOUNT"]
EXCLUDE_KEYWORDS = ["SUBTOTAL", "SUB TOTAL", "TAX", "GST", "DISCOUNT", "CHANGE"]

def extract_invoice_total(text):
    lines = text.split('\n')
    for keyword in TOTAL_KEYWORDS:
        for line in lines:
            upper_line = line.upper()
            if keyword in upper_line:
                if any(excl in upper_line for excl in EXCLUDE_KEYWORDS):
                    continue
                # Extract numeric value
                matches = re.findall(r'[\d,]+\.?\d*', upper_line)
                for match in matches:
                    cleaned = match.replace(',', '')
                    try:
                        val = float(cleaned)
                        if val > 0:
                            return val
                    except ValueError:
                        continue
    return None
```

### Date Line Prioritization
When multiple dates appear in an invoice, prioritize lines containing:
- `DATE`, `INVOICE`, `ISSUED`, `BILL`, `INVOICE DATE`

```python
def find_date_lines(text):
    date_keywords = ['DATE', 'INVOICE', 'ISSUED', 'BILL']
    return [line for line in text.split('\n') if any(kw in line.upper() for kw in date_keywords)]
```

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

## Claim Codes

### Standard formats
```python
r'(CLM-\d{4}-\d{3})'          # e.g., CLM-2024-001
r'(CLAIM-\d{4}-\d{3})'        # e.g., CLAIM-2024-001
```

### Labeled extraction
```python
r'(?:Claim\s*Code|Claim\s*Ref|Expense\s*Code)[:\s]*(CLM-\d{4}-\d{3})'
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