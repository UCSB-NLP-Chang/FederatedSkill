# Roster Matching & Excel Writing Patterns

## Roster Matching Workflow
When a reference file (roster) maps extracted keys to additional fields:

1. Extract the key field (e.g., claim_code, order_id) from each document.
2. Load the roster CSV into a dictionary keyed by the extracted field.
3. For each document, look up the key in the roster dict.
4. If found: populate additional columns from the roster row.
5. If not found: leave additional columns empty (use `None` in openpyxl).

### Python Pattern
```python
import csv

# Load roster into dict
roster = {}
with open("claim_roster.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        roster[row["claim_code"].strip()] = row

# Match during extraction
for filename in sorted(filenames):
    extracted = extract_data(filename)
    key = extracted.get("claim_code")
    roster_entry = roster.get(key)
    
    row = {
        "filename": filename,
        "claim_code": key,
        "employee_id": roster_entry["employee_id"] if roster_entry else None,
        "trip_id": roster_entry["trip_id"] if roster_entry else None,
        "date": extracted.get("date"),
        "total_amount": extracted.get("total_amount"),
    }
    rows.append(row)
```

## openpyxl Row Writing: Critical Anti-Pattern

### WRONG: Scatters cells across rows
```python
for r in rows:
    for col, h in enumerate(headers, 1):
        val = r.get(h, '')
        ws.cell(row=ws.max_row + 1, column=col, value=val)
```
Each `ws.max_row + 1` call returns a different value because `ws.max_row` increments after each cell write. This writes each cell to a new row.

### CORRECT: Capture row number once
```python
for r in rows:
    row_num = ws.max_row + 1
    for col, h in enumerate(headers, 1):
        val = r.get(h, '')
        ws.cell(row=row_num, column=col, value=val)
```

### Alternative: Use ws.append()
```python
for r in rows:
    ws.append([r.get(h, '') for h in headers])
```
`ws.append()` is simpler and avoids the row-number bug entirely. Prefer it when column order matches the header list.

## Common Scenarios
- **Travel claims**: Match claim codes to employee/trip roster. Unmatched claims get empty employee_id/trip_id.
- **Invoice processing**: Match vendor codes to vendor master data for address/tax info.
- **Product scanning**: Match barcodes to product catalog for name/price/category.