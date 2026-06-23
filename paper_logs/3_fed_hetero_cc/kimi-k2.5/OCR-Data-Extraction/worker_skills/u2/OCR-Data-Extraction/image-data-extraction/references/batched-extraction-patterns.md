# Batched Document Extraction Patterns

Patterns for extracting data from images organized in nested folder structures with document filtering and duplicate detection.

## Nested Folder Traversal

### Directory Structure Pattern
```
dataset/
├── batch_north/
│   ├── day1/
│   │   ├── fuel_001.jpg
│   │   └── cover.jpg
│   └── day2/
│       ├── fuel_002.jpg
│       └── promo.jpg
├── batch_south/
│   └── day1/
│       └── fuel_003.jpg
└── batch_west/
    └── day1/
        └── fuel_004.jpg
```

### Implementation
```python
import os
from pathlib import Path

def find_images_recursive(base_path):
    """Find all images in nested folders, tracking batch and relative path."""
    extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}
    images = []
    
    for root, dirs, files in os.walk(base_path):
        for f in files:
            if Path(f).suffix.lower() in extensions:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, base_path)
                
                # Extract batch name from first-level folder
                parts = rel_path.split(os.sep)
                batch_name = parts[0] if len(parts) > 1 else ''
                
                images.append({
                    'full_path': full_path,
                    'relative_path': rel_path,
                    'batch_name': batch_name
                })
    
    return sorted(images, key=lambda x: x['relative_path'])
```

## Document Type Filtering

### Keyword Indicators
Identify relevant documents by presence of specific keywords:
```python
# Fuel receipt indicators
FUEL_INDICATORS = ["FUEL RECEIPT", "PUMP SALE", "TAX INVOICE"]

# General receipt indicators
RECEIPT_INDICATORS = ["RECEIPT", "SALES RECEIPT", "TAX INVOICE", "INVOICE"]

# Non-receipt keywords to exclude
EXCLUDE_KEYWORDS = ["COVER", "PROMOTION", "LOYALTY", "ROUTE NOTE", "INFORMATION"]

def is_relevant_document(text, include_indicators, exclude_indicators=None):
    """Check if document matches include indicators and not exclude indicators."""
    text_upper = text.upper()
    
    # Must match at least one include indicator
    if not any(ind in text_upper for ind in include_indicators):
        return False
    
    # Must not match any exclude indicator
    if exclude_indicators:
        if any(ind in text_upper for ind in exclude_indicators):
            return False
    
    return True
```

### Filtering Strategy
1. Extract text from image using OCR
2. Check for include indicators (document type keywords)
3. Optionally check for exclude indicators (non-document keywords)
4. Only process relevant documents for field extraction

## Transaction Reference Normalization

### OCR Error Patterns
OCR commonly misreads characters in transaction references:
| OCR Error | Correction | Example |
|-----------|------------|---------|
| `O` (letter) | `0` (digit) | `FUEL-N-OO2` → `FUEL-N-002` |
| `l` (lowercase L) | `1` (digit) | `TXN-l234` → `TXN-1234` |
| `I` (uppercase i) | `1` (digit) | `REF-I234` → `REF-1234` |
| `S` | `5` | `TXN-S001` → `TXN-5001` |
| `B` | `8` | `REF-B001` → `REF-8001` |

### Normalization Function
```python
import re

def normalize_txn_ref(txn_ref):
    """Normalize transaction reference by fixing OCR errors."""
    if not txn_ref:
        return None
    
    # Fix common OCR misreads
    normalized = txn_ref.upper()
    normalized = normalized.replace('O', '0').replace('o', '0')
    normalized = normalized.replace('I', '1').replace('l', '1')
    normalized = normalized.replace('S', '5')
    normalized = normalized.replace('B', '8')
    
    # Normalize leading zeros in numeric suffix
    # Pattern: PREFIX-X-NNNN where X is letter and NNNN is number
    match = re.match(r'([A-Z]+-[A-Z]-)(\d+)', normalized)
    if match:
        prefix, number = match.groups()
        # Strip leading zeros, then pad to 3 digits minimum
        normalized_num = number.lstrip('0') or '0'
        normalized_num = normalized_num.zfill(3)
        return prefix + normalized_num
    
    return normalized
```

### Pattern Matching for Transaction References
```python
TXN_REF_PATTERNS = [
    r'Txn\s*(?:Ref|No)?[:\s]*([A-Z0-9-]+)',
    r'Transaction\s*(?:Ref|No|ID)?[:\s]*([A-Z0-9-]+)',
    r'Ref\s*(?:No)?[:\s]*([A-Z0-9-]+)',
    r'(FUEL-[A-Z]-\d+)',
    r'(TXN-\d+)',
    r'(REF-[A-Z0-9-]+)',
]

def extract_txn_ref(text):
    """Extract transaction reference from OCR text."""
    for pattern in TXN_REF_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalize_txn_ref(match.group(1))
    return None
```

## Duplicate Detection

### Strategy
Detect duplicates by comparing normalized transaction reference AND amount:
- Same transaction reference with same amount = duplicate
- Same transaction reference with different amount = different transaction (possible error, flag for review)

