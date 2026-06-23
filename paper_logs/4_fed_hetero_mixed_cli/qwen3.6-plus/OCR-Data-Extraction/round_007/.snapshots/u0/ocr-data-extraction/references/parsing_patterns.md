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

## Multi-Line Keyword & Value Extraction

OCR frequently splits compound keywords across lines with blank lines in between, or separates keywords from their values with one or more blank lines.

### Common Split Patterns
```
TOTAL

DUE: 120.75
```
```
PAY THIS AMOUNT

1234.56
```

### Robust Python Pattern (handles blank lines correctly)
```python
def extract_value_after_keyword(text, keywords, max_lines=5):
    """
    Extract value that may appear on same line or subsequent non-blank lines.
    
    Args:
        text: OCR text
        keywords: List of keywords in priority order
        max_lines: Maximum lines to search after keyword
    
    Returns:
        Extracted value string or None
    """
    lines = text.split('\n')
    
    for kw in keywords:
        kw_upper = kw.upper()
        for i, line in enumerate(lines):
            line_upper = line.strip().upper()
            if kw_upper in line_upper:
                # Check same line first
                m = re.search(r'[\$]?([\d,]+\.\d{2})', line)
                if m:
                    return m.group(1)
                
                # Search subsequent non-blank lines
                lines_searched = 0
                for j in range(i + 1, len(lines)):
                    next_line = lines[j].strip()
                    if not next_line:  # Skip blank lines
                        continue
                    lines_searched += 1
                    if lines_searched > max_lines:
                        break
                    m = re.search(r'[\$]?([\d,]+\.\d{2})', next_line)
                    if m:
                        return m.group(1)
    return None
```

**Critical**: Never mix indices between raw `lines` and a filtered `nonblank_lines` list. Either iterate over raw lines and skip blanks inline, or track the correct index in the filtered list.

## Price Extraction
- Strip currency prefixes/suffixes: `$`, `RM`, `MYR`, `€`, `£`, `EACH`, `PER`.
- Handle thousands separators: Remove commas before parsing.
- Regex: `(?:RM|MYR|\$|€)?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)`
- Format to 2 decimal places only if the task requires string output; otherwise, keep raw floats.

## Tabular Line-Item Parsing
Construction forms, measurement sheets, and invoices often render tables as single lines with noisy separators (`=`, `~`, `§`, `«`, `-`).

### Artifact Cleaning
```python
def clean_ocr_line(line: str) -> str:
    """Remove common OCR table artifacts before parsing."""
    line = re.sub(r'[=~§«»\-—–]+(?=\s*(?:\$|\d))', ' ', line)
    line = re.sub(r'[=~§«»]+', '', line)
    return line.strip()
```

### Robust Line Parser
```python
def parse_item_line(line: str) -> dict | None:
    line = clean_ocr_line(line)
    # Skip headers/empty
    if not line or any(kw in line.upper() for kw in ['ITEM', 'DESCRIPTION', 'QTY', 'UNIT', 'PRICE']):
        return None

    # Strategy 1: Regex capture (description, qty, skip units, price)
    m = re.match(
        r'^([A-Za-z][A-Za-z0-9\s,./\-\(\)]*?)\s+'
        r'(\d+(?:\.\d+)?)\s+'
        r'.*?'
        r'\$?\s*([\d,]+\.\d{2})\s*$',
        line
    )
    if m:
        return {
            'description': m.group(1).strip(),
            'quantity': float(m.group(2)),
            'unit_price': float(m.group(3).replace(',', ''))
        }

    # Strategy 2: Fallback to number positions
    nums = [(m.start(), float(m.group().replace(',', ''))) for m in re.finditer(r'[\d,]+\.?\d*', line)]
    if len(nums) >= 2:
        desc = line[:nums[0][0]].strip()
        return {
            'description': desc,
            'quantity': nums[-2][1],
            'unit_price': nums[-1][1]
        }
    return None
```

## Quantity Extraction from Line Items

When extracting quantities from lines where item names contain numbers (e.g., "Concrete C30 50 m³ $150.00"):

### Pitfall
Naive regex `\d+` will match "30" from "C30" instead of the actual quantity "50".

### Solution: Context-Aware Patterns
Match quantities AFTER the item name, not just any number on the line.

```python
def extract_quantity_with_context(line, item_name):
    """
    Extract quantity from a line, matching AFTER the item name.
    
    Args:
        line: OCR line like "Concrete C30 50 m³ $150.00"
        item_name: Item identifier like "Concrete C30" or "Steel reinforcement"
    
    Returns:
        Quantity as string, or None
    """
    # Escape special regex chars in item name
    escaped_name = re.escape(item_name)
    
    # Pattern: item name followed by space, then capture the quantity
    # Look for number AFTER the item name
    pattern = rf'{escaped_name}\s+(\d+)'
    match = re.search(pattern, line, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None

# Example usage for known item patterns
ITEM_PATTERNS = [
    ('Concrete C30', r'C30\s+(\d+)'),           # "Concrete C30 50" → 50
    ('Steel reinforcement', r'reinforcement\s+(\d+)'),  # "Steel reinforcement 100" → 100
    ('Brick work', r'work\s+(\d+)'),           # "Brick work 200" → 200
]

def extract_line_items(text):
    """Extract line items with quantities, handling embedded numbers in names."""
    items = []
    for line in text.split('\n'):
        for item_name, pattern in ITEM_PATTERNS:
            if item_name.lower() in line.lower():
                qty_match = re.search(pattern, line, re.IGNORECASE)
                price_match = re.search(r'\$(\d+\.\d{2})', line)
                if qty_match and price_match:
                    items.append({
                        'description': item_name,
                        'quantity': qty_match.group(1),
                        'unit_price': price_match.group(1)
                    })
    return items
```

## Multi-Item Deduplication Across OCR Strategies

When using multiple OCR strategies (different PSM modes, preprocessing), the same items may be extracted multiple times.

### Python Pattern
```python
def deduplicate_items(items, key_fields=('description',)):
    """
    Deduplicate items extracted from multiple OCR strategies.
    
    Args:
        items: List of item dicts with fields like description, quantity, unit_price
        key_fields: Tuple of field names to use for uniqueness check
    
    Returns:
        Deduplicated list of items (first occurrence kept)
    """
    seen = set()
    unique_items = []
    for item in items:
        key = tuple(item.get(f, '') for f in key_fields)
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    return unique_items

# Usage with multi-strategy OCR
def extract_items_multi_strategy(img_path):
    all_items = []
    for strategy in ['default', 'preprocessed', 'psm6', 'psm11']:
        text = ocr_with_strategy(img_path, strategy)
        items = extract_line_items(text)
        all_items.extend(items)
    
    return deduplicate_items(all_items, key_fields=('description',))
```

## Common OCR Artifacts
- `0` ↔ `O`, `1` ↔ `I` or `l`, `5` ↔ `S`, `8` ↔ `B`.
- Dashes vs slashes: `-` vs `/` vs `.`. Normalize to `-` for ISO dates.
- Missing spaces: `RM10.99` vs `RM 10.99`. Regex should allow optional whitespace.
