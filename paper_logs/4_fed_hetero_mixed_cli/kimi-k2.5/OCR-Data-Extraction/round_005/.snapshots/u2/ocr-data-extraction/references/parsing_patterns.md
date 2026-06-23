# Date & Price Parsing Patterns

## Date Disambiguation
- `DD/MM/YYYY` vs `MM/DD/YYYY`: Check the first number. If `> 12`, it is the day. If both `<= 12`, context or locale dictates. Default to `DD/MM` for international/Malaysian/European contexts.
- `MM/YYYY`: Implies first day of month. Normalize to `YYYY-MM-01`.
- `DD-MM-YYYY` vs `DD/MM/YYYY`: Treat separators interchangeably.

## Invoice Total Keyword Priority
When extracting totals from invoices, OCR captures multiple line items. Use this priority order to select the correct total:
1. `GRAND TOTAL`
2. `TOTAL DUE`
3. `TOTAL`
Explicitly exclude lines containing: `SUBTOTAL`, `TAX`, `VAT`, `SHIPPING`, `DISCOUNT`, `AMOUNT DUE` (unless specified).
If multiple matches exist, pick the highest priority keyword.

### Python Pattern
```python
import re

def extract_invoice_total(text):
    """Extract total amount prioritizing GRAND TOTAL > TOTAL DUE > TOTAL."""
    lines = text.split('\n')
    total_keywords = [
        (r'GRAND\s*TOTAL', 1),
        (r'TOTAL\s*DUE', 2),
        (r'\bTOTAL\b', 3)
    ]
    exclude_keywords = ['SUBTOTAL', 'TAX', 'VAT', 'SHIPPING', 'DISCOUNT']

    best_match = None
    best_priority = 99

    for line in lines:
        line_upper = line.upper()
        if any(kw in line_upper for kw in exclude_keywords):
            continue

        for pattern, priority in total_keywords:
            if re.search(pattern, line_upper):
                if priority < best_priority:
                    price_match = re.search(r'(?:RM|MYR|\$|€|£)?\s*([\d,]+\.?\d*)', line)
                    if price_match:
                        best_match = float(price_match.group(1).replace(',', ''))
                        best_priority = priority
                break
    return best_match
```

## Multi-Line Keyword Matching

OCR frequently splits compound keywords across lines with blank lines in between, or separates keywords from their values with blank lines.

### Common Split Patterns
```
TOTAL

DUE: 120.75
```
```
PAY THIS AMOUNT

1234.56
```

### Python Pattern
```python
def extract_amount_multiline(text, keywords, max_gap=4):
    """
    Extract amount handling multi-line keywords and blank line gaps.

    Args:
        text: OCR text
        keywords: List of keywords in priority order (e.g., ['PAY THIS AMOUNT', 'AMOUNT DUE', 'TOTAL DUE'])
        max_gap: Maximum lines to search after keyword for value
    """
    lines = text.strip().split('\n')

    for kw in keywords:
        parts = kw.upper().split()

        for i, line in enumerate(lines):
            line_upper = line.strip().upper()

            # Check if first part of keyword is on this line
            if parts[0] in line_upper:
                # Try to find remaining parts in next few lines
                found_all = True
                target_line_idx = i

                if len(parts) > 1:
                    # Look for remaining parts
                    for j in range(i + 1, min(i + max_gap, len(lines))):
                        if all(p in lines[j].upper() for p in parts[1:]):
                            target_line_idx = j
                            break
                    else:
                        # Not all parts found, check if amount is on current line
                        m = re.search(r'[\$]?([\d,]+\.\d{2})', line)
                        if m:
                            return m.group(1)
                        continue

                # Extract amount from target line or subsequent lines
                m = re.search(r'[\$]?([\d,]+\.\d{2})', lines[target_line_idx])
                if m:
                    return m.group(1)

                # Look in next few lines for amount
                for k in range(target_line_idx + 1, min(target_line_idx + max_gap, len(lines))):
                    m = re.search(r'[\$]?([\d,]+\.\d{2})', lines[k])
                    if m:
                        return m.group(1)

    return None
```

## Price Extraction
- Strip currency prefixes/suffixes: `$`, `RM`, `MYR`, `€`, `£`, `EACH`, `PER`.
- Handle thousands separators: Remove commas before parsing.
- Regex: `(?:RM|MYR|\$|€)?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)`
- Format to 2 decimal places only if the task requires string output; otherwise, keep raw floats.

## Common OCR Artifacts
- `0` ↔ `O`, `1` ↔ `I` or `l`, `5` ↔ `S`, `8` ↔ `B`.
- Dashes vs slashes: `-` vs `/` vs `.`. Normalize to `-` for ISO dates.
- Missing spaces: `RM10.99` vs `RM 10.99`. Regex should allow optional whitespace.
