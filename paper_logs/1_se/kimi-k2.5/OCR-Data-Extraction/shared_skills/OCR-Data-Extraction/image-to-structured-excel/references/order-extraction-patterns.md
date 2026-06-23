# Order Extraction Patterns

## Reference File Loading

```python
import csv

def load_roster(csv_path, delimiter='\t'):
    """Load reference data keyed by ID.
    
    Handles tab-delimited rosters common in claim systems.
    """
    data = {}
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            key = row.get('claim_code', row.get('order_id', row.get('id')))
            data[key] = {k: v for k, v in row.items() if k != key}
    return data
```

## Invoice Total Keyword Priority

When extracting totals from invoices, multiple keywords may appear. Check in priority order:

| Priority | Keyword | Pattern | Notes |
|----------|---------|---------|-------|
| 1 | GRAND TOTAL | `r'GRAND TOTAL:\s*\$?([\d.]+)'` | Final amount after tax |
| 2 | TOTAL DUE | `r'TOTAL DUE:\s*\$?([\d.]+)'` | Amount payable |
| 3 | TOTAL | `r'TOTAL:\s*\$?([\d.]+)'` | May appear multiple times |
| 4 | REIMBURSABLE TOTAL | `r'REIMBURSABLE TOTAL:\s*\$?([\d.]+)'` | For expense claims |
| 5 | SUBTOTAL | `r'SUBTOTAL:\s*\$?([\d.]+)'` | Pre-tax amount, fallback only |

```python
import re

def extract_total(text):
    """Extract total amount using priority keyword system."""
    total_patterns = [
        (r'GRAND TOTAL:\s*\$?([\d.]+)', 'grand_total'),
        (r'TOTAL DUE:\s*\$?([\d.]+)', 'total_due'),
        (r'TOTAL:\s*\$?([\d.]+)', 'total'),
        (r'REIMBURSABLE TOTAL:\s*\$?([\d.]+)', 'reimbursable'),
        (r'SUBTOTAL:\s*\$?([\d.]+)', 'subtotal'),
    ]
    
    for pattern, label in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return format_price(match.group(1)), label
    
    return '', None
```

## OCR Pattern Examples

| Field | Pattern | Regex |
|-------|---------|-------|
| Claim Code | `CLAIM CODE: CLM-YYYY-XXX` | `r'CLAIM CODE:\s*(CLM-\d{4}-\d+)'` |
| Transaction Date | `TRANSACTION DATE: DD/MM/YYYY` | `r'TRANSACTION DATE:\s*([\d/]+)'` |
| Total/Amount | `REIMBURSABLE TOTAL: XX.XX` or `GRAND TOTAL: $XX.XX` | `r'TOTAL:\s*\$?([\d.]+)'` |
| Order ID (ORD) | `ORDER ID: ORD-YYYY-XXXXX` | `r'ORDER ID:\s*(ORD-\d{4}-\d{5})'` |
| Order ID (SO) | `ORDER ID: SO-YYYY-XXX` | `r'ORDER ID:\s*(SO-\d{4}-\d+)'` |
| Order ID (INV) | `ORDER ID: INV-YYYYXXXX` | `r'ORDER ID:\s*(INV-\d+)'` |
| Invoice Number | `Invoice No: INV-XXXXX` | `r'Invoice\s*No:\s*(INV-\d+)'` |
| Order Date | `ORDER DATE: DD/MM/YYYY` | `r'ORDER DATE:\s*([\d/]+)'` |
| Invoice Date | `Date: DD/MM/YYYY` | `r'^Date:\s*([\d/]+)'` or `r'Date:\s*([\d/]+)'` |

## Partial Match Handling

```python
def enrich_from_roster(extracted_id, roster):
    """Return enriched fields or empty strings for missing IDs."""
    if extracted_id in roster:
        return roster[extracted_id]
    # Return empty strings for Excel compatibility
    return {k: '' for k in expected_fields}
```

## Deduplication Logic

```python
seen_ids = set()
results = []

for img_path in sorted(image_paths):
    extracted_id = extract_id(ocr_text)
    
    if extracted_id in seen_ids:
        # Duplicate: output nulls
        result = {'filename': basename, 'id': None, 
                  'date': None, 'amount': None}
    else:
        seen_ids.add(extracted_id)
        result = {'filename': basename, 'id': extracted_id,
                  'date': extract_date(ocr_text),
                  'amount': format_price(extract_amount(ocr_text))}
    results.append(result)
```

## Price Formatting

```python
def format_price(value):
    """Ensure price is string with exactly 2 decimal places."""
    if value is None or value == '':
        return ''
    try:
        # Remove currency prefixes first
        clean = str(value).replace('$', '').replace('RM', '').replace('MYR', '').strip()
        return f"{float(clean):.2f}"
    except (ValueError, TypeError):
        return ''
```

## Excel Empty Cell Handling

```python
# CORRECT: empty string for empty cells
row = [filename, code, '', '', date, amount]  # Empty strings

# WRONG: None becomes 'None' literal or causes issues
row = [filename, code, None, None, date, amount]  # Avoid
```
