# OCR Table Extraction Patterns

## Handling OCR Artifacts in Tabular Data

Common OCR corruption patterns and fixes:

| Corruption | Cause | Fix |
|------------|-------|-----|
| `m?` or `=m =` | Superscript/cubic meter symbol | Normalize: `re.sub(r'm\?|=m\s*=?', 'm3', text)` |
| `=` before numbers | Bullet or formatting artifact | Strip: `re.sub(r'=(?=\d)', '', text)` |
| Split lines in tables | Row breaks mid-cell | Normalize whitespace, parse flexibly |
| Extra newlines | Layout preservation | `re.sub(r'\n+', '\n', text)` |

## Multi-Line Item Parsing

Construction forms and tables often have variable column alignment:

```python
def parse_table_items(text, min_columns=4):
    """
    Parse tabular data from OCR text with flexible column detection.
    
    Strategy:
    1. Normalize whitespace artifacts
    2. Skip header/footer lines
    3. Require minimum numeric/price columns
    4. Extract by position or regex
    """
    # Normalize common OCR artifacts
    text = re.sub(r'm\?|=m\s*=?', 'm3', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    
    items = []
    for line in text.split('\n'):
        line = line.strip()
        # Skip headers, footers, empty lines
        if not line or any(skip in line.upper() for skip in 
                          ['ITEM', 'DESCRIPTION', 'PROJECT TOTAL', '---']):
            continue
        
        # Look for price pattern at end
        price_match = re.search(r'\$?([\d,.]+)\s*$', line)
        if not price_match:
            continue
            
        # Extract preceding tokens
        tokens = line[:price_match.start()].strip().split()
        if len(tokens) >= 2:
            # description = all tokens except last 2 (qty, unit)
            # quantity = tokens[-2] if numeric
            # unit = tokens[-1]
            # price = price_match.group(1)
            items.append(parse_tokens(tokens, price_match.group(1)))
    
    return items
```

## Validation: Expected Row Count

Always verify extracted row counts match expectations:

```python
# Before: brittle - stops at first failure
for img in images:
    items = extract(img)
    if len(items) != EXPECTED_ITEMS_PER_FORM:
        print(f"Warning: {img} has {len(items)} items, expected {EXPECTED_ITEMS}")
        # Continue anyway or retry with different parsing
```

## Pattern Priority for Price Extraction

When multiple prices exist in a row:
1. Last price on line (typically unit price, not total)
2. Price preceded by `$` or space-dollar
3. Price with 2 decimal places

## Anti-Patterns

- **Don't** assume fixed column positions - OCR shifts horizontally
- **Don't** rely on unit symbols being exact - normalize `m?` → `m3`
- **Don't** parse only by split position - use regex for prices
- **Don't** assume consistent line breaks - tables may wrap
