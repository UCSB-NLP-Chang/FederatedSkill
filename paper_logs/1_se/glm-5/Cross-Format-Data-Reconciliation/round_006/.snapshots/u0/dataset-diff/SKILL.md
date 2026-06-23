---
name: dataset-diff
description: Compare structured datasets across different file formats (Excel, PDF, CSV, JSON) and generate a diff output. Use when tasks require identifying added, removed, or changed records between two data sources. Use the bundled script as the primary approach for standard comparisons.
---

# Dataset Diff

Compare two datasets from different file formats and produce a structured diff.

## Workflow

1. **Identify source formats** - Check file extensions to determine read method
2. **Extract data to common format** - Convert both sources to Python dicts/lists
3. **Compare by primary key** - Use a unique identifier field to match records
4. **Generate diff output** - Structure as retired IDs, new IDs, and changed fields

## Quick Start

**Always try the bundled script first** for standard comparisons:

```bash
python3 scripts/diff_datasets.py old_file.xlsx new_file.pdf --key ID -o diff_report.json
```

The script handles:
- Binary Excel files (.xlsx, .xls)
- PDF files (including base64-encoded content)
- CSV and JSON files
- Numpy type conversion for JSON serialization

Fall back to manual comparison only when you need:
- Custom output formats (but see post-processing below)
- Special key matching logic
- Non-tabular PDF structures

## Using the Script as a Module

For custom output formats or programmatic control, import the script functions:

```python
from scripts.diff_datasets import load_excel, load_pdf_from_base64, diff_datasets

# When Read tool returns base64-encoded PDF
old_records = load_pdf_from_base64(base64_content)
new_records = load_excel('/path/to/file.xlsx')

# Compare with custom key field
result = diff_datasets(old_records, new_records, key_field='ServerID')

# Customize output keys for task requirements
custom = {'removed': result['retired_ids'], 'modified': result['changed_records']}
```

## Output Format Verification

**Before finalizing output, verify the expected format matches the task requirements.**

The script produces this structure:

```json
{
  "retired_ids": ["ID1", "ID2"],
  "new_ids": ["ID3"],
  "changed_records": [
    {"id": "ID4", "field": "FieldName", "old_value": "x", "new_value": "y"}
  ]
}
```

If the task requires different key names (e.g., `deleted_medications` instead of `retired_ids`), post-process the output:

```python
# Rename keys to match task requirements
output = {
    'deleted_medications': result['retired_ids'],
    'modified_medications': result['changed_records']
}
```

## Reading Different Formats

### Binary Excel (.xlsx)
Do NOT use the Read tool on .xlsx files - it will fail with a binary error.

```python
import pandas as pd
df = pd.read_excel('/path/to/file.xlsx')
records = df.to_dict('records')
```

### PDF Files
The Read tool returns base64-encoded PDF content. You must decode before parsing:

```python
import base64
import pdfplumber
import io

# If Read tool returns base64 string:
pdf_bytes = base64.b64decode(base64_content)
pdf = pdfplumber.open(io.BytesIO(pdf_bytes))

# Extract text
text = ''.join([page.extract_text() or '' for page in pdf.pages])

# Extract tables (for tabular PDFs)
tables = []
for page in pdf.pages:
    tables.extend(page.extract_tables() or [])
```

**Tip:** The bundled script provides `load_pdf_from_base64()` which handles decoding and table extraction automatically.

**Troubleshooting:** If you get `ImportError: pdfplumber is required`, install it first:
```bash
pip install pdfplumber
```

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

## JSON Output from Pandas Data

When writing diff results to JSON after using pandas, numpy types (int64, float64, etc.) are not JSON serializable and will raise `TypeError: Object of type int64 is not JSON serializable`.

**Solution:** Convert values to native Python types before JSON serialization:

```python
import json

# Option 1: Convert individual values
def to_native(val):
    if hasattr(val, 'item'):  # numpy scalar
        return val.item()
    return val

result = {k: to_native(v) for k, v in record.items()}

# Option 2: Use pandas to convert entire DataFrame
df = df.astype(object).where(pd.notnull(df), None)
records = df.to_dict('records')

# Option 3: Custom JSON encoder
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'item'):
            return obj.item()
        return super().default(obj)

json.dumps(result, cls=NumpyEncoder)
```

## Anti-Patterns

- **Do not** attempt to read .xlsx files with the Read tool - always use Python/pandas
- **Do not** assume PDFs will yield clean text; they may require table extraction
- **Do not** compare without a primary key; field-by-field comparison without ID matching produces false positives
- **Do not** forget to decode base64 when the Read tool returns PDF content
- **Do not** skip installing pdfplumber before attempting PDF parsing
- **Do not** pass pandas/numpy types directly to `json.dumps()` - convert to native Python types first
- **Do not** write custom parsing code when the bundled script handles your use case - use the script first
- **Do not** assume output format - verify required key names match task specification