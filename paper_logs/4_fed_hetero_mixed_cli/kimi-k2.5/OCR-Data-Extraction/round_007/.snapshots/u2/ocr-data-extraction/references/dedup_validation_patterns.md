# Deduplication & Reference Validation Patterns

## Duplicate Detection Workflow
When processing a batch of images/documents that may contain duplicate logical records:

1. Extract the key field (e.g., order_id, invoice_number, product_code) from each document.
2. Sort documents by filename (or other deterministic order).
3. Track seen keys in a set.
4. For each document:
   - If key is not in seen set: add to set, keep extracted data.
   - If key is in seen set: null out data fields, preserve filename.

### Python Pattern
```python
seen_keys = set()
rows = []
for filename in sorted(filenames):
    extracted = extract_data(filename)
    key = extracted.get("order_id")
    if key and key in seen_keys:
        rows.append({"filename": filename, "order_id": None, "date": None, "total_amount": None})
    else:
        if key:
            seen_keys.add(key)
        rows.append(extracted)
```

## Reference File Validation
When a reference file (CSV, JSON, etc.) is provided with valid keys:

1. Load reference file early in the workflow.
2. Extract keys from reference into a set for O(1) lookup.
3. Validate each extracted key against the reference set.
4. Handle unknown keys per task requirements (null, flag, or skip).

### Python Pattern
```python
import csv

# Load reference
valid_keys = set()
with open("known_orders.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        valid_keys.add(row["order_id"].strip())

# Validate
if extracted_id not in valid_keys:
    # Handle unknown: null, flag, or skip per task spec
    pass
```

## OCR Artifact Normalization for Duplicate Detection

**Critical**: OCR frequently misreads characters, creating apparent duplicates with different spellings. Simple character substitution is insufficient because OCR can create different-length IDs.

### The Problem
OCR may read the same ID differently:
- `FUEL-N-001` → `FUEL-N-OO1` (O instead of 0)
- `FUEL-N-001` → `FUEL-N-002` (different length due to OCR error)
- `FUEL-S-00001` → `FUEL-S-OO0O1` (multiple O/0 confusions)

Naive normalization (just replacing O→0) fails because `FUEL-N-OO1` and `FUEL-N-002` normalize to different lengths.

### The Solution: Character Substitution + Numeric Normalization
```python
import re

def normalize_id_for_dedup(id_str: str) -> str:
    """
    Normalize an ID for duplicate detection by handling OCR artifacts.

    1. Replace common OCR confusions (O→0, l→1, I→1, S→5, B→8)
    2. Strip leading zeros from numeric suffix to handle length differences

    Example:
        FUEL-N-OO1 → FUEL-N-1
        FUEL-N-002 → FUEL-N-2
        FUEL-S-OO0O1 → FUEL-S-1
    """
    # Step 1: Character substitutions for OCR confusions
    normalized = id_str.upper()
    normalized = normalized.replace('O', '0').replace('l', '1').replace('I', '1')
    normalized = normalized.replace('S', '5').replace('B', '8')

    # Step 2: Strip leading zeros from numeric suffix
    # Pattern: prefix (letters/dashes) followed by zeros and digits
    match = re.match(r"([A-Z\-]+)(0*)(\d+)", normalized)
    if match:
        prefix = match.group(1)
        number = match.group(3)  # Actual number without leading zeros
        return f"{prefix}{number}"

    return normalized

# Usage in duplicate detection
seen_normalized = set()
for item in items:
    raw_id = item['txn_ref']
    normalized_id = normalize_id_for_dedup(raw_id)
    if normalized_id in seen_normalized:
        print(f"Duplicate: {raw_id} (normalized: {normalized_id})")
        continue  # Skip duplicate
    seen_normalized.add(normalized_id)
    # Process unique item
```

### Common OCR Confusions
| OCR Reads | Likely Intended | Normalization |
|-----------|------------------|---------------|
| `O` in numbers | `0` | Replace O→0 |
| `l` (lowercase L) | `1` | Replace l→1 |
| `I` (uppercase i) | `1` | Replace I→1 |
| `S` in numbers | `5` | Replace S→5 |
| `B` in numbers | `8` | Replace B→8 |
| `FUEL-N-OO1` | `FUEL-N-001` | O→0, strip leading zeros → `FUEL-N-1` |
| `FUEL-S-OO0O1` | `FUEL-S-00001` | O→0, strip leading zeros → `FUEL-S-1` |

## Merging Extracted Data with Reference Files
When you need to join extracted image data with external reference data (rosters, catalogs, employee lists):

### Pattern: Left Join on Common Key
```python
import csv
from openpyxl import Workbook

# Load reference data into a lookup dict
reference = {}
with open("roster.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Key is the field that matches extracted data
        reference[row["claim_code"]] = {
            "employee_id": row["employee_id"],
            "trip_id": row["trip_id"]
        }

# Process images and merge
wb = Workbook()
ws = wb.active
ws.append(["filename", "claim_code", "employee_id", "trip_id", "date", "amount"])

for filename in sorted(image_files):
    extracted = extract_from_image(filename)  # Your OCR extraction
    claim_code = extracted["claim_code"]

    # Look up reference data (returns None if not found)
    ref_data = reference.get(claim_code, {})

    # Write row with merged data - NOTE: pass raw float for amount
    ws.append([
        filename,
        claim_code,
        ref_data.get("employee_id"),  # None if not in reference
        ref_data.get("trip_id"),       # None if not in reference
        extracted["date"],
        extracted["amount"]  # Raw float, NOT formatted string
    ])
```

### Key Points for Merging
1. **Load reference data first** - before processing any images
2. **Use dict lookup for O(1) access** - don't iterate through reference for each image
3. **Handle missing keys gracefully** - use `.get()` with default, leave cells empty/None
4. **Don't format numbers during merge** - pass raw floats to Excel
5. **Sort output by filename** for deterministic, testable results

## Common Scenarios
- **Shipping orders**: Duplicate order IDs across different shipment dates. Keep first by filename.
- **Invoices**: Same invoice number scanned multiple times. Keep first occurrence.
- **Product catalogs**: Same product code with different prices. Validate against master catalog.
- **Travel claims**: Merge claim images with employee roster. Claims not in roster get empty employee fields.
- **Fuel receipts**: Transaction refs with OCR artifacts (O/0 confusion). Normalize before dedup.