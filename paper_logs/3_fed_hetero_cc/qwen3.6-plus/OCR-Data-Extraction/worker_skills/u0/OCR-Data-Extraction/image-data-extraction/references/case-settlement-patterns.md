# Case Settlement Packet Patterns

Patterns for extracting data from case settlement packets organized in nested folder structures with document type filtering, admin page exclusion, duplicate detection, and case-based aggregation.

## Directory Structure Pattern

```
dataset/
├── case_alpha/
│   ├── purchases/
│   │   ├── pur_001.jpg
│   │   ├── pur_002.jpg
│   │   └── pur_dup.jpg      # Duplicate - same ref as another
│   ├── credits/
│   │   └── cred_001.jpg
│   └── admin/
│       ├── cover.jpg        # Exclude
│       └── checklist.jpg    # Exclude
├── case_beta/
│   ├── purchases/
│   │   └── pur_001.jpg
│   └── credits/
│       └── cred_001.jpg
```

## Document Type Classification

### Purchase Document Indicators
```python
PURCHASE_INDICATORS = ["PURCHASE", "RECEIPT", "INVOICE", "TAX INVOICE", "PUR-"]
```

### Credit Document Indicators
```python
CREDIT_INDICATORS = ["CREDIT", "CREDIT NOTE", "REFUND", "ADJUSTMENT", "CR-"]
```

### Admin Page Indicators (Exclude)
```python
ADMIN_INDICATORS = ["CHECKLIST", "COVER PAGE", "THANK YOU", "ADMIN", "INSTRUCTIONS", "INDEX"]
```

### Classification Function
```python
def classify_document(text):
    """Classify document type from OCR text."""
    text_upper = text.upper()
    
    # Check for admin pages first (exclude these)
    if any(ind in text_upper for ind in ADMIN_INDICATORS):
        return 'admin'
    
    # Check for credit documents
    if any(ind in text_upper for ind in CREDIT_INDICATORS):
        return 'credit'
    
    # Check for purchase documents
    if any(ind in text_upper for ind in PURCHASE_INDICATORS):
        return 'purchase'
    
    return 'unknown'
```

## Document Reference Extraction

```python
DOC_REF_PATTERNS = [
    r'(PUR-[A-Z]-\d+)',       # PUR-A-001, PUR-B-002
    r'(CR-[A-Z]-\d+)',        # CR-A-001, CR-B-001
]

def extract_document_ref(text):
    """Extract document reference from OCR text."""
    for pattern in DOC_REF_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalize_doc_ref(match.group(1))
    return None

def normalize_doc_ref(ref):
    """Normalize document reference - fix OCR errors."""
    normalized = ref.upper()
    normalized = normalized.replace('O', '0').replace('l', '1')
    return normalized
```

## Duplicate Detection Strategy

Detect duplicates by normalized document reference. Keep first occurrence by sorted path:

```python
def deduplicate_by_ref(records, ref_field='document_ref'):
    """Keep first occurrence by sorted relative_path."""
    seen = set()
    unique = []
    for r in sorted(records, key=lambda x: x['relative_path']):
        ref = r.get(ref_field)
        if ref and ref not in seen:
            seen.add(ref)
            unique.append(r)
        elif not ref:
            unique.append(r)  # Keep records without refs
    return unique
```

## Case-Based Aggregation (Net Summary)

```python
from collections import defaultdict

def aggregate_by_case(events):
    """Calculate net summary per case.
    
    Returns list of dicts with:
    - case_id: Case identifier
    - purchase_total: Sum of purchase amounts (raw float)
    - credit_total: Sum of credit amounts (raw float)
    - net_amount: purchase_total - credit_total (raw float)
    - latest_date: Most recent date across all events
    """
    cases = defaultdict(lambda: {'purchases': [], 'credits': [], 'dates': []})
    
    for evt in events:
        case_id = evt['case_id']
        if evt['document_type'] == 'purchase':
            cases[case_id]['purchases'].append(evt['amount'] or 0)
        elif evt['document_type'] == 'credit':
            cases[case_id]['credits'].append(evt['amount'] or 0)
        if evt['date']:
            cases[case_id]['dates'].append(evt['date'])
    
    summary = []
    for case_id in sorted(cases.keys()):
        data = cases[case_id]
        purchase_total = sum(data['purchases'])
        credit_total = sum(data['credits'])
        net_amount = purchase_total - credit_total
        latest_date = max(data['dates']) if data['dates'] else None
        
        summary.append({
            'case_id': case_id,
            'purchase_total': purchase_total,  # RAW FLOAT
            'credit_total': credit_total,      # RAW FLOAT
            'net_amount': net_amount,          # RAW FLOAT
            'latest_date': latest_date
        })
    
    return summary
```

