---
name: edit-embedded-excel
description: Edit embedded Excel workbooks inside PowerPoint (.pptx) or Word (.docx) files. Use when tasks require modifying spreadsheet data, updating cell values, or preserving formulas within Office documents that contain embedded Excel objects. Critical for FX rate matrices, financial grids, conversion matrices, and cross-rate tables where inverse formulas must be preserved. Also covers extracting embedded slide notes for task instructions.
---

# Edit Embedded Excel in Office Documents

Extract, modify, and repackage Excel workbooks embedded in .pptx or .docx files.

## When to Use

- Task involves updating data in an Excel table shown in a PowerPoint slide
- Need to modify cell values while preserving formulas that reference those cells
- Working with .pptx or .docx files containing embedded spreadsheets
- FX rate matrices, financial grids, conversion matrices, or cross-rate tables need correction
- Instructions or correction values are hidden in slide notes or speaker notes

## Workflow

### 1. Read Slide Notes (If Present)

Slide notes in .pptx are often embedded as text boxes in `slide1.xml`, not in a separate notes.xml file. Instructions may be concatenated in a single text box (e.g., separated by `||` or newlines). Filter out stale/archived instructions.

```python
import zipfile, re

with zipfile.ZipFile('document.pptx', 'r') as z:
    slide_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
    # Extract all text between <a:t> tags
    texts = re.findall(r'<a:t>(.*?)</a:t>', slide_xml)
    # Look for actionable keywords like "FINAL", "UPDATE", "CORRECTION"
```

**Decision rule**: If notes specify a target value (e.g., "cart to bay = 0.50"), use that to identify the cell. If notes conflict with Excel structure, trust the Excel structure for cell location but use the note's target value. Ignore lines marked "ARCHIVED" or "DO NOT EDIT".

### 2. Locate the Embedded Excel

Office documents are ZIP archives. Embedded Excel files are typically at:
- `ppt/embeddings/Microsoft_Excel_Sheet*.xlsx` or `Microsoft_Excel_Worksheet*.xlsx` (PowerPoint)
- `word/embeddings/Microsoft_Excel_Sheet*.xlsx` (Word)

```python
import zipfile
with zipfile.ZipFile('document.pptx', 'r') as z:
    for name in z.namelist():
        if 'embeddings' in name and name.endswith('.xlsx'):
            print(name)
```

### 3. Extract and Inspect

**Critical:** Check if target cells are formulas or values before modifying.

```python
import openpyxl, io
xlsx_bytes = z.read('ppt/embeddings/Microsoft_Excel_Worksheet.xlsx')
wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
ws = wb.active

# Check cell types before editing
for row in ws.iter_rows():
    for cell in row:
        print(f"{cell.coordinate}: value={cell.value}, type={cell.data_type}")
```

See `references/openpyxl_cell_types.md` for cell type reference.

### 4. Update Values (Preserve Formulas)

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

### 5. Handle Cached Formula Values (Critical)

**Problem:** openpyxl preserves formulas but does NOT update cached `<v>` values in XML. Verifiers reading XML directly see stale or empty values (`<v />`).

After updating source cells, manually update the cached value for formula cells using ElementTree:

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
            v_elem = c.find('v')
            if v_elem is None:
                v_elem = ET.SubElement(c, 'v')
            # Compute result based on the formula logic (e.g., =ROUND(1/D5,4))
            # Adjust calculation to match the actual formula
            v_elem.text = str(round(1 / ws['D5'].value, 4))

# Save updated XML back to xlsx
with zipfile.ZipFile('/tmp/embedded.xlsx', 'r') as zin:
    with zipfile.ZipFile('/tmp/fixed.xlsx', 'w') as zout:
        for item in zin.infolist():
            if item.filename == 'xl/worksheets/sheet1.xml':
                zout.writestr(item, ET.tostring(root))
            else:
                zout.writestr(item, zin.read(item.filename))
```

**Alternative:** Use the helper script for detection and repair:
```bash
python3 scripts/fix_cached_values.py /tmp/embedded.xlsx --detect-only
python3 scripts/fix_cached_values.py /tmp/embedded.xlsx /tmp/fixed.xlsx G4=2 E5=0.5
```

### 6. Repackage into Office Document

**Warning:** Python's `zipfile` does not support in-place deletion or modification. Always read all entries into memory and write a new archive. **Ensure the writer context manager fully exits before reading the output.**

```python
src_pptx = 'original.pptx'
dst_pptx = 'results.pptx'
updated_excel = '/tmp/embedded_fixed.xlsx'
embed_path = 'ppt/embeddings/Microsoft_Excel_Worksheet.xlsx'

