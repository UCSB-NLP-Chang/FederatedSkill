# OpenXML Structures for Embedded Excel

## File Locations in PPTX

```
input.pptx (ZIP)
├── [Content_Types].xml          # Must preserve exactly
├── _rels/.rels                  # Package relationships
├── ppt/
│   ├── embeddings/
│   │   └── Microsoft_Excel_Worksheet.xlsx   # Target Excel file
│   └── slides/
│       └── slide1.xml           # Contains slide content & notes
```

## Extracting Text from Slide XML
If a task mentions a "note" or "correction" inside the file, search `<a:t>` tags in `ppt/slides/slide*.xml`:
```python
import zipfile, re
z = zipfile.ZipFile('input.pptx')
for name in z.namelist():
    if name.startswith('ppt/slides/slide') and name.endswith('.xml'):
        xml = z.read(name).decode('utf-8')
        texts = re.findall(r'<a:t>(.*?)</a:t>', xml)
        print(f"{name}: {' '.join(texts)}")
```

## Excel XML Structure (worksheet.xml)

Namespace: `http://schemas.openxmlformats.org/spreadsheetml/2006/main`

Key cell types:
- **Text**: `<c r="A1" t="inlineStr"><is><t>Text</t></is></c>`
- **Number**: `<c r="B2" t="n"><v>1.0823</v></c>`
- **Formula**: `<c r="C2"><f>ROUND(1/B3, 4)</f><v /></c>`

## Modification Pattern

### Using openpyxl (Preferred)
```python
import zipfile, openpyxl, io

with zipfile.ZipFile('input.pptx') as z:
    xlsx_bytes = z.read('ppt/embeddings/Microsoft_Excel_Worksheet.xlsx')

wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
ws = wb.active
ws['E6'] = 0.5  # Raw float, no rounding
new_xlsx = io.BytesIO()
wb.save(new_xlsx)

# Repack into host
with zipfile.ZipFile('input.pptx', 'r') as zin:
    with zipfile.ZipFile('output.pptx', 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == 'ppt/embeddings/Microsoft_Excel_Worksheet.xlsx':
                zout.writestr(item, new_xlsx.getvalue())
            else:
                zout.writestr(item, zin.read(item.filename))
```

### Using XML directly (Fallback)
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
- **Reality**: The correction value is often in the task prompt itself, but can also be embedded as plain text in slide XML (`<a:t>` tags).
- **Fix**: Read correction values directly from task instructions first. If not found, extract all `<a:t>` text from `ppt/slides/slide*.xml`. Do not guess.

### Arbitrary correction values
- **Problem**: Using an arbitrary value when the specific correction value is unclear.
- **Reality**: Verifier expects exact match to task-provided value.
- **Fix**: If multiple candidates exist, list them and identify the correct one from task context. Never guess.

### Namespace stripping
- **Problem**: Removing namespace declarations during XML parse/repack.
- **Reality**: Office XML files require namespaces for Excel to open them correctly.
- **Fix**: Register namespaces with ElementTree and use full URIs in XPath queries.

### Confusing notes with text boxes
- **Problem**: Checking `slide.has_notes_slide` and finding nothing, missing the text box on the slide itself.
- **Reality**: Notes (`notesSlide`) are separate from slide shapes/text boxes. If notes are empty, iterate `slide.shapes` or parse slide XML for `<a:t>` elements.
- **Fix**: If task says value is "in the slide" but notes are empty, check text boxes: `for shape in slide.shapes: if hasattr(shape, "text"): ...`
