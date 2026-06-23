# Amount/Total Keyword Patterns

## Priority Order for Amount Extraction

Different documents use varying keywords for the final amount. Check in this priority order:

| Priority | Keyword | Pattern | Use Case |
|----------|---------|---------|----------|
| 1 | `PAY THIS AMOUNT` | `r'PAY THIS AMOUNT\s*\n*\s*\$?([\d,.]+)'` | Utility bills, government forms |
| 2 | `CURRENT CHARGES` | `r'CURRENT CHARGES:\s*\$?([\d,.]+)'` | Utility bills, statements |
| 3 | `AMOUNT DUE` | `r'AMOUNT DUE:\s*\$?([\d,.]+)'` | Invoices, bills |
| 4 | `TOTAL DUE` | `r'TOTAL\s*DUE:\s*\$?([\d,.]+)'` | Invoices (may be split across lines) |
| 5 | `TOTAL` | `r'TOTAL:\s*\$?([\d,.]+)'` | Generic fallback |
| 6 | `GRAND TOTAL` | `r'GRAND TOTAL:\s*\$?([\d,.]+)'` | Final amount after tax |
| 7 | `SUBTOTAL` | `r'SUBTOTAL:\s*\$?([\d,.]+)'` | Pre-tax, last resort |

## Split-Line OCR Handling

OCR frequently inserts newlines between related words:

```python
import re

# Raw OCR: "TOTAL\n\nDUE: 120.75"
# Normalized: "TOTAL DUE: 120.75"

def extract_amount_split_lines(text):
    """Extract amount handling split-line OCR."""
    # Normalize newlines to spaces for pattern matching
    normalized = re.sub(r'\n+', ' ', text)
    
    patterns = [
        r'PAY THIS AMOUNT\s+\$?([\d,.]+)',
        r'CURRENT CHARGES:\s*\$?([\d,.]+)',
        r'AMOUNT DUE:\s*\$?([\d,.]+)',
        r'TOTAL\s+DUE:\s*\$?([\d,.]+)',
        r'TOTAL:\s*\$?([\d,.]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            return match.group(1).replace(',', '')
    
    return None

# Alternative: use DOTALL to match across newlines
def extract_amount_dotall(text):
    """Extract amount using DOTALL for multiline matching."""
    pattern = r'TOTAL\s*DUE:\s*\$?([\d,.]+)'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).replace(',', '')
    return None
```

## Distractor Patterns to Ignore

Exclude these from amount extraction:

- `PREVIOUS BALANCE` - Prior period, not current charge
- `LATE FEE` - Penalty, not base amount
- `TAX` / `GST` / `VAT` - Component, not total
- `CREDIT` - Negative adjustment
- `CURRENT USAGE` - Usage quantity, not dollar amount

```python
def is_distractor_line(line):
    """Check if line contains a distractor pattern."""
    distractors = r'PREVIOUS BALANCE|LATE FEE|TAX|GST|VAT|CREDIT|CURRENT USAGE'
    return re.search(distractors, line, re.IGNORECASE)
```

## Amount Extraction Function

```python
import re

def extract_total_amount(text):
    """
    Extract total/amount due from OCR text.
    Handles split-line OCR and multiple keyword variants.
    """
    # Normalize whitespace for split-line patterns
    normalized = re.sub(r'\n+', ' ', text)
    
    # Priority order patterns
    patterns = [
        (r'PAY THIS AMOUNT\s+\$?([\d,.]+)', 'pay_this'),
        (r'CURRENT CHARGES:\s*\$?([\d,.]+)', 'current_charges'),
        (r'AMOUNT DUE:\s*\$?([\d,.]+)', 'amount_due'),
        (r'TOTAL\s+DUE:\s*\$?([\d,.]+)', 'total_due'),
        (r'TOTAL:\s*\$?([\d,.]+)', 'total'),
        (r'GRAND TOTAL:\s*\$?([\d,.]+)', 'grand_total'),
    ]
    
    for pattern, label in patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '').replace('$', '')
            try:
                return float(amount_str), label
            except ValueError:
                continue
    
    return None, None

def format_amount(value):
    """Format amount as string with exactly 2 decimal places."""
    if value is None:
        return ''
    return f"{float(value):.2f}"
```

## Utility Bill Specific Patterns

```python
# Common utility bill patterns
UTILITY_PATTERNS = {
    'date': [
        r'STATEMENT DATE:\s*([\d/-]+)',
        r'BILL DATE:\s*([\d/-]+)', 
        r'DATE:\s*([\d/-]+)',
    ],
    'amount': [
        r'PAY THIS AMOUNT\s+\$?([\d,.]+)',
        r'CURRENT CHARGES:\s*\$?([\d,.]+)',
        r'AMOUNT DUE:\s*\$?([\d,.]+)',
        r'TOTAL\s+DUE:\s*\$?([\d,.]+)',
    ]
}
```
