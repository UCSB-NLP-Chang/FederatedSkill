---
name: case-document-aggregation
description: Extract and aggregate financial documents from hierarchical case directories. Use when task involves nested folder structures (case_*/{purchases,credits,admin}/), document classification with deduplication per case, and case-level summary calculations (totals, net amounts, latest dates). Handles fragmented OCR in credit notes and mixed date formats.
---

# Case Document Aggregation

Extract structured data from nested case directories containing purchase receipts, credit notes, and administrative documents. Aggregate to case-level summaries with deduplication.

## When to Use
- Directory structure: `cases/case_*/{purchases,credits,admin}/*.{jpg,png}`
- Need to classify: purchase receipts vs credit notes vs admin documents (filter out)
- Must deduplicate by `document_ref` within each case (keep first occurrence)
- Require case-level aggregation: purchase totals, credit totals, net amounts, latest dates
- OCR has fragmented text (split across lines: "CRE\n\nDIT NO:")
- Mixed date formats in same dataset (DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD)

## Directory Structure Convention

```
cases/
├── case_alpha/
│   ├── purchases/pur_001.jpg      # PUR-A-001, 120.50
│   ├── purchases/pur_002.jpg      # PUR-A-002, 80.00
│   ├── credits/cred_001.jpg       # CR-A-001, 20.00
│   └── admin/checklist.jpg        # Filter out (no transaction)
├── case_beta/
│   ├── purchases/...
│   └── credits/...
└── case_gamma/
    ├── purchases/pur_dup.jpg      # Duplicate ref - skip
    └── ...
```

## Document Classification

**Purchase Receipt indicators:**
- Header: `PURCHASE RECEIPT`, `STORE RECEIPT`, `TAX INVOICE`
- Ref patterns: `RECEIPT NO:`, `PUR-` prefix
- Amount keywords: `GRAND TOTAL`, `TOTAL DUE`, `AMOUNT DUE`

**Credit Note indicators:**
- Header: `CREDIT NOTE`, `CREDIT MEMO`, `REFUND ADJUSTMENT`
- **Critical OCR fragmentation:** Text splits as `CRE\n\nCRE\n\nDATE:\n\nDIT NO:`
- Ref patterns: `CREDIT NO:`, `CR-` prefix, or fragmented `DIT NO:` on its own line
- Amount keywords: `DIT AMOUNT:`, `REFUND TOTAL`, `TOTAL CREDIT` (also fragmented)

**Admin documents (FILTER OUT):**
- Headers: `CHECKLIST PAGE`, `CASE COVER`, `THANK YOU PAGE`
- No transaction reference patterns
- No amount keywords

## Fragmented OCR Handling

Credit notes suffer from severe line fragmentation. Use line-scanning, not whole-text regex:

```python
def extract_from_fragmented_lines(lines, doc_type):
    """Scan line-by-line for fragmented patterns."""
    ref = date = amount = None
    
    for i, line in enumerate(lines):
        line = line.strip().upper()
        
        # Fragmented credit ref: "DIT NO: CR-A-001" or "CREDIT NO: CR-A-001"
        if 'DIT NO:' in line or 'CREDIT NO:' in line:
            m = re.search(r'(?:CREDIT|DIT)\s*NO:\s*([A-Z0-9-]+)', line)
            if m:
                ref = m.group(1)
        
        # Fragmented credit amount: "DIT AMOUNT:" or "DIT:" followed by value
        if doc_type == 'credit' and ('DIT' in line or i < len(lines)-1):
            # Check current and next lines for amount
            combined = ' '.join(lines[max(0,i-1):min(len(lines),i+2)])
            m = re.search(r'DIT(?:\s*AMOUNT)?[:\s]+([\d.]+)', combined)
            if m:
                amount = m.group(1)
    
    return ref, date, amount
```

## Date Format Auto-Detection

