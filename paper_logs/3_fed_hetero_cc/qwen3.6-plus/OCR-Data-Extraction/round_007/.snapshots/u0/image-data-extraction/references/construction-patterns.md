# Construction Measurement Form Patterns

Patterns for extracting line-item data from construction measurement forms and outputting multi-sheet Excel with correct project aggregation.

## Trigger Conditions
- Forms contain repeating line items (tabular data)
- Multiple items per document that need individual rows
- Output requires both details (line items) and summary (project-level) sheets

## Form Structure

Construction measurement forms typically contain:
- Header: Project code (`PROJ-YYYY-NNN`), date, form identifier
- Line items table: Description, quantity, unit of measure, unit price
- Footer: Cumulative total amount

## Project Code Pattern
```python
PROJECT_CODE_PATTERN = r'(PROJ-\d{4}-\d{3})'
# Examples: PROJ-2024-001, PROJ-2023-015

def extract_project_code(text):
    match = re.search(PROJECT_CODE_PATTERN, text, re.IGNORECASE)
    return match.group(1).upper() if match else None
```

## Line Item Extraction

### Quantity vs Price Disambiguation
Critical: Distinguish quantity (integer, 1-9999) from price (decimal, typically 2 places) from item codes (letter+number like C30):

```python
def extract_line_items(text):
    """Extract line items with quantity/price disambiguation."""
    items = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # Skip patterns for headers/footers
    skip_keywords = ['ITEM', 'DESC', 'QTY', 'PRICE', 'TOTAL', 'PROJECT', 'DATE']
    
    for line in lines:
        # Skip header lines
        if any(kw in line.upper() for kw in skip_keywords) and not re.search(r'\d+\.\d{2}', line):
            continue
        
        # Pattern: description + quantity + unit price
        # Price has decimal: \d+\.\d{2} at end of line
        price_match = re.search(r'[\$]?([\d,]+\.\d{2})\s*$', line)
        if price_match:
            price = float(price_match.group(1).replace(',', ''))
            remaining = line[:price_match.start()].strip()
            
            # Quantity: integer in reasonable range (NOT item codes like C30)
            # Item codes have letter prefix (C30, M20, etc.) - these are NOT quantities
            qty_match = re.search(r'(\d{1,4})\s*(?:m[³²]?|kg|pcs|units?|tons?)?\s*$', remaining, re.IGNORECASE)
            if qty_match:
                # Check it's not part of an item code (preceded by letter)
                before_qty = remaining[:qty_match.start()]
                if not re.search(r'[A-Z]\s*$', before_qty, re.IGNORECASE):  # Not like "C 30"
                    qty = int(qty_match.group(1))
                    desc = before_qty.strip()
                    
                    # Clean description: remove trailing codes like C30, M20
                    desc = re.sub(r'\s+[A-Z]\d+\s*$', '', desc, flags=re.IGNORECASE).strip()
                    
                    if desc and qty > 0 and price > 0:
                        items.append({
                            'description': desc,
                            'quantity': qty,
                            'unit_price': price
                        })
    
    return items
```

## Multi-Sheet Excel Output

### Details Sheet
One row per line item per image:
```python
from openpyxl import Workbook

wb = Workbook()
ws_details = wb.active
ws_details.title = 'details'
ws_details.append(['filename', 'project_code', 'item_description', 'quantity', 'unit_price'])

for record in sorted(details_records, key=lambda x: x['filename']):
    ws_details.append([
        record['filename'],
        record['project_code'],
        record['item_description'],
        record['quantity'],
        record['unit_price']  # Raw float - NO rounding
    ])
```

### Summary Sheet - CORRECT Aggregation Logic
**Critical**: Use LATEST form's date and total for each project, NOT sum across forms:

