---
name: ocr-reference-merge
description: Extract key identifiers from documents/images using OCR and merge with external reference datasets (CSV/JSON). Use when enriching OCR-extracted records with master data like employee IDs, product details, or account information from a roster/catalog/database file.
---

# OCR Reference Data Merging

Extract documents using OCR, join with reference datasets via extracted keys, and produce unified output. This pattern handles the "document + master data" integration workflow where images contain codes/IDs that link to structured reference information.

## Quick Start

1. **Load reference** as lookup dict keyed by join column
2. **OCR images** using multi-strategy extraction (see ocr-data-extraction skill)
3. **Extract keys** using regex with multiple label variations
4. **Left-join**: Preserve all image records, enrich where reference exists
5. **Normalize** dates to ISO, amounts to 2-decimal strings
6. **Validate** row count matches input image count exactly

## Critical Rules

**Always Left-Join**: Preserve every image as one output row. If reference lookup fails, set merged fields to null. Never filter out "orphan" records.

**Normalize Keys Before Lookup**:
```python
lookup_key = extracted_key.upper().strip()
ref_data = reference_dict.get(lookup_key)  # May be None
```

**Handle Label Variation**: Same dataset may use different labels for the same field ("Claim Code:", "Claim Ref:", "Expense ID:"). Scan for all variants.

## Workflow Details

### 1. Reference Data Loading

```python
import csv
from pathlib import Path

def load_reference(ref_path: Path, key_column: str, value_columns: list[str]):
    """Load CSV as dict: {key: {col: val, ...}}"""
    ref = {}
    with open(ref_path) as f:
        for row in csv.DictReader(f):
            key = row[key_column].strip().upper()
            ref[key] = {col: row[col] for col in value_columns}
    return ref
```

### 2. Flexible Field Extraction

Documents use inconsistent labels. Try multiple patterns for the same semantic field:

| Field | Pattern Variations |
|-------|-------------------|
| Code ID | `CODE:`, `REF:`, `ID:`, `NUMBER:` |
| Dates | `DATE:`, `PURCHASE DATE`, `TRANSACTION DATE` |
| Amounts | `TOTAL:`, `AMOUNT:`, `REIMBURSABLE TOTAL` |

Use case-insensitive regex with optional prefixes:
```regex
(?:CLAIM\s*(?:CODE|REF|ID)?|EXPENSE\s*(?:CODE|ID))\s*[:\-]?\s*(CLM-\d{4}-\d{3})
```

### 3. Date Normalization

Real documents mix formats. Try in order of specificity:
- `YYYY-MM-DD` (ISO, unambiguous)
- `DD/MM/YYYY` (common in non-US locales)
- `DD-MM-YYYY`

Parse to `datetime` then output `YYYY-MM-DD`. Invalid dates → None.

### 4. Amount Extraction

Look for currency indicators, but extract numeric value. Handle:
- Decimal: `55.20`, `120.00`
- Thousand separators: `1,234.56` → strip commas
- Different labels: `TOTAL CLAIM:`, `AMOUNT CLAIMED`, `REIMBURSABLE TOTAL`

## Validation Checklist

- [ ] Output rows == input image count (left-join verification)
- [ ] Files processed in sorted order (deterministic output)
- [ ] Dates valid ISO format or None (not raw OCR strings)
- [ ] Amounts consistently formatted (numeric or 2-decimal strings)
- [ ] Reference columns present for all rows (None/empty if no match)
- [ ] No duplicate rows (check for duplicate filenames in output)

## Anti-Patterns

- **Don't use inner join**: Filtering out images not in reference loses data and breaks row alignment
- **Don't trust single label pattern**: "Claim Code:" in first image may be "Claim Ref:" in next
- **Don't skip key normalization**: OCR may yield "clm-2024-001" but reference has "CLM-2024-001"
- **Don't round amounts**: Preserve full precision; format to 2 decimals only for display
- **Don't process files unsorted**: Sort `Path.glob()` results for deterministic "first" occurrence logic

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| All reference columns null | Case mismatch or whitespace | Uppercase and strip both extracted and reference keys |
| Row count mismatch | Inner join filtering | Ensure all images produce output row even without reference match |
| Dates inconsistent | Mixed formats | Parse multiple patterns, normalize to ISO |
| Missing some amounts | Label variation | Add regex for alternative field names (TOTAL vs AMOUNT) |
| Duplicate outputs | Unsorted processing | Sort input files before loop |

## Scripts and Templates

- `scripts/merge_template.py` - Complete implementation with reference loading, OCR, and Excel output

## Related Skills

- `ocr-data-extraction` - Multi-strategy OCR preprocessing and field extraction patterns