```python
def parse_date_multi_format(date_str):
    """Parse dates with automatic format detection."""
    date_str = date_str.strip()
    
    # ISO format: 2024-01-15
    iso_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if iso_match:
        return date_str
    
    # Delimited: try DD/MM/YYYY vs MM/DD/YYYY
    m = re.match(r'(\d{2})[/-](\d{2})[/-](\d{4})', date_str)
    if m:
        first, second, year = int(m.group(1)), int(m.group(2)), m.group(3)
        
        # Second > 12 confirms MM/DD (02/14/2024 = Feb 14)
        if second > 12:
            return f"{year}-{first:02d}-{second:02d}"
        # First > 12 confirms DD/MM
        elif first > 12:
            return f"{year}-{second:02d}-{first:02d}"
        # Ambiguous: inspect case context or use DD/MM default
        else:
            return f"{year}-{second:02d}-{first:02d}"  # DD/MM default
    
    return None
```

## Deduplication Logic

Track seen refs per case, not globally:

```python
seen_refs = defaultdict(set)

for record in records:
    case_id = record['case_id']
    ref = record['document_ref']
    
    if ref in seen_refs[case_id]:
        print(f"Skipping duplicate ref: {ref} in {record['relative_path']}")
        continue
    
    seen_refs[case_id].add(ref)
    filtered_records.append(record)
```

## Case-Level Aggregation

```python
from collections import defaultdict

def aggregate_by_case(records):
    """Aggregate to case-level summary."""
    cases = defaultdict(lambda: {
        'purchases': [],
        'credits': [],
        'dates': []
    })
    
    for r in records:
        cid = r['case_id']
        cases[cid]['dates'].append(r['date'])
        
        if r['document_type'] == 'purchase':
            cases[cid]['purchases'].append(float(r['amount']))
        else:
            cases[cid]['credits'].append(float(r['amount']))
    
    summaries = []
    for cid, data in sorted(cases.items()):
        purchase_total = sum(data['purchases'])
        credit_total = sum(data['credits'])
        
        summaries.append({
            'case_id': cid,
            'purchase_total': f"{purchase_total:.2f}",
            'credit_total': f"{credit_total:.2f}",
            'net_amount': f"{purchase_total - credit_total:.2f}",
            'latest_date': max(data['dates'])
        })
    
    return summaries
```

## Output Schema

**events sheet:**
| case_id | relative_path | document_type | document_ref | date | amount |
|---------|---------------|---------------|--------------|------|--------|
| case_alpha | case_alpha/purchases/pur_001.jpg | purchase | PUR-A-001 | 2024-01-02 | 120.50 |

**net_summary sheet:**
| case_id | purchase_total | credit_total | net_amount | latest_date |
|---------|----------------|--------------|------------|-------------|
| case_alpha | 200.50 | 20.00 | 180.50 | 2024-01-15 |

## Validation Checklist

- [ ] All purchase and credit documents extracted from `purchases/` and `credits/` subdirs
- [ ] Admin documents in `admin/` correctly filtered out (no transaction data)
- [ ] Duplicate `document_ref` values within same case excluded
- [ ] Dates normalized to `YYYY-MM-DD` ISO format
- [ ] Amounts as strings with exactly 2 decimal places
- [ ] `net_amount` = `purchase_total` - `credit_total` per case
- [ ] `latest_date` = max date across all documents in case
- [ ] Sheets named exactly: `events`, `net_summary`

## Anti-Patterns

- **Do not** use whole-text regex for credit note refs - fragmentation breaks patterns
- **Do not** deduplicate globally - only within each `case_id`
- **Do not** assume consistent date format - auto-detect or check samples
- **Do not** include admin documents even if they have dates/refs (no transaction amounts)
- **Do not** calculate net_amount before formatting to 2 decimals (float precision)

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Credit refs showing as partial text (e.g., "TE") | Use line-by-line scan, not whole-text regex; check for "DIT NO:" pattern |
| Credit amounts not found | Fragmentation: check surrounding lines, combine with `\n` normalization |
| Duplicate documents included | Verify dedupe dict is keyed by `case_id`, not global |
| Dates parsed wrong | Second value > 12 confirms MM/DD (US format), else DD/MM |
| Admin docs in output | Add explicit exclusion for `CHECKLIST`, `COVER`, `THANK YOU` headers |
| Wrong net_amount | Ensure amounts converted to float before subtraction, format after |

## See Also

- `../fuel-receipt-extraction/` - Similar receipt extraction but with TXN REF filtering
- `../image-to-structured-excel/` - Template preservation and reference file enrichment
