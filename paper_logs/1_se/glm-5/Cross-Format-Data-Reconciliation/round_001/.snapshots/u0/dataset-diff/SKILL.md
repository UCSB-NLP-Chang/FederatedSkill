---
name: dataset-diff
description: Compare structured datasets across different file formats (Excel, PDF, CSV, JSON) and generate a diff output. Use when tasks require identifying added, removed, or changed records between two data sources.
---

# Dataset Diff

Compare two datasets from different file formats and produce a structured diff.

## Workflow

1. **Identify source formats** - Check file extensions to determine read method
2. **Extract data to common format** - Convert both sources to Python dicts/lists
3. **Compare by primary key** - Use a unique identifier field to match records
4. **Generate diff output** - Structure as retired IDs, new IDs, and changed fields

## Reading Different Formats

### Binary Excel (.xlsx)
Do NOT use the Read tool on .xlsx files - it will fail with a binary error.

```python
import pandas as pd
df = pd.read_excel('/path/to/file.xlsx')
records = df.to_dict('records')
```

### PDF Files
PDFs return base64-encoded content via the Read tool. Decode and parse:

```python
import base64
import pdfplumber  # or PyPDF2

# If Read tool returns base64:
with open('/path/to/file.pdf', 'rb') as f:
    pdf = pdfplumber.open(f)
    text = ''.join([page.extract_text() for page in pdf.pages])
```

For tabular PDFs, use `pdfplumber`'s `extract_tables()` method.

### CSV and JSON
These can be read directly with the Read tool or via Python:

```python
import json, csv
# JSON
with open('/path/to/file.json') as f:
    data = json.load(f)
# CSV
import pandas as pd
df = pd.read_csv('/path/to/file.csv')
```

## Diff Output Structure

```json
{
  "retired_ids": ["ID1", "ID2"],
  "new_ids": ["ID3"],
  "changed_records": [
    {"id": "ID4", "field": "FieldName", "old_value": "x", "new_value": "y"}
  ]
}
```

## Comparison Pattern

```python
def diff_datasets(old_records, new_records, key_field='id'):
    old_by_id = {r[key_field]: r for r in old_records}
    new_by_id = {r[key_field]: r for r in new_records}
    
    old_ids = set(old_by_id.keys())
    new_ids = set(new_by_id.keys())
    
    retired_ids = list(old_ids - new_ids)
    new_id_list = list(new_ids - old_ids)
    
    changed = []
    for shared_id in old_ids & new_ids:
        old_rec = old_by_id[shared_id]
        new_rec = new_by_id[shared_id]
        for field in old_rec:
            if old_rec.get(field) != new_rec.get(field):
                changed.append({
                    'id': shared_id,
                    'field': field,
                    'old_value': old_rec.get(field),
                    'new_value': new_rec.get(field)
                })
    
    return {'retired_ids': retired_ids, 'new_ids': new_id_list, 'changed_records': changed}
```

## Anti-Patterns

- **Do not** attempt to read .xlsx files with the Read tool - always use Python/pandas
- **Do not** assume PDFs will yield clean text; they may require table extraction
- **Do not** compare without a primary key; field-by-field comparison without ID matching produces false positives