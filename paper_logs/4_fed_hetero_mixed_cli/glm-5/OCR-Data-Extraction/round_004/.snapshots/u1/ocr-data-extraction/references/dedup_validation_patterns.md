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