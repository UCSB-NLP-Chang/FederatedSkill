# Document Type Classification

## Receipt Types (Target)

| Type | Indicators | Fields Present |
|------|-----------|----------------|
| FUEL RECEIPT | Header text "FUEL RECEIPT" | TXN REF, DATE, GRAND TOTAL |
| TAX INVOICE | Header "TAX INVOICE" | REF NO, SALE DATE, AMOUNT PAID |
| PUMP SALE | Header "PUMP SALE" | TRANSACTION NO, DATE, TOTAL AMOUNT |

## Non-Receipt Types (Filter)

| Type | Indicators | Why Filtered |
|------|-----------|--------------|
| COVER SHEET | "COVER SHEET" header | Metadata, no transaction |
| ROUTE NOTE | "ROUTE NOTE" header | Operational note, no purchase |
| LOYALTY FORM | "LOYALTY FORM", "MEMBER REF" | Membership data, not purchase |
| PROMOTION FLYER | "PROMOTION FLYER", "OFFER REF" | Marketing, not transaction |

## Classification Logic

```python
def is_fuel_receipt(text):
    """Determine if OCR text is a fuel purchase receipt."""
    text_upper = text.upper()
    
    # Must have transaction reference indicator
    has_txn_ref = any(re.search(p, text_upper) for p in [
        r'TXN REF',
        r'TRANSACTION NO',
        r'REF NO',
        r'TRANSACTION REF',
    ])
    
    # Must have amount indicator
    has_amount = any(re.search(p, text_upper) for p in [
        r'GRAND TOTAL',
        r'TOTAL AMOUNT',
        r'AMOUNT PAID',
        r'TOTAL DUE',
    ])
    
    # Must NOT be non-receipt type
    non_receipt = any(x in text_upper for x in [
        'COVER SHEET',
        'ROUTE NOTE', 
        'LOYALTY FORM',
        'PROMOTION FLYER',
        'TOTAL SAVINGS',  # Without TXN REF
    ])
    
    return has_txn_ref and has_amount and not non_receipt
```

## Edge Cases

- Document with `TOTAL SAVINGS` + `TXN REF` → **Receipt** (rare but possible)
- Document with `MEMBER REF` only → **Non-receipt** (loyalty card)
- Document with `OFFER REF` → **Non-receipt** (promotion)
