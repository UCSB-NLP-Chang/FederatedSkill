# OpenXML Structures for Embedded Excel

## File Locations in PPTX

```
input.pptx (ZIP)
├── [Content_Types].xml          # Must preserve exactly
├── _rels/.rels                  # Package relationships
├── ppt/
│   ├── slides/
│   │   └── slide1.xml           # Slide content including text boxes
│   ├── embeddings/
│   │   └── Microsoft_Excel_Worksheet.xlsx   # Target Excel file
│   └── ...
```

## Extracting Text from Slides

When directed to find correction values in slide content:

### Using python-pptx
```python
from pptx import Presentation
prs = Presentation('input.pptx')
slide = prs.slides[0]
for shape in slide.shapes:
    if hasattr(shape, "text") and shape.text:
        print(f"Text: {shape.text}")
```

### Using XML parsing (if python-pptx unavailable)
```python
import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile('input.pptx') as z:
    xml = z.read('ppt/slides/slide1.xml')
    root = ET.fromstring(xml)
    # Text is in <a:t> elements within DrawingML
    ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
    texts = [t.text for t in root.findall('.//a:t', ns) if t.text]
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

## Using openpyxl (Preferred when available)

```python
import zipfile
import openpyxl
import io

# Extract
with zipfile.ZipFile('input.pptx') as z:
    xlsx_bytes = z.read('ppt/embeddings/Microsoft_Excel_Worksheet.xlsx')

# Modify
wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
ws = wb.active
ws['E6'] = 0.5  # Raw float, no rounding
new_xlsx = io.BytesIO()
wb.save(new_xlsx)

# Repack
with zipfile.ZipFile('input.pptx', 'r') as zin:
    with zipfile.ZipFile('output.pptx', 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == 'ppt/embeddings/Microsoft_Excel_Worksheet.xlsx':
                zout.writestr(item, new_xlsx.getvalue())
            else:
                zout.writestr(item, zin.read(item.filename))
```

## Critical Namespaces

```python
NS = {
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'
}
```

## Reassembly Notes

- Use `zipfile.ZipFile` with mode `'w'` and `compress_type=zipfile.ZIP_DEFLATED`
- **Always iterate `infolist()` and pass the original `ZipInfo` object to `writestr()`**. This preserves timestamps, compression flags, external attributes, and CRC values.
- Maintain original file order if possible (though usually not strictly required)
- Do not modify `[Content_Types].xml` unless adding new parts

### WRONG: Dict-based reconstruction (strips metadata)
```python
# DO NOT DO THIS — loses ZipInfo metadata
with zipfile.ZipFile('input.pptx', 'r') as z_in:
    zip_data = {name: z_in.read(name) for name in z_in.namelist()}
zip_data['ppt/embeddings/Microsoft_Excel_Worksheet.xlsx'] = new_bytes
with zipfile.ZipFile('output.pptx', 'w', zipfile.ZIP_DEFLATED) as z_out:
    for name, data in zip_data.items():
        z_out.writestr(name, data)  # Missing ZipInfo!
```

### RIGHT: ZipInfo-preserving copy
```python
# DO THIS — preserves all original metadata
with zipfile.ZipFile('input.pptx', 'r') as zin:
    with zipfile.ZipFile('output.pptx', 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == 'ppt/embeddings/Microsoft_Excel_Worksheet.xlsx':
                zout.writestr(item, new_bytes)  # item is ZipInfo
            else:
                zout.writestr(item, zin.read(item.filename))
```

## Common Failure Patterns

### Searching for internal instructions when not directed
- **Problem**: Searching for "slide notes" or other text fields for correction values when the task says "the note contains the correction."
- **Reality**: Only search file internals when explicitly directed by the task description.
- **Fix**: Read correction values directly from task instructions unless task explicitly says to look in file content.

### Confusing notes with text boxes
- **Problem**: Checking `slide.has_notes_slide` and finding nothing, missing the text box on the slide itself.
- **Reality**: Notes are separate from slide content/shapes.
- **Fix**: If notes are empty, iterate slide shapes or parse slide1.xml for text elements.

### Arbitrary correction values
- **Problem**: Using an arbitrary value when the specific correction value is unclear.
- **Reality**: Verifier expects exact match to task-provided value.
- **Fix**: If multiple candidates exist, list them and identify the correct one from task context. Never guess.

### Namespace stripping
- **Problem**: Removing namespace declarations during XML parse/repack.
- **Reality**: Office XML files require namespaces for Excel to open them correctly.
- **Fix**: Register namespaces with ElementTree and use full URIs in XPath queries.

### Precision loss in derived calculations
- **Problem**: Computing `1/0.8645` and writing `1.1567` (rounded to 4 decimals).
- **Reality**: Verifier may expect full precision; rounding introduces error that compounds.
- **Fix**: Write `repr(1/0.8645)` or compute in Python and write the full float representation. Never round intermediate calculations.

### ZIP metadata loss causing verifier rejection
- **Problem**: Using dict-based ZIP reconstruction (`{name: data}`) strips ZipInfo metadata, producing a structurally different archive.
- **Reality**: Verifiers may check file structure, timestamps, or entry metadata, not just content.
- **Fix**: Always use the `infolist()`-preserving repack pattern. Pass the original `ZipInfo` object to `writestr()`.
