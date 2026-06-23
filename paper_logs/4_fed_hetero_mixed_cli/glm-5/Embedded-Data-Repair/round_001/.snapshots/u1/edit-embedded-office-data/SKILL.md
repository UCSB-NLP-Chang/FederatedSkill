---
name: edit-embedded-office-data
description: Modify embedded Office documents (Excel workbooks, Word documents) inside PowerPoint or other Office containers. Use when you need to edit embedded charts, tables, or workbooks that high-level libraries cannot access directly.
---

# Edit Embedded Office Documents

## When to Use
- Editing embedded Excel workbooks inside PowerPoint presentations
- Modifying embedded charts or tables where the data source is an internal workbook
- Updating linked or embedded OLE objects in Office documents
- High-level libraries (python-pptx, openpyxl) cannot access embedded content

## Workflow

### 1. Extract the Container Document
```bash
unzip -d /root/pptx_extract /root/input.pptx
```
**Fallback**: If `unzip` CLI is unavailable, use Python's `zipfile` module:
```python
import zipfile
with zipfile.ZipFile('/root/input.pptx', 'r') as zf:
    zf.extractall('/root/pptx_extract')
```

### 2. Locate the Embedded Document
- PowerPoint: `ppt/embeddings/` directory
- Word: `word/embeddings/` directory
- Files are typically named `Microsoft_Excel_Worksheet.xlsx` or similar

### 3. Extract the Embedded Document
```bash
unzip -d /root/xlsx_extract /root/pptx_extract/ppt/embeddings/Microsoft_Excel_Worksheet.xlsx
```
**Fallback**: Use Python's `zipfile` module if `unzip` unavailable.

### 4. Edit the XML Directly
For Excel workbooks:
- Worksheet data: `xl/worksheets/sheet1.xml`
- Cell values: `<c r="A1" t="n"><v>1.234</v></c>`
- Cell formulas: `<c r="B1"><f>ROUND(A1, 2)</f><v/></c>`
- Preserve formulas when editing values; formulas are in `<f>` tags, values in `<v>` tags

**Helper script available**: See `scripts/update_embedded_xlsx.py` for a deterministic, namespace-safe cell update.

### 5. Repackage the Embedded Document
```python
import zipfile
import os

with zipfile.ZipFile('/root/updated_workbook.xlsx', 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('/root/xlsx_extract'):
        for f in files:
            path = os.path.join(root, f)
            arcname = os.path.relpath(path, '/root/xlsx_extract')
            zf.write(path, arcname)
```

### 6. Replace in Container and Repackage
```bash
cp /root/updated_workbook.xlsx /root/pptx_extract/ppt/embeddings/Microsoft_Excel_Worksheet.xlsx
```

Then repackage the PPTX using the same ZIP method.

### 7. Verify the Result
Always extract and verify the final output:
```python
import zipfile
with zipfile.ZipFile('/root/results.pptx', 'r') as zf:
    # Extract and check the embedded workbook
    with zf.open('ppt/embeddings/Microsoft_Excel_Worksheet.xlsx') as emb:
        # Further verify the specific cell values
```

## XML Structure Reference

### Excel Cell Types
- `t="n"` - numeric value
- `t="inlineStr"` - inline string (contains `<is><t>text</t></is>`)
- `t="s"` - shared string (value is index into sharedStrings.xml)
- No `t` attribute with `<f>` - formula cell

### Preserving Formulas
When editing a cell that has a formula:
- The formula is in `<f>...</f>`
- The cached value is in `<v>...</v>`
- Edit only the value if needed; do not remove the formula tag

See `references/openxml-structures.md` for detailed namespace and schema information.

## Anti-Patterns
- Do not use python-pptx or openpyxl for embedded content - they cannot access it
- Do not forget to preserve the XML namespace declarations when editing
- Do not skip verification - always confirm the final output contains your changes
- Do not edit shared strings without updating `xl/sharedStrings.xml`
- Do not search for "slide notes" or "correction instructions" inside the file unless explicitly told they exist as text fields — correction values come from the task prompt, not file internals
- Do not use arbitrary correction values if the specific value is unclear — list candidates and identify the target from task instructions

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### embedded-excel-fx-rate-update
- Formulas referencing updated cells (e.g., `ROUND(1/C4, 4)` for cross-rates) must be preserved — they recalculate on open.
- Base rate cells are static values (`t="n"` without `<f>`); derived rates are formula cells.
- Correction value is provided in the task prompt, not within the file.

## Troubleshooting
- If the file won't open after editing, check XML well-formedness
- If formulas show errors, verify cell references are correct
- If changes don't appear, confirm you edited the correct sheet in the correct embedded file
- If `unzip` CLI fails, use Python `zipfile` module as fallback

## Helper Scripts
- `scripts/update_embedded_xlsx.py`: Run this script for deterministic, namespace-safe cell updates in embedded workbooks. Pass host file, embed path, cell reference, new value, and output path as arguments.