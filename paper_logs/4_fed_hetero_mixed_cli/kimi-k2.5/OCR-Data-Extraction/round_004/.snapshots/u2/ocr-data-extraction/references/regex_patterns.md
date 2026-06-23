# OCR Regex Pattern Library

Common patterns for extracting structured data from OCR text output.

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

# Generic ISO-like
(\d{4}[\/\-\.]\d{2}[\/\-\.]\d{2})
```

### Date Format Disambiguation

When regex finds `\d{1,2}/\d{1,2}/\d{4}`, the format is ambiguous. Use validation logic:

```python
def extract_date_with_fallback(text):
    """Extract date trying DD/MM first, then MM/DD if invalid."""
    match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', text)
    if not match:
        # Try ISO format
        iso_match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', text)
        if iso_match:
            y, m, d = map(int, iso_match.groups())
            return f"{y:04d}-{m:02d}-{d:02d}"
        return None
    
    first, second, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    
    # Try DD/MM/YYYY first (more common globally)
    if first <= 31 and second <= 12:
        try:
            datetime(year, second, first)
            return f"{year:04d}-{second:02d}-{first:02d}"
        except ValueError:
            pass
    
    # Fall back to MM/DD/YYYY
    if first <= 12 and second <= 31:
        try:
            datetime(year, first, second)
            return f"{year:04d}-{first:02d}-{second:02d}"
        except ValueError:
            pass
    
    return None
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
```

### Price Normalization

```python
def normalize_price(text: str) -> float:
    """Extract numeric price from OCR text."""
    # Remove currency symbols and whitespace
    cleaned = re.sub(r'[RMYUSD€£,\s]', '', text)
    return float(cleaned)
```

## Invoice-Specific Patterns

### Total Amount Labels

Invoices use inconsistent labels for the final amount. Match in this priority order:

```regex
# 1. Grand Total (most specific)
GRAND\s*TOTAL\s*[:\-]?\s*[\$£€]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})

# 2. Total Due / Total Amount (explicit)
TOTAL\s*(?:DUE|AMOUNT)\s*[:\-]?\s*[\$£€]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})

# 3. Balance Due
BALANCE\s*(?:DUE)?\s*[:\-]?\s*[\$£€]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})

# 4. Generic Total (avoid subtotals)
(?<!SUB)\s*TOTAL\s*[:\-]?\s*[\$£€]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})

# 5. Amount Payable / Payment Due
(?:AMOUNT\s*PAYABLE|PAYMENT\s*DUE)\s*[:\-]?\s*[\$£€]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})
```

**Extraction Strategy:**
1. Search for "GRAND TOTAL" first (highest confidence)
2. If not found, search for "TOTAL DUE" or "TOTAL AMOUNT"
3. If still not found, use negative lookahead to find "TOTAL" but not "SUBTOTAL"
4. Always validate that extracted amount > 0 and < reasonable maximum

### Invoice Dates

```regex
# Standard date labels
(?:INVOICE\s*)?DATE\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})
(?:ISSUE\s*)?DATE\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})

# Due date (if looking for payment terms)
DUE\s*DATE\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})
```

## Order IDs (E-commerce & Logistics)

```regex
# Standard order format: ORD-YYYY-NNNNN
\bORD-\d{4}-\d{5}\b

# Sales order format: SO-YYYY-NNN
\bSO-\d{4}-\d{3}\b

# Purchase order format: PO-YYYY-NNNNN
\bPO-\d{4}-\d{5}\b

# Invoice format: INV-YYYYNNNN (8 digits after INV)
\bINV-\d{8}\b

# Generic order ID (comprehensive fallback)
\b(?:ORD|SO|PO|INV)[-\s]?\d{4}[-\s]?\d{3,6}\b

# Amazon-style order (3-7-7 format)
\b\d{3}-\d{7}-\d{7}\b
```

### Order ID Validation

When validating against reference lists:
- Normalize case (uppercase) before comparison
- Strip whitespace and common OCR artifacts (`\n`, `\t`)
- Check for common substitutions: O→0, I→1, S→5

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
|-----------|----------------|-----------------|
| `O` in numbers | `0` | Replace O with 0 in digit context |
| `l` (lowercase L) | `1` | Replace l with 1 in digit context |
| `S` in years | `5` | Context: `202S` → `2025` |
| `B` in numbers | `8` | Context: prices/dates |
| `$/` or `S` | `$` | Currency symbol OCR errors |
| `ORD-2O24` | `ORD-2024` | Letter O to zero in order IDs |
| `02/14/2024` | `2024-02-14` | US format (Feb 14) vs EU (14 Feb) - use validation |
