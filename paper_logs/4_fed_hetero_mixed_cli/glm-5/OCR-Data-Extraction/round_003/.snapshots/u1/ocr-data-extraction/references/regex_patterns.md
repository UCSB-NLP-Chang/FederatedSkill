# OCR Regex Pattern Library

Common patterns for extracting structured data from OCR text output.

## Order IDs and Invoice Numbers

### Common Formats

```regex
# Order ID patterns
ORD[-_]?\d{4}[-_]?\d{5}        # ORD-2024-00123, ORD_2024_00123
SO[-_]?\d{4}[-_]?\d{3}         # SO-2024-001, SO_2024_001
INV[-_]?\d{8}                  # INV-20240001, INV20240001
PO[-_]?\d{6,10}                # PO-123456, PO_123456789

# Generic order/invoice pattern
(?:ORD|SO|INV|PO)[-_]?(\d{4}[-_]?\d{3,5})

# Numeric order IDs
ORDER[:\s#]*(\d{6,12})
INVOICE[:\s#]*(\d{6,12})
```

### Extraction Example

```python
def extract_order_id(text):
    """Extract order ID from OCR text."""
    patterns = [
        r'(ORD[-_]?(?:\d{4}[-_]?\d{5}))',
        r'(SO[-_]?(?:\d{4}[-_]?\d{3}))',
        r'(INV[-_]?\d{8})',
        r'(?:ORDER|INVOICE)[:\s#]*(\d{6,12})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None
```

## Dates

### Label-Specific Patterns

```regex
# Expiration / Expiry
EXP(?:IRY|DATE)?[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})
EXP(?:IRY|DATE)?[:\s]*(\d{1,2}[\/\-\.]\d{4})

# Manufacturing / Production
MFG(?:DATE)?[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})
PROD(?:UCT)?\.?\s*DATE[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})

# Best Before
BB(?:E|\.\s*E)?[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})
BEST\s*BEFORE[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})

# Order/Transaction dates
ORDER\s*DATE[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})
DATE[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})

# Generic ISO-like
(\d{4}[\/\-\.]\d{2}[\/\-\.]\d{2})
```

### Normalization Logic

```python
def normalize_date(match: str, dayfirst: bool = True) -> str:
    """
    Convert various date formats to ISO YYYY-MM-DD.
    dayfirst=True for DD/MM/YYYY (common outside US).
    """
    # Handle partial dates (MM/YYYY)
    if match.count('/') == 1 or match.count('-') == 1:
        parts = re.split(r'[\/\-]', match)
        if len(parts[1]) == 4:  # MM/YYYY
            return f"{parts[1]}-{parts[0].zfill(2)}-01"
    
    # Full dates - use dayfirst based on source locale
    # Returns YYYY-MM-DD or raises for invalid
```

## Prices

### Currency Patterns

```regex
# Malaysian Ringgit variants
(?:RM|MYR)\s*(\d{1,3}(?:,\d{3})*\.\d{2})

# USD/Dollar variants  
(?:\$|USD)\s*(\d{1,3}(?:,\d{3})*\.\d{2})

# Euro
(?:€|EUR)\s*(\d{1,3}(?:,\d{3})*\.\d{2})

# Generic decimal (fallback)
(\d{1,3}(?:,\d{3})*\.\d{2})

# Price with each/EA suffix
(\d+\.\d{2})\s*(?:EA|EACH|PC|PIECE)?

# Total amount patterns
TOTAL[:\s]*(?:RM|MYR|\$)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})
AMOUNT[:\s]*(?:RM|MYR|\$)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})
```

### Price Normalization

```python
def normalize_price(text: str) -> float:
    """Extract numeric price from OCR text."""
    # Remove currency symbols and whitespace
    cleaned = re.sub(r'[RMYUSD€£,\s]', '', text)
    return float(cleaned)
```

## Product Codes

```regex
# Generic barcode formats
\b\d{8,13}\b

# Alphanumeric SKUs
SKU[:\s]*([A-Z0-9\-]{4,20})

# Lot numbers
LOT(?:NO)?\.?[:\s]*([A-Z0-9\-]+)
```

## Common OCR Error Corrections

| OCR Reads | Likely Intended | Correction Rule |
|-----------|-----------------|-----------------|
| `O` in numbers | `0` | Replace O with 0 in digit context |
| `l` (lowercase L) | `1` | Replace l with 1 in digit context |
| `S` in years | `5` | Context: `202S` → `2025` |
| `B` in numbers | `8` | Context: prices/dates |
| `$/` or `S` | `$` | Currency symbol OCR errors |