### Implementation
```python
def detect_duplicates(records, key_field='txn_ref', amount_field='total_amount'):
    """Detect and filter duplicate transactions.
    
    Returns tuple of (unique_records, duplicate_count).
    Keeps first occurrence, filters subsequent duplicates.
    """
    seen = {}
    unique = []
    duplicate_count = 0
    
    for record in records:
        key = (record.get(key_field), record.get(amount_field))
        
        if key not in seen:
            seen[key] = record['relative_path']  # Track first occurrence
            unique.append(record)
        else:
            duplicate_count += 1
            # Optionally log: f"Duplicate: {record['relative_path']} matches {seen[key]}"
    
    return unique, duplicate_count
```

### Duplicate Detection with Tolerance
For amounts that may have minor OCR variations:
```python
def amounts_match(a1, a2, tolerance=0.01):
    """Check if two amounts match within tolerance."""
    if a1 is None or a2 is None:
        return a1 == a2
    return abs(a1 - a2) <= tolerance

def detect_duplicates_with_tolerance(records, key_field='txn_ref', amount_field='total_amount', tolerance=0.01):
    """Detect duplicates with amount tolerance for OCR variations."""
    seen = {}
    unique = []
    
    for record in records:
        key = record.get(key_field)
        amount = record.get(amount_field)
        
        if key not in seen:
            seen[key] = (record['relative_path'], amount)
            unique.append(record)
        else:
            # Check if amounts match within tolerance
            _, seen_amount = seen[key]
            if amounts_match(amount, seen_amount, tolerance):
                continue  # Skip duplicate
            else:
                # Same ref, different amount - keep both (may be error)
                unique.append(record)
    
    return unique
```

## Complete Batched Extraction Example

```python
import os
import re
from pathlib import Path
from PIL import Image, ImageEnhance
import pytesseract
from openpyxl import Workbook

def process_batched_documents(dataset_path, output_path):
    """Process documents in nested folders with filtering and deduplication."""
    
    # Find all images
    images = find_images_recursive(dataset_path)
    
    # Process each image
    records = []
    for img_info in images:
        # OCR with preprocessing
        text = extract_text_with_preprocessing(img_info['full_path'])
        
        # Filter by document type
        if not is_relevant_document(text, FUEL_INDICATORS):
            continue
        
        # Extract fields
        txn_ref = extract_txn_ref(text)
        date = extract_date(text)
        amount = extract_total(text)
        
        records.append({
            'batch_name': img_info['batch_name'],
            'relative_path': img_info['relative_path'],
            'txn_ref': txn_ref,
            'date': date,
            'total_amount': amount
        })
    
    # Deduplicate
    unique_records, dup_count = detect_duplicates(records)
    
    # Sort by relative_path
    unique_records.sort(key=lambda x: x['relative_path'])
    
    # Write to Excel
    wb = Workbook()
    ws = wb.active
    ws.title = 'transactions'
    ws.append(['batch_name', 'relative_path', 'txn_ref', 'date', 'total_amount'])
    
    for record in unique_records:
        ws.append([
            record['batch_name'],
            record['relative_path'],
            record['txn_ref'],
            record['date'],
            record['total_amount']  # Raw float
        ])
    
    wb.save(output_path)
    return unique_records

def extract_text_with_preprocessing(image_path):
    """Extract text with image preprocessing for better accuracy."""
    img = Image.open(image_path)
    
    # Convert to grayscale
    img = img.convert('L')
    
    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2)
    
    # Sharpen
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2)
    
    return pytesseract.image_to_string(img)
```

## Output Format

### Column Requirements
| Column | Type | Notes |
|--------|------|-------|
| batch_name | string | First-level folder name |
| relative_path | string | Path from dataset root |
| txn_ref | string | Normalized transaction reference |
| date | string | ISO format YYYY-MM-DD |
| total_amount | float | Raw number, no formatting |

### Validation Rules
1. Row count = unique relevant documents (after filtering and deduplication)
2. All dates in ISO YYYY-MM-DD format
3. All amounts as raw floats (no string formatting)
4. Transaction refs normalized (O→0, l→1)
5. Sorted by relative_path ascending
6. No duplicate (txn_ref, amount) pairs

## Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| OCR reads "O" as "0" | Font similarity | Normalize txn refs before comparison |
| Duplicate detection fails | Inconsistent normalization | Apply normalize_txn_ref() before comparison |
| Wrong row count | Non-relevant documents included | Filter by document indicators first |
| Missing batch_name | Flat folder structure | Default to empty string or parent folder |
| Amounts don't match | OCR variation | Use tolerance-based comparison |

## Anti-Patterns

- **Do not compare raw OCR output for duplicates.** Always normalize first.
- **Do not assume all images are relevant.** Filter by document type indicators.
- **Do not use filename for deduplication.** Use transaction reference + amount.
- **Do not skip preprocessing for low-quality images.** Grayscale + contrast helps OCR accuracy.
- **Do not hardcode batch names.** Extract from folder structure dynamically.