# Date & Price Parsing Patterns

## Date Disambiguation
- `DD/MM/YYYY` vs `MM/DD/YYYY`: Check the first number. If `> 12`, it is the day. If both `<= 12`, context or locale dictates. Default to `DD/MM` for international/Malaysian/European contexts.
- `MM/YYYY`: Implies first day of month. Normalize to `YYYY-MM-01`.
- `DD-MM-YYYY` vs `DD/MM/YYYY`: Treat separators interchangeably.

## Keyword Specificity for Amount Extraction (CRITICAL)

**Pitfall**: Using short or common substrings as keywords causes false matches in OCR text.

### Example of the Problem
```python
# WRONG: 'DIT' matches 'CREDIT MEMO' text
keywords = ['CREDIT AMOUNT', 'DIT AMOUNT', 'REFUND TOTAL', 'TOTAL CREDIT', 'DIT']
# OCR text: "CREDIT MEMO\nCREDIT NO: CR-G-001\nTOTAL CREDIT: 50.00"
# 'DIT' matches position 3 in 'CREDIT MEMO' → wrong extraction
```

### Solution: Use Only Complete, Specific Keywords
```python
# CORRECT: Only complete keywords that won't match substrings
keywords = ['CREDIT AMOUNT', 'DIT AMOUNT', 'REFUND TOTAL', 'TOTAL CREDIT']
```

### Rules for Keyword Selection
1. **Minimum length**: Keywords should be at least 4-5 characters to avoid accidental substring matches
2. **Uniqueness**: Prefer compound keywords (e.g., `TOTAL CREDIT` over just `CREDIT`)
3. **Test against common OCR outputs**: Check that keywords don't appear in document headers, labels, or other non-target text
4. **Document-type-specific lists**: Different document types need different keyword priorities:
   ```python
   KEYWORDS_BY_TYPE = {
       'purchase': ['GRAND TOTAL', 'TOTAL DUE', 'AMOUNT DUE'],
       'credit': ['CREDIT AMOUNT', 'REFUND TOTAL', 'TOTAL CREDIT'],
       'utility': ['PAY THIS AMOUNT', 'CURRENT CHARGES', 'AMOUNT DUE'],
   }
   ```

## Word Boundary & Split Keyword Handling (CRITICAL)

### Do Not Match Partial Keywords Without Boundaries
OCR text often contains words that share prefixes with your target keywords. Matching without word boundaries causes false positives.

**Example failure**: Searching for `CREDIT NO` in text containing `CREDIT NOTE` will match `CREDIT NO` (the first 9 characters of `CREDIT NOTE`) and capture `TE` as the reference value.

**Fix**: Use negative lookahead after short keywords to ensure they are not followed by letters:
```python
# WRONG: matches "CREDIT NOTE" and captures "TE"
r"(?i)credit\s+no\.?\s*[:\-]?\s*([A-Za-z][A-Za-z0-9\-]+)"

# CORRECT: rejects "CREDIT NOTE" because "NO" is followed by "T"
r"(?i)credit\s+no\.?)(?![A-Za-z])\s*[:\-]?\s*([A-Za-z][A-Za-z0-9\-]+)"
```

Apply this pattern to all short keyword matches: `receipt no`, `credit no`, `invoice no`, `order no`, `reference`, etc.

### Handle Split OCR Keywords
OCR frequently fragments compound keywords across lines with blank lines or other content between parts:

| Intended Keyword | OCR Fragmentation | Solution |
|------------------|-------------------|----------|
| `CREDIT NO` | `CRE` ... `DIT NO:` | Add fallback pattern for `DIT NO` |
| `TOTAL CREDIT` | `TOTAL CRE]` ... `DIT:` | Fix artifacts (`CRE]` → `CREDIT`) or search for partial match |
| `CREDIT AMOUNT` | `DIT AMOUNT:` | Add fallback pattern for `DIT AMOUNT` |

**Pattern**: After primary keyword search fails, search for common fragment patterns:
```python
# Primary pattern
r"(?i)credit\s+no\.?)(?![A-Za-z])\s*[:\-]?\s*([A-Za-z][A-Za-z0-9\-]+)"
# Fallback for split keyword
r"(?i)dit\s+no\.?)(?![A-Za-z])\s*[:\-]?\s*([A-Za-z][A-Za-z0-9\-]+)"
```

### OCR Artifact Correction Timing
Apply character substitution **after** extracting a value, not to the full OCR text. This avoids corrupting legitimate words.

```python
def fix_ocr_code(code: str) -> str:
    """Fix common OCR confusions in alphanumeric codes (IDs, refs, etc.)."""
    code = code.upper()
    code = code.replace('O', '0').replace('l', '1').replace('I', '1')
    code = code.replace('S', '5').replace('B', '8')
    return code
```

**Do not** apply these substitutions to the full OCR text before keyword matching, as it will corrupt words like `NOTE` → `N0TE` or `CREDIT` → `CREDI7`.

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
