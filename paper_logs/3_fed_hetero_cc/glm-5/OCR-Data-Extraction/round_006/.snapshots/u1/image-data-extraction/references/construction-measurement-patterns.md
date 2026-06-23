# Construction Measurement Form Patterns

Patterns for extracting data from construction measurement forms with line items and project aggregation.

## Form Structure

Construction measurement forms typically contain:
- Header: Project code, date, form identifier
- Line items table: Description, quantity, unit of measure, unit price
- Footer: Project total (cumulative, NOT to be summed across forms)

## Column Requirements

### Details Sheet
| Column | Type | Notes |
|--------|------|-------|
| filename | string | Original image filename |
| project_code | string | Project identifier (e.g., PROJ-2024-001) |
| item_description | string | Description of work item/material |
| quantity | float | Quantity measured (raw float, NOT formatted) |
| unit_price | float | Unit price as raw number (NOT formatted) |

### Summary Sheet
| Column | Type | Notes |
|--------|------|-------|
| project_code | string | Project identifier |
| date | string | ISO format YYYY-MM-DD (**latest** form date for this project) |
| total_amount | float | Total from the **latest** form for this project (NOT summed) |

## Project Code Patterns

```python
PROJECT_CODE_PATTERNS = [
    r'(PROJ-\d{4}-\d{3})',      # PROJ-2024-001
    r'(PROJECT[-_]\d{4}[-_]\d+)', # PROJECT-2024-001 or PROJECT_2024_1
    r'(P\d{4}-\d{3})',          # P2024-001
]

def extract_project_code(text):
    for pattern in PROJECT_CODE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None
```

## Line Item Extraction

### Pattern Recognition
Construction forms often have tabular data with:
- Item description (text)
- Quantity (number, possibly with unit)
- Unit price (currency amount)

**CRITICAL: Disambiguate quantity from item codes**
- "C30" or "M20" are concrete/steel grades, NOT quantities
- Quantity is a standalone integer (1-9999 range) NOT prefixed by letters

```python
def extract_line_items(text):
    """Extract line items from construction measurement form."""
    items = []
    lines = text.split('\n')
    
    # Skip patterns for headers/footers
    skip_keywords = ['ITEM', 'DESCRIPTION', 'QTY', 'QUANTITY', 'PRICE', 'TOTAL', 'PROJECT', 'CONSTRUCTION', 'MEASUREMENT', 'FORM']
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Skip header/footer lines (lines with keywords but no prices)
        if any(kw in line.upper() for kw in skip_keywords) and not re.search(r'\d+\.\d{2}', line):
            continue
        
        # Pattern: description + quantity + unit price
        # Price typically at end of line with decimal (e.g., 150.00, 234.50)
        price_match = re.search(r'[\$]?([\d,]+\.\d{2})\s*$', line)
        if price_match:
            price = float(price_match.group(1).replace(',', ''))
            remaining = line[:price_match.start()].strip()
            
            # Quantity: number before price, NOT part of item code
            # Pattern: extract last standalone number that is NOT preceded by letters (like C30, M20)
            qty_match = re.search(r'(\d+)\s*(?:m[³²]?|kg|pcs|units?|tons?)?\s*$', remaining, re.IGNORECASE)
            if qty_match:
                qty_candidate = qty_match.group(1)
                # Verify it's NOT part of an item code (preceded by letter)
                before_qty = remaining[:qty_match.start()].strip()
                if before_qty and before_qty[-1].isalpha():
                    # This is part of code like "C30", skip it, look for real quantity
                    continue
                
                qty = float(qty_candidate)
                desc = remaining[:qty_match.start()].strip()
                
                # Clean description - normalize whitespace
                desc = re.sub(r'\s+', ' ', desc)
                
                if desc and qty > 0 and price > 0:
                    items.append({
                        'description': desc,
                        'quantity': qty,
                        'unit_price': price
                    })
    
    return items
```

## Summary Aggregation Logic (CRITICAL)

**WRONG approaches:**
- Summing totals across all forms for a project
- Using earliest date for summary

**CORRECT approach:**
```python
def aggregate_by_project(forms):
    """Aggregate forms by project - use latest form's date and total."""
    project_latest = {}
    
    for form in forms:
        proj = form['project_code']
        if proj is None:
            continue
        
        # Store the form with the latest date for each project
        if proj not in project_latest:
            project_latest[proj] = form
        elif form['date'] and project_latest[proj]['date']:
            if form['date'] > project_latest[proj]['date']:
                project_latest[proj] = form  # Replace with later form
    
    # Build summary - one row per project using the latest form's values
    summary = []
    for project_code in sorted(project_latest.keys()):
        latest_form = project_latest[project_code]
        summary.append({
            'project_code': project_code,
            'date': latest_form['date'],
            'total_amount': latest_form['total_amount']  # From the form itself, NOT summed
        })
    
    return summary
```

**Why latest-form logic:**
- Construction totals are cumulative measurements
- The latest form already contains the cumulative total
- Summing across forms would over-count (double or triple count)

## Multi-Sheet Excel Output

```python
from openpyxl import Workbook

def create_construction_output(details_records, summary_records, output_path):
    """Create Excel with details and summary sheets."""
    wb = Workbook()
    
    # Details sheet
    ws_details = wb.active
    ws_details.title = 'details'
    ws_details.append(['filename', 'project_code', 'item_description', 'quantity', 'unit_price'])
    
    for record in sorted(details_records, key=lambda x: x['filename']):
        ws_details.append([
            record['filename'],
            record['project_code'],
            record['item_description'],
            record['quantity'],
            record['unit_price']  # Raw float - DO NOT format
        ])
    
    # Summary sheet
    ws_summary = wb.create_sheet('summary')
    ws_summary.append(['project_code', 'date', 'total_amount'])
    
    for record in summary_records:
        ws_summary.append([
            record['project_code'],
            record['date'],
            record['total_amount']  # Raw float - DO NOT format
        ])
    
    wb.save(output_path)
```

## Common OCR Errors in Construction Forms

| Error | Correction | Context |
|-------|-----------|---------|
| `m³` → `m3` or `m?` | Normalize unit | Quantity extraction |
| `m²` → `m2` or `m?` | Normalize unit | Quantity extraction |
| `O` → `0` | Digit zero | Prices, quantities |
| `l` → `1` | Digit one | Prices, quantities |
| `C30` misread as quantity | Filter letter-prefixed numbers | Item code vs quantity |
| Split descriptions | Multi-line handling | Item descriptions |

## Anti-Patterns

- **Do NOT sum totals across forms** - totals are cumulative per form
- **Do NOT use earliest date** - use latest form's date for summary
- **Do NOT mistake item codes for quantities** - "C30" is a grade, not a quantity
- **Do NOT format amounts as strings** - pass raw floats to openpyxl
- **Do NOT hardcode values** - always use OCR automation
- **Do NOT flatten multi-item forms** - each item gets its own row in details

## Validation Rules

1. Details row count = images × items per form
2. Summary row count = unique project codes
3. Summary uses latest form's date and total (NOT sum)
4. Dates normalized to ISO YYYY-MM-DD
5. Amounts are raw floats (no formatting)
6. No item codes mistaken as quantities