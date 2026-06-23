# Tabular Form Extraction Patterns

Extract structured data from form images containing repeating line items (tables, measurement forms, invoices with item lists).

## Trigger Patterns
- Forms with repeating line items per image
- Quantity × Unit Price = Total calculations
- Multiple items per document that need individual rows
- Need both detail and summary output sheets

## Line Item Extraction Strategy

### 1. Identify Item Types with Priority Ordering
More specific patterns first to avoid partial matches:

```python
ITEM_PATTERNS = [
    # (regex_pattern, normalized_name)
    (r'(Concrete\s+C\d+)', 'Concrete C30'),  # C30 extracted separately if needed
    (r'(Steel\s+reinforcement)', 'Steel reinforcement'),
    (r'(Brick\s+work)', 'Brick work'),
    # Generic fallback last
    (r'(\w+(?:\s+\w+){0,3})', None),  # Up to 4 words
]
```

### 2. Extract Numbers with Role Disambiguation
Critical: Distinguish quantity from unit price from total/line number:

```python
def extract_item_details(line, item_name):
    """Extract qty and price from item line."""
    # Find all numbers
    numbers = re.findall(r'\d+(?:\.\d+)?', line)
    
    # Find price by pattern ($X.XX or ends with .XX)
    price_match = re.search(r'\$?(\d+\.\d{2})\b', line)
    price = float(price_match.group(1)) if price_match else None
    
    # Quantity: remaining number in reasonable range (1-9999)
    qty = None
    for num_str in numbers:
        if price_match and num_str == price_match.group(1).replace('.', ''):
            continue  # Skip the price number
        val = float(num_str)
        if 0 < val < 10000:
            qty = int(val)
            break
    
    return {'description': item_name, 'quantity': qty, 'unit_price': price}
```

### 3. Multi-Line Item Handling
Some items split across OCR lines:

```python
def extract_multiline_items(text):
    """Handle items where description and numbers are on different lines."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    items = []
    
    for i, line in enumerate(lines):
        # Check if line is an item description (no numbers or only item code)
        if is_item_description(line) and not has_amount(line):
            # Look at next 1-2 lines for quantities/prices
            for j in range(i+1, min(i+3, len(lines))):
                numbers = extract_numbers(lines[j])
                if len(numbers) >= 2:
                    items.append(parse_item_line(line + ' ' + lines[j]))
                    break
    return items
```

## Multi-Sheet Output Pattern

Common for measurement forms, bills of materials, time sheets:

### Sheet 1: Details (one row per line item)
```python
details = []
for img_path in image_paths:
    form_data = extract_form(img_path)
    for item in form_data['items']:
        details.append({
            'filename': os.path.basename(img_path),
            'project_code': form_data['project_code'],
            'item_description': item['description'],
            'quantity': item['quantity'],
            'unit_price': item['unit_price']
        })
```

### Sheet 2: Summary (aggregated by project/code)
```python
from collections import defaultdict

projects = defaultdict(lambda: {'dates': [], 'totals': []})
for img_path in image_paths:
    form_data = extract_form(img_path)
    code = form_data['project_code']
    projects[code]['dates'].append(form_data['date'])
    projects[code]['totals'].append(form_data['total'])

# Latest date per project, sum or latest total
summary = []
for code, data in sorted(projects.items()):
    latest_date = max(data['dates'])
    latest_total = data['totals'][-1]  # Or sum if cumulative
    summary.append({
        'project_code': code,
        'date': latest_date,
        'total_amount': latest_total
    })
```

## Common OCR Errors in Forms

| Error Pattern | Correction Strategy |
|-------------|---------------------|
| Quantity "30" from "C30" in same line | Filter out numbers that are part of item codes (preceded by letter) |
| Item description split from values | Line lookahead strategy |
| Multiple prices (unit vs total) | Prefer rightmost with decimal, or context by "@" or "×" |
| Line numbers in margin | Ignore numbers at start of line if followed by item description |

## Validation Checklist

- [ ] Item count matches expected items per form × form count
- [ ] All quantities are integers in reasonable range (1-9999)
- [ ] Unit prices are raw floats (no fixed decimal formatting)
- [ ] No prices mistaken for quantities (check magnitude)
- [ ] Summary aggregates correctly (latest date, proper total)
- [ ] Row order: sorted by filename, items in extraction order
- [ ] No duplicate rows from same line being parsed twice

## Anti-Patterns

- **Don't** use simple `re.findall(r'\d+')` - loses number context
- **Don't** assume first number is quantity - could be line number or item code
- **Don't** hardcode item names - use pattern matching with normalization
- **Don't** sum totals for summary if data shows cumulative (latest-wins instead)
- **Don't** write formatted strings (`"150.00"`) to Excel - use raw float, format cells instead
