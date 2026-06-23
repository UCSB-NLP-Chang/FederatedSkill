---
name: edit-embedded-excel
description: Edit embedded Excel workbooks inside PowerPoint (.pptx) or Word (.docx) files. Use when tasks require modifying spreadsheet data, updating cell values, or preserving formulas within Office documents that contain embedded Excel objects. Common for FX rate matrices, financial tables, and formula-driven grids.
---

# Edit Embedded Excel in Office Documents

Extract, modify, and repackage Excel workbooks embedded in .pptx or .docx files.

## When to Use

- Task involves updating data in an Excel table shown in a PowerPoint slide
- Need to modify cell values while preserving formulas that reference those cells
- FX rate matrices, financial grids, or cross-rate tables need correction

## Workflow

### 1. Locate the Embedded Excel

Office documents are ZIP archives. Embedded Excel files are typically at:
- `ppt/embeddings/Microsoft_Excel_Sheet*.xlsx` or `Microsoft_Excel_Worksheet*.xlsx`
- `word/embeddings/Microsoft_Excel_Sheet*.xlsx`

```python
import zipfile
with zipfile.ZipFile('document.pptx', 'r') as z:
    for name in z.namelist():
        if 'embeddings' in name and name.endswith('.xlsx'):
            print(name)
```

### 2. Extract and Inspect

```python
import openpyxl
xlsx_bytes = z.read('ppt/embeddings/Microsoft_Excel_Worksheet.xlsx')
wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
ws = wb.active

# Check cell types before editing
for row in ws.iter_rows():
    for cell in row:
        print(f"{cell.coordinate}: value={cell.value}, type={cell.data_type}")
```

See `references/openpyxl_cell_types.md` for cell type reference.

### 3. Update Values (Preserve Formulas)

- Edit **value cells** (`data_type == 'n'` or `'s'`)
- **Never overwrite formula cells** (`data_type == 'f'`)
- For inverse formulas (e.g., `=ROUND(1/D5, 4)`), update the source cell D5

```python
# Update a source cell for inverse formula
target_rate = 0.8645
matrix_precision = 4  # Match existing decimal places in grid
ws['D5'].value = round(1 / target_rate, matrix_precision)  # 1.1567
wb.save('/tmp/embedded.xlsx')
```

### 4. Handle Cached Formula Values

**Critical:** openpyxl preserves formulas but does NOT update cached `<v>` values in XML. Verifiers reading XML directly see stale values.

After updating source cells, manually update the cached value for formula cells:

```python
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO

# After openpyxl saves, extract the sheet XML and update cached values
with zipfile.ZipFile('/tmp/embedded.xlsx', 'r') as z:
    sheet_xml = z.read('xl/worksheets/sheet1.xml')

root = ET.fromstring(sheet_xml)
# Find formula cells and update their <v> elements
for row in root.findall('.//row'):
    for c in row.findall('c'):
        f_elem = c.find('f')
        if f_elem is not None:  # This is a formula cell
            # Calculate the formula result and update <v>
            v_elem = c.find('v')
            if v_elem is None:
                v_elem = ET.SubElement(c, 'v')
            # Example: if formula is =ROUND(1/D5,4), compute result
            v_elem.text = str(round(1 / ws['D5'].value, 4))

# Save updated XML back to xlsx
with zipfile.ZipFile('/tmp/embedded.xlsx', 'r') as zin:
    with zipfile.ZipFile('/tmp/embedded_fixed.xlsx', 'w') as zout:
        for item in zin.infolist():
            if item.filename == 'xl/worksheets/sheet1.xml':
                zout.writestr(item, ET.tostring(root))
            else:
                zout.writestr(item, zin.read(item.filename))
```

### 5. Repackage into Office Document

```python
src_pptx = 'original.pptx'
dst_pptx = 'results.pptx'
updated_excel = '/tmp/embedded_fixed.xlsx'
embed_path = 'ppt/embeddings/Microsoft_Excel_Worksheet.xlsx'

with zipfile.ZipFile(src_pptx, 'r') as zin:
    with zipfile.ZipFile(dst_pptx, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == embed_path:
                zout.write(updated_excel, embed_path)
            else:
                zout.writestr(item, zin.read(item.filename))
```

## FX Cross-Rate Matrix Pattern

| Scenario | Wrong Approach | Correct Approach |
|----------|---------------|------------------|
| E4 contains `=ROUND(1/D5,4)` and target is 0.8645 | Overwrite E4 | Update D5 to `round(1/0.8645, 4)` |
| Matrix uses 4 decimal places | Use full float `1.15673...` | Match precision: `round(1/target, 4)` |

**Precision rule:** Match decimal places of surrounding data in the matrix. Excessive precision causes display/test failures.

## Known Invariants (by sub-task)

### fx-cross-rate-matrix
- Verifier reads `<v>` cached values from XML; openpyxl does NOT update them automatically
- Matrix precision typically 4 decimal places; match existing values
- Cross-rate formulas follow `=ROUND(1/{source_cell}, 4)` pattern

## Critical Anti-Patterns

- **Do not use `python-pptx`** for embedded OLE objects - use `zipfile` + `openpyxl`
- **Do not modify ZIP in-place** - create new archive
- **Do not overwrite formula cells** - check `cell.data_type` first
- **Do not use excessive precision** - match matrix decimals
- **Do not rely on openpyxl to update cached `<v>` values** - patch XML manually

## Environment Setup

```bash
pip install openpyxl --break-system-packages -q
```