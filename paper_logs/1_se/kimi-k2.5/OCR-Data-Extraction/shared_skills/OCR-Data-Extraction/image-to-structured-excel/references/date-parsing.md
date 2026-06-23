# Date Parsing Reference

## Supported Input Formats

| Input Pattern | Output | Notes |
|-------------|--------|-------|
| `DD/MM/YYYY` | `YYYY-MM-DD` | International standard for claims/receipts |
| `MM/DD/YYYY` | `YYYY-MM-DD` | US format—verify with samples first |
| `MM/YYYY` | `YYYY-MM-01` | Use first of month |
| `MM-DD-YYYY` | `YYYY-MM-DD` | Dash-separated variant |

## Critical: Determine Format First

**Always inspect 2-3 sample images before parsing.**

```python
# Quick format detection
def detect_date_format(sample_dates):
    """Returns 'DD/MM' or 'MM/DD' based on samples."""
    for d in sample_dates:
        parts = d.split('/')
        if len(parts) == 3:
            first, second = int(parts[0]), int(parts[1])
            if first > 12:
                return 'DD/MM'
            elif second > 12:
                return 'MM/DD'
    return 'DD/MM'  # Default for international claims
```

## Claim/Invoice Specific Patterns

```python
# Travel expense claim
r'TRANSACTION DATE:\s*([\d/]+)'

# Generic date extraction
r'Date[\s:]+([\d/\-]+)'
```

## Ambiguity Resolution

- Day value > 12 → unambiguous DD/MM
- Month value > 12 → unambiguous MM/DD  
- Both ≤ 12 → context-dependent; prefer DD/MM for international receipts