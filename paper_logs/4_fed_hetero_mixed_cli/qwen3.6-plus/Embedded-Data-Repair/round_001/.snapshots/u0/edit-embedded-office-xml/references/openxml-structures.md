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
