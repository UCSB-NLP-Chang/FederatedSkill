# PDF Table Extraction Patterns

Common patterns for extracting structured data from PDFs using `pdfplumber`.

## Basic Table Extraction

```python
import pdfplumber
import pandas as pd
import json

with pdfplumber.open('document.pdf') as pdf:
    all_data = []
    for page_num, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for table in tables:
            # First row is typically headers
            headers = table[0]
            rows = table[1:]
            for row in rows:
                # Clean whitespace from strings
                cleaned = {h: (v.strip() if isinstance(v, str) else v) 
                          for h, v in zip(headers, row)}
                all_data.append(cleaned)

# Preserve types by converting through JSON
json_str = json.dumps(all_data)
data = json.loads(json_str)
```

## Handling Numeric Columns

PDFs extract as strings. Convert numeric columns explicitly:

```python
def parse_numeric(val):
    """Convert string to int/float, preserving None."""
    if val is None or val == '':
        return None
    try:
        f = float(val)
        return int(f) if f == int(f) else f
    except (ValueError, TypeError):
        return val

# Apply to known numeric columns
for row in data:
    for col in ['StockUnits', 'ReorderLevel', 'Capacity']:
        if col in row:
            row[col] = parse_numeric(row[col])
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Multi-page tables | Iterate all pages, accumulate rows |
| Header repeated on each page | Skip rows matching header pattern or use `setdefault` logic |
| Merged cells | Check for `None` values in row, fill from above row |
| Whitespace in cells | Strip strings: `val.strip() if val else val` |
| Empty tables returned | Try `page.extract_text()` to verify content exists; adjust `table_settings` |
| Jagged rows (missing columns) | Pad row to match header length: `row += [None] * (len(headers) - len(row))` |

## Table Settings for Complex Layouts

```python
tables = page.extract_tables({
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "join_tolerance": 3,
})
```

## Medication Inventory Example

```python
import pdfplumber
import json

with pdfplumber.open('medications_archive.pdf') as pdf:
    all_meds = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            headers = table[0]
            for row in table[1:]:
                record = dict(zip(headers, row))
                # Clean and type-convert
                for key in ['StockUnits', 'ReorderLevel']:
                    if key in record and record[key]:
                        record[key] = int(float(record[key]))
                all_meds.append(record)

with open('archive.json', 'w') as f:
    json.dump(all_meds, f, indent=2)
```