```python
from collections import defaultdict

def aggregate_projects(forms):
    """Aggregate by project: latest form's date and total_amount."""
    project_latest = {}
    
    for form in forms:
        proj = form['project_code']
        if proj:
            # Keep the form with the LATEST date for each project
            if proj not in project_latest:
                project_latest[proj] = form
            elif form['date'] and form['date'] > project_latest[proj]['date']:
                project_latest[proj] = form
    
    # Build summary rows
    summary = []
    for proj in sorted(project_latest.keys()):
        form = project_latest[proj]
        summary.append({
            'project_code': proj,
            'date': form['date'],
            'total_amount': form['total_amount']  # From form itself, NOT computed
        })
    
    return summary

# Write summary sheet
ws_summary = wb.create_sheet('summary')
ws_summary.append(['project_code', 'date', 'total_amount'])

for record in summary_records:
    ws_summary.append([
        record['project_code'],
        record['date'],
        record['total_amount']  # Raw float - NO rounding
    ])
```

**Anti-Pattern - DO NOT DO THIS**:
```python
# WRONG: Summing totals across forms or computing from line items
for proj, data in projects:
    total = sum(r['quantity'] * r['unit_price'] for r in data['items'])  # WRONG
    date = min(data['dates'])  # WRONG - should be max (latest)
```

## Total Amount Extraction

Use the form's reported total, NOT computed sum:
```python
TOTAL_PATTERN = r'(?:TOTAL|CUMULATIVE|GRAND TOTAL)[:\s]*[\$]?\s*([\d,]+\.?\d{2})'

def extract_total_amount(text):
    match = re.search(TOTAL_PATTERN, text, re.IGNORECASE)
    return float(match.group(1).replace(',', '')) if match else None
```

## Common OCR Errors

| OCR Error | Correction | Context |
|-----------|------------|---------|
| `C30` read as quantity 30 | Filter letter-prefix numbers | Quantity extraction |
| `m³` → `m3` or `m?` | Normalize unit string | Quantity parsing |
| `O` → `0`, `l` → `1` | Digit normalization | Prices, quantities |
| Description split across lines | Line lookahead | Item parsing |

## Validation Rules

1. Details row count = images × items per form (verify with OCR)
2. Summary row count = unique project codes
3. Project codes match pattern `PROJ-YYYY-NNN`
4. Dates in ISO YYYY-MM-DD format
5. Amounts as raw floats (NO fixed decimal formatting)
6. Summary uses LATEST date per project (NOT earliest)
7. Summary uses form's total_amount (NOT computed from line items)

## Complete Example

```python
import os
import re
import glob
import pytesseract
from PIL import Image, ImageEnhance
from openpyxl import Workbook

def process_construction_forms(image_dir, output_path):
    image_paths = sorted(glob.glob(os.path.join(image_dir, '*.[jp][pn][g]')))
    
    forms = []
    details = []
    
    for path in image_paths:
        text = pytesseract.image_to_string(Image.open(path))
        
        proj = extract_project_code(text)
        date = extract_date(text)
        total = extract_total_amount(text)
        items = extract_line_items(text)
        
        form = {
            'filename': os.path.basename(path),
            'project_code': proj,
            'date': date,
            'total_amount': total,
            'items': items
        }
        forms.append(form)
        
        for item in items:
            details.append({
                'filename': form['filename'],
                'project_code': proj,
                'item_description': item['description'],
                'quantity': item['quantity'],
                'unit_price': item['unit_price']
            })
    
    # Correct aggregation: latest form per project
    summary = aggregate_projects(forms)
    
    # Output
    wb = Workbook()
    ws_det = wb.active
    ws_det.title = 'details'
    ws_det.append(['filename', 'project_code', 'item_description', 'quantity', 'unit_price'])
    for r in sorted(details, key=lambda x: x['filename']):
        ws_det.append([r['filename'], r['project_code'], r['item_description'], r['quantity'], r['unit_price']])
    
    ws_sum = wb.create_sheet('summary')
    ws_sum.append(['project_code', 'date', 'total_amount'])
    for r in summary:
        ws_sum.append([r['project_code'], r['date'], r['total_amount']])
    
    wb.save(output_path)
```