## Multi-Sheet Excel Output

```python
from openpyxl import Workbook

def create_case_settlement_output(events, summary, output_path):
    """Create Excel with events and net_summary sheets."""
    wb = Workbook()
    
    # Events sheet
    ws_events = wb.active
    ws_events.title = 'events'
    ws_events.append(['case_id', 'relative_path', 'document_type', 
                       'document_ref', 'date', 'amount'])
    
    for event in events:
        ws_events.append([
            event['case_id'],
            event['relative_path'],
            event['document_type'],
            event['document_ref'],
            event['date'],
            event['amount']  # RAW FLOAT - NO formatting
        ])
    
    # Net summary sheet
    ws_summary = wb.create_sheet('net_summary')
    ws_summary.append(['case_id', 'purchase_total', 'credit_total', 
                        'net_amount', 'latest_date'])
    
    for row in summary:
        ws_summary.append([
            row['case_id'],
            row['purchase_total'],  # RAW FLOAT
            row['credit_total'],    # RAW FLOAT
            row['net_amount'],      # RAW FLOAT
            row['latest_date']
        ])
    
    wb.save(output_path)
```

## Complete Processing Example

```python
import os
import re
import pytesseract
from PIL import Image
from openpyxl import Workbook

def process_case_settlements(dataset_root, output_path):
    # Find all images
    images = []
    for root, dirs, files in os.walk(dataset_root):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, dataset_root)
                case_id = rel_path.split(os.sep)[0]
                images.append((full_path, rel_path, case_id))
    
    events = []
    for full_path, rel_path, case_id in sorted(images, key=lambda x: x[1]):
        text = pytesseract.image_to_string(Image.open(full_path))
        
        if is_admin_page(text):
            continue
        
        doc_type = classify_document(text)
        if doc_type == 'admin' or doc_type == 'unknown':
            continue
        
        doc_ref = extract_document_ref(text)
        date = extract_date(text)
        amount = extract_amount(text)
        
        events.append({
            'case_id': case_id,
            'relative_path': rel_path.replace('\\', '/'),  # Forward slashes
            'document_type': doc_type,
            'document_ref': doc_ref,
            'date': date,
            'amount': amount  # RAW FLOAT
        })
    
    # Deduplicate by document_ref
    events = deduplicate_by_ref(events)
    
    # Compute summary
    summary = aggregate_by_case(events)
    
    # Create output
    create_case_settlement_output(events, summary, output_path)
```

## Output Format

### Events Sheet
| Column | Type | Notes |
|--------|------|-------|
| case_id | string | Case identifier from folder name |
| relative_path | string | Path from dataset root (forward slashes) |
| document_type | string | 'purchase' or 'credit' |
| document_ref | string | Normalized document reference |
| date | string | ISO format YYYY-MM-DD |
| amount | float | **Raw float**, no formatting |

### Net Summary Sheet
| Column | Type | Notes |
|--------|------|-------|
| case_id | string | Case identifier |
| purchase_total | float | Sum of purchase amounts (**raw float**) |
| credit_total | float | Sum of credit amounts (**raw float**) |
| net_amount | float | purchase_total - credit_total (**raw float**) |
| latest_date | string | Most recent date for this case |

## Validation Rules

1. Events row count = relevant documents (excluding admin and duplicates)
2. Net summary row count = unique case IDs
3. **All amounts are raw floats** (NOT formatted strings like `'78.50'`)
4. Document refs normalized (O→0, l→1)
5. Dates in ISO YYYY-MM-DD format
6. Relative paths use forward slashes (not backslashes)
7. Events sorted by case_id then relative_path
8. Net summary sorted by case_id

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Amount stored as string | `f"{x:.2f}"` applied | Use raw float, no formatting |
| Duplicate refs not caught | OCR variation | Normalize refs before comparison |
| Admin pages included | Missing filter | Check admin indicators first |
| Backslashes in path | Windows handling | Replace `\\` with `/` |