---
name: structured-data-reconciliation
description: Compare structured datasets across different file formats (PDF, Excel, CSV) and generate a validated diff report. Use when tasked with reconciling versions of tabular data, identifying added/retired records, or tracking field-level changes.
---

# Structured Data Reconciliation & Cross-Format Diff

## Decision Rules
1. **Excel/CSV**: Always use `pandas` or `openpyxl`. Never use `Read` on binary spreadsheets.
2. **PDF Tables**: Always prefer `pdfplumber`'s `extract_table()` for tabular data. It preserves column boundaries reliably.
3. **PDF Raw Text**: Only fall back to raw text extraction (`page.extract_text()`) if `extract_table()` returns `None` or empty. **Warning**: Raw text parsing frequently splits multi-word fields (e.g., "Applied Statistics 101" → `["Applied", "Statistics", "101"]`), causing column misalignment.
4. **Diffing**: Always run extraction, normalization, and diffing in a single Python script. Avoid multi-step shell pipelines or subagents.

## Workflow
1. **Extract**: Load both datasets into Python lists of dicts.
   - For PDFs, use `page.extract_table()`. Verify headers match expected columns.
2. **Normalize & Coerce**: 
   - Identify the unique key field (e.g., `ID`, `SKU`).
   - **Crucial**: PDF text extraction returns strings. Coerce numeric-looking strings to `float`/`int` before diffing to prevent false positives.
3. **Align Output Schema**: Check task requirements for exact output keys (e.g., `missing_containers` vs `retired_service_ids`).
4. **Compute Diff**: Map old/new records, find added/removed keys, and compare field values for common keys.
5. **Validate**: Verify output JSON matches schema, preserves numeric types, and correctly identifies deltas.

## Fallback: Raw Text PDF Parsing
Use only when `extract_table()` fails. Always verify column alignment immediately:
```python
import re

def parse_simple_pdf(text, headers):
    lines = [l for l in text.splitlines() if l.strip()]
    data = []
    for line in lines[1:]: # skip header
        parts = re.split(r'\s{2,}', line.strip())
        if len(parts) == len(headers):
            data.append(dict(zip(headers, parts)))
        else:
            # Column misalignment detected. Switch to extract_table() or adjust regex.
            raise ValueError(f"Column mismatch: expected {len(headers)}, got {len(parts)} in line: {line}")
    return data
```

## Inline Python Template (Extraction + Coercion + Diff)
Use this for most tasks. It handles extraction, type coercion, and schema mapping in one step:
```python
import json, re, openpyxl
import pdfplumber

def coerce(val):
    if isinstance(val, str) and re.match(r'^-?\d+(\.\d+)?$', val.strip()):
        return float(val) if '.' in val else int(val)
    return val

def normalize(data):
    return [{k: coerce(v) for k, v in row.items()} for row in data]

# 1. Extract
pdf_data = []
with pdfplumber.open("old.pdf") as pdf:
    for page in pdf.pages:
        table = page.extract_table()
        if table:
            headers = [h.strip() for h in table[0]]
            for row in table[1:]:
                pdf_data.append(dict(zip(headers, row)))

wb = openpyxl.load_workbook("new.xlsx")
ws = wb.active
excel_data = []
headers = [cell.value for cell in ws[1]]
for row in ws.iter_rows(min_row=2, values_only=True):
    excel_data.append(dict(zip(headers, row)))

# 2. Normalize
old_data = normalize(pdf_data)
new_data = normalize(excel_data)

# 3. Diff
old_map = {r['ID']: r for r in old_data}
new_map = {r['ID']: r for r in new_data}

retired = [k for k in old_map if k not in new_map]
added = [k for k in new_map if k not in old_map]
changed = []
for k in sorted(set(old_map) & set(new_map)):
    for f in sorted(set(old_map[k]) | set(new_map[k])):
        if old_map[k].get(f) != new_map[k].get(f):
            changed.append({"id": k, "field": f, "old_value": old_map[k].get(f), "new_value": new_map[k].get(f)})

# 4. Map to task-specific keys & output
output = {
    "deleted_items": retired,
    "added_items": added,
    "modified_items": changed
}
print(json.dumps(output, indent=2))
with open("diff_report.json", "w") as f:
    json.dump(output, f, indent=2)
```

## Anti-Patterns
- ❌ Using `Read` on `.xlsx` or binary files (returns tool error).
- ❌ Relying on fixed diff output keys without checking task requirements.
- ❌ Comparing raw PDF-extracted strings against Excel numbers without type coercion.
- ❌ Using subagents for table extraction when direct Python is faster and more controllable.
- ❌ Splitting extraction and diffing into multiple steps unless necessary; prefer a single deterministic script.
- ❌ Assuming raw text PDF parsing preserves columns; always verify `len(parts) == len(headers)` or use `extract_table()`.

## Script Usage
Run `scripts/diff_generator.py` only when you already have normalized JSON arrays and need a quick CLI diff:
```bash
python3 scripts/diff_generator.py --old old_data.json --new new_data.json --key ID --output diff.json
```
- **Note**: The script outputs fixed keys (`retired_service_ids`, `added_service_ids`, `changed_services`). If the task requires different keys, use the inline template instead.

## Validation Checklist
- [ ] Output is valid JSON.
- [ ] Output keys exactly match the task specification.
- [ ] Retired/dropped IDs are present in old but missing in new.
- [ ] Changed/adjusted entries list exact field deltas with `old_value` and `new_value`.
- [ ] Numeric types are preserved and coerced consistently before diffing.
- [ ] PDF extraction column alignment verified (headers match row parts count).