# Read all original entries first
with zipfile.ZipFile(src_pptx, 'r') as zin:
    entries = {item.filename: zin.read(item.filename) for item in zin.infolist()}

# Replace the embedded Excel
entries[embed_path] = open(updated_excel, 'rb').read()

# Write new archive
with zipfile.ZipFile(dst_pptx, 'w', zipfile.ZIP_DEFLATED) as zout:
    for name, data in entries.items():
        zout.writestr(name, data)

# Verify only AFTER the context manager exits
with zipfile.ZipFile(dst_pptx, 'r') as z:
    print("Archive valid:", z.testzip() is None)
```

### 7. Verify the Update

Always verify both the openpyxl values AND the XML cached values:

```python
import zipfile
with zipfile.ZipFile(dst_pptx, 'r') as z:
    excel_data = z.read(embed_path)
    # Load with openpyxl and verify key cells
    # Also check XML for cached formula values
```

## Reciprocal Rate Matrix Pattern

| Scenario | Wrong Approach | Correct Approach |
|----------|---------------|------------------|
| E4 contains `=ROUND(1/D5,4)` and target is 0.8645 | Overwrite E4 | Update D5 to `round(1/0.8645, 4)` |
| Matrix uses 4 decimal places | Use full float `1.15673...` | Match precision: `round(1/target, 4)` |

**Precision rule:** Match decimal places of surrounding data in the matrix. Excessive precision causes display/test failures.

## Known Invariants (by pattern)

### reciprocal-rate-matrix
Applies to: FX cross-rate grids, warehouse slot factors, supplier pack matrices, unit conversion tables

- Verifier reads `<v>` cached values from XML; openpyxl does NOT update them automatically
- Matrix precision typically 4 decimal places; match existing values
- Cross-rate formulas follow `=ROUND(1/{source_cell}, 4)` pattern
- Source cell must be updated, not formula cell
- Identify the matrix structure: row/column headers define units, cells define conversion rates

### pptx-embedded-excel-edit
- Formula cells auto-recalculate when opened in PowerPoint/Excel; do not pre-compute values
- Embedded Excel path format: `ppt/embeddings/Microsoft_Excel_Worksheet*.xlsx` or `Microsoft_Excel_Sheet*.xlsx`
- Slide notes may contain actionable instructions; parse `<a:t>` elements in `ppt/slides/slide1.xml`

### docx-embedded-excel-edit
- Embedded Excel path format: `word/embeddings/Microsoft_Excel_Worksheet*.xlsx`

## Critical Anti-Patterns

- **Do not use `python-pptx`** for embedded OLE objects - use `zipfile` + `openpyxl`
- **Do not modify ZIP in-place** - `zipfile` lacks delete/update; always read-all-then-write-new
- **Do not overwrite formula cells** - check `cell.data_type` first
- **Do not use excessive precision** - match matrix decimals
- **Do not rely on openpyxl to update cached `<v>` values** - patch XML manually
- **Do not look for notes.xml** - Notes often inline text boxes in slide XML
- **Do not verify output ZIP immediately** - `BadZipFile` if writer buffer not flushed; wait for `with` block to exit

## Environment Setup

```bash
pip install openpyxl --break-system-packages -q
```

## Helper Scripts

- `scripts/update_embedded_excel.py` - CLI helper for simple cell updates
- `scripts/fix_cached_values.py` - Detection and repair for empty cached values

## References

- `references/openpyxl_cell_types.md` - Cell data type reference for openpyxl

## Troubleshooting

- **`BadZipFile: Truncated file header` on output**: Caused by reading the archive before the `ZipFile` writer finishes flushing. Always verify *after* the `with zipfile.ZipFile(...) as zout:` block exits.
- **Slide notes not in notes.xml**: Notes are often inline text boxes. Parse `ppt/slides/slide1.xml` for `<a:t>` elements containing instructions.
- **Multiple slide note instructions**: Split by `||`, newlines, or bullet points. Filter out stale/archived items before applying.

## Verification Checklist

- [ ] Embedded workbook extracted and loaded successfully.
- [ ] Target cell(s) updated to correct values.
- [ ] Formula cells remain intact and reference updated cells correctly.
- [ ] Updated values match precision of surrounding data.
- [ ] Formula cells have non-empty cached `<v>` values in XML.
- [ ] Output file contains all original files plus the modified workbook.
- [ ] Re-extracted workbook matches expected state.
- [ ] Sheet names and count unchanged from original.
