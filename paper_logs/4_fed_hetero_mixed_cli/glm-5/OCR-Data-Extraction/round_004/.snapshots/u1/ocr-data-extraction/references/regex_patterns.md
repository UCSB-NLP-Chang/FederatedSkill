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
# Invoice dates
INVOICE\s*DATE[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})
INV\.?\s*DATE[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})

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

**Decision Rule**: When day ≤ 12 and month ≤ 12, both formats are mathematically valid. Use these heuristics:
- If one interpretation fails calendar validation (e.g., day 31 in month with 30 days), use the other
- If both valid and you have batch context, check surrounding dates for format consistency
- When uncertain, prefer DD/MM for documents from non-US sources

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

## Prices and Totals

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

### Total Amount Patterns (Invoices, Receipts)

Invoices use varying labels for final amounts. Match in this priority order:

```regex
# 1. Grand Total (most specific)
GRAND\s*TOTAL[:\s]*(?:RM|MYR|\$|USD)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})

# 2. Total Due / Total Amount (explicit)
TOTAL\s*(?:DUE|AMOUNT)[:\s]*(?:RM|MYR|\$|USD)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})

# 3. Balance Due
BALANCE\s*(?:DUE)?[:\s]*(?:RM|MYR|\$|USD)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})

# 4. Generic Total (avoid subtotals)
(?<!SUB)\s*TOTAL[:\s]*(?:RM|MYR|\$|USD)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})

# 5. Amount Payable / Payment Due
(?:AMOUNT\s*PAYABLE|PAYMENT\s*DUE)[:\s]*(?:RM|MYR|\$|USD)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})

# Subtotal (fallback only if no total found)
SUBTOTAL[:\s]*(?:RM|MYR|\$|USD)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})
```

### Price Extraction with Priority

```python
def extract_total_amount(text):
    """Extract total amount from invoice/receipt text with priority."""
    patterns = [
        r'GRAND\s*TOTAL[:\s]*(?:RM|MYR|\$|USD)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
        r'TOTAL\s*DUE[:\s]*(?:RM|MYR|\$|USD)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
        r'TOTAL[:\s]*(?:RM|MYR|\$|USD)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
        r'AMOUNT[:\s]*(?:RM|MYR|\$|USD)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', ''))
    return None
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

### Order ID Validation

When validating against reference lists:
- Normalize case (uppercase) before comparison
- Strip whitespace and common OCR artifacts (`\n`, `\t`)
- Check for common substitutions: O→0, I→1, S→5

## Common OCR Error Corrections

| OCR Reads | Likely Intended | Correction Rule |
|-----------|-----------------|-----------------|
| `O` in numbers | `0` | Replace O with 0 in digit context |
| `l` (lowercase L) | `1` | Replace l with 1 in digit context |
| `S` in years | `5` | Context: `202S` → `2025` |
| `B` in numbers | `8` | Context: prices/dates |
| `$/` or `S` | `$` | Currency symbol OCR errors |
| `ORD-2O24` | `ORD-2024` | Letter O to zero in order IDs |
| `02/14/2024` | `2024-02-14` | US format (Feb 14) vs EU (14 Feb) - use validation |
