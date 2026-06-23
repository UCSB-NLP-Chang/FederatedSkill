# TXN Reference Patterns

## Fuel Receipt TXN REF Variations

| Format | Example | Pattern | Notes |
|--------|---------|---------|-------|
| Standard | FUEL-N-001 | `([A-Z]+-[A-Z]+-\d+)` | Region + sequence |
| With zeros | FUEL-N-OO1 | `([A-Z]+-[A-Z]+-\w+)` | Letter O vs zero |
| Extended | FUEL-S-OO0O1 | `([A-Z]+-[A-Z]+-\w+)` | Mixed O/0 noise |
| West region | FUEL-W-001 | `([A-Z]+-W-\d+)` | West-specific |

## OCR Noise in References

Common corruptions in TXN REF extraction:

```python
# Raw OCR examples:
# "FUEL-N-OO1"   - letter O instead of zero
# "FUEL-S-OO0O1" - multiple O/0 confusions
# "FUEL-N-OO02"  - O instead of 0 in middle

# Pattern handles all variants:
r'TXN REF:\s*([A-Z]+-[A-Z]+-\w+)'
# \w captures [A-Za-z0-9_]
```

## Alternative REF Labels

```python
REF_LABEL_PATTERNS = [
    r'TXN REF:\s*([\w-]+)',
    r'TRANSACTION NO:\s*([\w-]+)',
    r'TRANSACTION REF:\s*([\w-]+)',
    r'REF NO:\s*([\w-]+)',
    r'REFERENCE:\s*([\w-]+)',
]
```

## Validation

- Extract raw value without normalization
- Check uniqueness across all extracted receipts
- Log ambiguous refs for manual review
