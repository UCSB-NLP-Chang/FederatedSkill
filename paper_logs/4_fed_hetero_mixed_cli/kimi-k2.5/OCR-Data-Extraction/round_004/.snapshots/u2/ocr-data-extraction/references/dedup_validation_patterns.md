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

## Common Scenarios
- **Shipping orders**: Duplicate order IDs across different shipment dates. Keep first by filename.
- **Invoices**: Same invoice number scanned multiple times. Keep first occurrence.
- **Product catalogs**: Same product code with different prices. Validate against master catalog.