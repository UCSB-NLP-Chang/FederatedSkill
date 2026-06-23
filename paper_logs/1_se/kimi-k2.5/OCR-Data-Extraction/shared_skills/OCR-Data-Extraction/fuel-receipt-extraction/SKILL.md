---
name: fuel-receipt-extraction
description: Extract structured fuel purchase receipt data from mixed image collections containing receipts, cover sheets, notes, and promotional materials. Use when images contain fuel/pump sale receipts with TXN REF, SALE DATE, and GRAND TOTAL patterns mixed with non-receipt documents that must be filtered out.
---

# Fuel Receipt Extraction from Mixed Image Collections

Extract fuel purchase data from receipt images while filtering non-receipt documents in mixed datasets.

## When to Use
- Dataset contains fuel receipts mixed with cover sheets, route notes, loyalty forms, promotional flyers
- Receipts use varying templates (FUEL RECEIPT, TAX INVOICE, PUMP SALE)
- TXN REF patterns vary (FUEL-{region}-{number}, may have OCR noise like OO vs 00)
- Dates may be DD/MM/YYYY or MM/DD/YYYY format
- Need to extract: batch_name, relative_path, txn_ref, date, total_amount

## Document Type Classification

**Receipt indicators** (include):
- Contains `FUEL RECEIPT`, `TAX INVOICE`, `PUMP SALE`
- Contains `TXN REF`, `TRANSACTION NO`, `REF NO`
- Contains `GRAND TOTAL`, `TOTAL AMOUNT`, `AMOUNT PAID`

**Non-receipt indicators** (exclude):
- `COVER SHEET`, `ROUTE NOTE`, `LOYALTY FORM`, `PROMOTION FLYER`
- `TOTAL SAVINGS` without `TXN REF` (savings tracker, not purchase)
- `MEMBER REF` instead of transaction reference

## Extraction Patterns

```python
# TXN REF variations with OCR noise handling
TXN_PATTERNS = [
    r'TXN REF:\s*([A-Z]+-\w+-\d+)',           # TXN REF: FUEL-N-001
    r'TRANSACTION NO:\s*([A-Z]+-\w+-\d+)',    # TRANSACTION NO: FUEL-W-001
    r'REF NO:\s*([A-Z]+-\w+-\d+)',            # REF NO: FUEL-S-0001
]

# Amount patterns (check in priority order)
AMOUNT_PATTERNS = [
    r'GRAND TOTAL:\s*\$?([\d.]+)',            # GRAND TOTAL: 64.20
    r'AMOUNT PAID:\s*\$?([\d.]+)',             # AMOUNT PAID: 54.00
    r'TOTAL AMOUNT\s*\$?([\d.]+)',             # TOTAL AMOUNT\n78.10 (split line)
    r'TOTAL\s*:\s*\$?([\d.]+)',                # fallback
]

# Date patterns (auto-detect format)
DATE_PATTERNS = [
    r'DATE:\s*([\d/-]+)',                      # DATE: 05/01/2024 or 07-02-2024
    r'SALE DATE:\s*([\d/-]+)',                 # SALE DATE: 03/18/2024
]
```

## OCR Noise Normalization

Zero vs letter O confusion is common in TXN REF:

```python
def normalize_txn_ref(raw_ref):
    """Normalize OCR noise in transaction references."""
    # FUEL-N-OO1 → FUEL-N-001 (but keep original if valid)
    # FUEL-S-OO0O1 → FUEL-S-0001
    # Don't auto-correct; extract as-is, validate uniqueness
    return raw_ref.strip()
```

## Date Format Auto-Detection

```python
def parse_date_auto(date_str):
    """Parse date with automatic MM/DD vs DD/MM detection."""
    # Try ISO first
    if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
        return date_str
    
    # Delimited formats
    m = re.match(r'(\d{2})[/-](\d{2})[/-](\d{4})', date_str)
    if not m:
        return None
    
    first, second, year = int(m.group(1)), int(m.group(2)), m.group(3)
    
    # Second value > 12 confirms MM/DD (month first)
    if second > 12:
        return f"{year}-{first:02d}-{second:02d}"  # MM/DD → YYYY-MM-DD
    # First value > 12 confirms DD/MM (day first)
    elif first > 12:
        return f"{year}-{second:02d}-{first:02d}"  # DD/MM → YYYY-MM-DD
    # Ambiguous: check context or default to DD/MM for international
    else:
        # For US fuel receipts with 03/18 pattern, second > 12 check catches it
        return f"{year}-{second:02d}-{first:02d}"  # Default DD/MM
```

## Key Decision Rules

| Pattern | Action |
|---------|--------|
| Image contains `COVER SHEET`, `ROUTE NOTE`, `LOYALTY`, `PROMOTION` | Skip - not a receipt |
| `TOTAL SAVINGS` without `TXN REF` | Skip - savings tracker, not purchase receipt |
| `MEMBER REF` present, no `TXN REF` | Skip - loyalty form, not receipt |
| Date second value > 12 | Confirm MM/DD format (e.g., 03/18 = March 18) |
| Date first value > 12 | Confirm DD/MM format |
| Amount on split line (TOTAL AMOUNT\n\n78.10) | Use DOTALL or normalize newlines |
| TXN REF has `O` vs `0` ambiguity | Extract as-is; verify uniqueness across dataset |

## Split-Line Amount Handling

```python
# OCR: "TOTAL AMOUNT\n\n78.10" or "TOTAL\n\nAMOUNT\n78.10"
normalized = re.sub(r'\n+', ' ', text)
match = re.search(r'TOTAL AMOUNT\s*\$?([\d.]+)', normalized, re.IGNORECASE)
```

## Output Schema

```python
{
    'batch_name': 'batch_north',      # Top-level directory name
    'relative_path': 'batch_north/day1/fuel_001.jpg',
    'txn_ref': 'FUEL-N-001',          # Raw extracted, OCR noise preserved
    'date': '2024-01-05',             # ISO format YYYY-MM-DD
    'total_amount': '64.20'           # String with exactly 2 decimals
}
```

## Validation Checklist

- [ ] 8 fuel receipts extracted from 12 total images (4 non-receipts filtered)
- [ ] All dates in ISO format `YYYY-MM-DD`
- [ ] All amounts as strings with exactly 2 decimal places
- [ ] Rows sorted by `relative_path` ascending
- [ ] Transaction references unique (no duplicates removed in this case)
- [ ] Sheet name: `transactions`
- [ ] Headers: `batch_name`, `relative_path`, `txn_ref`, `date`, `total_amount`

## Anti-Patterns

- **Do not** assume all images are receipts - always classify first
- **Do not** auto-correct `O` to `0` in TXN REF without validation
- **Do not** assume single date format - auto-detect with MM/DD check
- **Do not** miss split-line amounts - normalize whitespace or use DOTALL
- **Do not** include `TOTAL SAVINGS` documents - they're not purchase receipts

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Dates parsed as 2024-18-03 | Second value > 12 indicates MM/DD, not DD/MM |
| Too many rows extracted | Add document type classification - filter by TXN REF presence |
| Missing fuel receipts | Check for `PUMP SALE`, `TAX INVOICE` variants |
| Amount extraction fails | Check for split-line OCR, normalize newlines |
| TXN REF duplicates | Verify actual duplication; OCR noise may make refs appear different |

## See Also

- `../image-to-structured-excel/` for general OCR-to-Excel patterns
- `../image-to-structured-excel/references/date-parsing.md` for extended date handling
- `../image-to-structured-excel/references/amount-keyword-patterns.md` for priority-based amount extraction
