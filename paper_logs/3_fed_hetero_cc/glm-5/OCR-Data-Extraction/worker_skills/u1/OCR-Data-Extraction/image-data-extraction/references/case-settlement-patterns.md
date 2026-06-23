# Case Settlement Packet Patterns

Patterns for extracting data from case settlement packets organized in nested folder structures with document type filtering, duplicate detection, and case-based aggregation.

## CRITICAL: Raw Float Output

**All amounts must be raw floats. This is the #1 failure mode.**

```python
# WRONG - causes verifier failure
amount = f"{extracted:.2f}"  # Creates string "78.50"

# RIGHT - validated
amount = float(extracted)    # Creates float 78.5
ws.cell(row=r, column=6, value=amount)  # Raw float
```

**Verification**: Check `isinstance(cell.value, float)` after writing.

## Directory Structure

```
dataset/
├── case_alpha/
│   ├── purchases/
│   │   ├── pur_001.jpg
│   │   └── pur_002.jpg
│   ├── credits/
│   │   └── cred_001.jpg
│   └── admin/
│       ├── cover.jpg        # EXCLUDE
│       └── checklist.jpg    # EXCLUDE
├── case_beta/
│   └── ...
```

## Document Classification

### Purchase Indicators
```python
PURCHASE_INDICATORS = ["PURCHASE", "RECEIPT", "INVOICE", "PUR-"]
```

### Credit Indicators
```python
CREDIT_INDICATORS = ["CREDIT", "CREDIT NOTE", "REFUND", "CR-", "ADJUSTMENT"]
```

### Admin Page Indicators (EXCLUDE)
```python
ADMIN_INDICATORS = ["CHECKLIST", "COVER PAGE", "THANK YOU", "ADMIN", "INSTRUCTIONS"]
```

```python
def classify_document(text):
    text_upper = text.upper()
    if any(ind in text_upper for ind in ADMIN_INDICATORS):
        return 'admin'  # Skip these
    if any(ind in text_upper for ind in CREDIT_INDICATORS):
        return 'credit'
    if any(ind in text_upper for ind in PURCHASE_INDICATORS):
        return 'purchase'
    return 'unknown'
```

## Document Reference Extraction

```python
DOC_REF_PATTERNS = [
    r'(PUR-[A-Z]-\d+)',   # PUR-A-001
    r'(CR-[A-Z]-\d+)',    # CR-A-001
]

def extract_document_ref(text):
    for pattern in DOC_REF_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalize_doc_ref(match.group(1))
    return None

def normalize_doc_ref(ref):
    # Fix OCR errors: O -> 0, l -> 1
    return ref.upper().replace('O', '0').replace('l', '1')
```

## Deduplication

Keep first occurrence by sorted relative_path:

```python
def deduplicate_by_ref(records):
    seen = set()
    unique = []
    for r in sorted(records, key=lambda x: x['relative_path']):
        ref = r.get('document_ref')
        if ref and ref not in seen:
            seen.add(ref)
            unique.append(r)
        elif ref is None:
            unique.append(r)  # Keep records without refs
    return unique
```

## Case Aggregation

```python
def aggregate_by_case(events):
    cases = {}
    for evt in events:
        case_id = evt['case_id']
        if case_id not in cases:
            cases[case_id] = {'purchase_total': 0, 'credit_total': 0, 'dates': []}

        amount = evt['amount'] or 0  # Raw float or 0
        if evt['document_type'] == 'purchase':
            cases[case_id]['purchase_total'] += amount
        elif evt['document_type'] == 'credit':
            cases[case_id]['credit_total'] += amount
        if evt['date']:
            cases[case_id]['dates'].append(evt['date'])

    summary = []
    for case_id in sorted(cases.keys()):
        data = cases[case_id]
        summary.append({
            'case_id': case_id,
            'purchase_total': data['purchase_total'],      # Raw float
            'credit_total': data['credit_total'],          # Raw float
            'net_amount': data['purchase_total'] - data['credit_total'],  # Raw float
            'latest_date': max(data['dates']) if data['dates'] else None
        })
    return summary
```

## Multi-Sheet Excel Output

```python
from openpyxl import Workbook

wb = Workbook()

# Events sheet
ws_events = wb.active
ws_events.title = 'events'
ws_events.append(['case_id', 'relative_path', 'document_type', 'document_ref', 'date', 'amount'])

for evt in events:
    ws_events.append([
        evt['case_id'],
        evt['relative_path'].replace('\\', '/'),  # Forward slashes
        evt['document_type'],
        evt['document_ref'],
        evt['date'],
        evt['amount']  # Raw float - NO formatting
    ])

# Net summary sheet
ws_summary = wb.create_sheet('net_summary')
ws_summary.append(['case_id', 'purchase_total', 'credit_total', 'net_amount', 'latest_date'])

for row in summary:
    ws_summary.append([
        row['case_id'],
        row['purchase_total'],   # Raw float
        row['credit_total'],     # Raw float
        row['net_amount'],       # Raw float
        row['latest_date']
    ])

wb.save(output_path)
```

## Output Schema Tables

### Events Sheet
| Column | Type | Description |
|--------|------|-------------|
| case_id | string | First folder component |
| relative_path | string | Forward slashes `/` |
| document_type | string | `purchase` or `credit` |
| document_ref | string | Normalized (O→0, l→1) |
| date | string | YYYY-MM-DD |
| amount | **float** | Raw number |

### Net Summary Sheet
| Column | Type | Description |
|--------|------|-------------|
| case_id | string | Case identifier |
| purchase_total | **float** | Sum of purchases |
| credit_total | **float** | Sum of credits |
| net_amount | **float** | purchase - credit |
| latest_date | string | Max date per case |

## Validation Rules

1. Events rows = unique documents (after admin filtering + deduplication)
2. Net summary rows = unique case IDs
3. **All amounts are raw floats** - verify with `isinstance(value, float)`
4. Document refs normalized (O→0, l→1)
5. Relative paths use `/` not `\\`
6. Events sorted by (case_id, relative_path)
7. Net summary sorted by case_id

## Anti-Patterns

- **DO NOT format amounts as strings** - use raw floats
- **DO NOT include admin pages** - filter by indicators
- **DO NOT sum all amounts together** - separate purchases vs credits
- **DO NOT use backslashes** - replace `\\` with `/`
- **DO NOT skip duplicate detection** - same document_ref = duplicate
- **DO NOT hardcode case IDs** - extract from folder structure