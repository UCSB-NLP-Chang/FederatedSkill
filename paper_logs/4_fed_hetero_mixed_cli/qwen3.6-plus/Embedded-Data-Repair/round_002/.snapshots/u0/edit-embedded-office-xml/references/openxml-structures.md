# OpenXML Structures for Embedded Excel

## File Locations in PPTX

```
input.pptx (ZIP)
├── [Content_Types].xml          # Must preserve exactly
├── _rels/.rels                  # Package relationships
├── ppt/
│   ├── embeddings/
│   │   └── Microsoft_Excel_Worksheet.xlsx   # Target Excel file
│   └── ...
```

## Excel XML Structure (worksheet.xml)

Namespace: `http://schemas.openxmlformats.org/spreadsheetml/2006/main`

Key cell types:
- **Text**: `<c r="A1" t="inlineStr"><is><t>Text</t></is></c>`
- **Number**: `<c r="B2" t="n"><v>1.0823</v></c>`
- **Formula**: `<c r="C2"><f>ROUND(1/B3, 4)</f><v /></c>`

## Modification Pattern

Only modify `<v>` tags inside `<c>` elements without `<f>` children:

```python
# Safe: Update static value
if cell.get('r') == target_coord and cell.get('t') == 'n':
    v_elem = cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
    if v_elem is not None and cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}f') is None:
        v_elem.text = str(new_value)
```

## Critical Namespaces

```python
NS = {
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
}
```

## Reassembly Notes

- Use `zipfile.ZipFile` with mode `'w'` and `compress_type=zipfile.ZIP_DEFLATED`
- Maintain original file order if possible (though usually not strictly required)
- Do not modify `[Content_Types].xml` unless adding new parts

## Common Failure Patterns

### Precision loss in derived calculations (R1 failure)
- **Problem**: Computing `1/0.8645` and writing `1.1567` (rounded to 4 decimals) instead of full precision.
- **Reality**: Verifier expects exact match; rounding introduces error.
- **Fix**: Write `repr(1/0.8645)` in Python. Never round intermediate calculations. Compute: `value = 1 / 0.8645` then use `repr(value)`.

### Searching for internal instructions
- **Problem**: Searching for "slide notes" or other text fields for correction values when the task says "the note contains the correction."
- **Reality**: The correction value is in the task prompt itself, not stored in any file field.
- **Fix**: Read correction values directly from task instructions; do not search file internals unless explicitly confirmed.

### Arbitrary correction values
- **Problem**: Using an arbitrary value when the specific correction value is unclear.
- **Reality**: Verifier expects exact match to task-provided value.
- **Fix**: If multiple candidates exist, list them and identify the correct one from task context. Never guess.

### Namespace stripping
- **Problem**: Removing namespace declarations during XML parse/repack.
- **Reality**: Office XML files require namespaces for Excel to open them correctly.
- **Fix**: Register namespaces with ElementTree and use full URIs in XPath queries.
