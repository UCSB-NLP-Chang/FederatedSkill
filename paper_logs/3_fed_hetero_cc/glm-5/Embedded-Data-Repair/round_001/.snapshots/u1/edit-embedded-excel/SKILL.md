---
name: edit-embedded-excel
description: Edit embedded Excel workbooks inside PowerPoint (.pptx) or Word (.docx) files. Use when tasks require modifying spreadsheet data, updating cell values, or preserving formulas within Office documents that contain embedded Excel objects.
---

# Edit Embedded Excel in Office Documents

Extract, modify, and repackage Excel workbooks embedded in .pptx or .docx files.

## When to Use

- Task involves updating data in an Excel table shown in a PowerPoint slide
- Need to modify cell values while preserving formulas that reference those cells
- Working with .pptx or .docx files containing embedded spreadsheets

## Workflow

### 1. Locate the Embedded Excel

Office documents are ZIP archives. Embedded Excel files are typically at:
- `ppt/embeddings/Microsoft_Excel_Sheet*.xlsx` (PowerPoint)
- `word/embeddings/Microsoft_Excel_Sheet*.xlsx` (Word)

```bash
unzip -l document.pptx | grep -i excel
```

### 2. Extract the Excel File

```bash
unzip document.pptx ppt/embeddings/Microsoft_Excel_Sheet1.xlsx -d /tmp/workdir/
cp /tmp/workdir/ppt/embeddings/Microsoft_Excel_Sheet1.xlsx /tmp/embedded.xlsx
```

### 3. Inspect Before Editing

**Critical:** Check if target cells are formulas or values before modifying.

```python
import openpyxl
wb = openpyxl.load_workbook('/tmp/embedded.xlsx')
ws = wb['Sheet Name']

# Check cell type
cell = ws['C4']
print(f"Value: {cell.value}")
print(f"Type: {cell.data_type}")  # 'n'=number, 'f'=formula
print(f"Is formula: {cell.data_type == 'f'}")
```

### 4. Update Values (Preserve Formulas)

- Edit **value cells** (`data_type == 'n'` or `'s'`)
- **Never overwrite formula cells** (`data_type == 'f'`) unless explicitly required
- Formulas referencing updated values will recalculate automatically when opened

```python
# Update a numeric value
ws['C4'].value = 1.1590
wb.save('/tmp/embedded.xlsx')
```

### 5. Repackage into Office Document

Replace the embedded Excel in the original ZIP structure:

```python
import zipfile
import shutil
import os

src_pptx = '/root/original.pptx'
dst_pptx = '/root/results.pptx'
updated_excel = '/tmp/embedded.xlsx'
embed_path = 'ppt/embeddings/Microsoft_Excel_Sheet1.xlsx'

# Create new PPTX with updated Excel
with zipfile.ZipFile(src_pptx, 'r') as zin:
    with zipfile.ZipFile(dst_pptx, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == embed_path:
                zout.write(updated_excel, embed_path)
            else:
                zout.writestr(item, zin.read(item.filename))
```

### 6. Verify the Update

```python
import zipfile
with zipfile.ZipFile(dst_pptx, 'r') as z:
    excel_data = z.read(embed_path)
    # Load with openpyxl and verify key cells
```

## Environment Setup

If `openpyxl` is not available and pip fails with "externally-managed-environment":

```bash
pip install openpyxl --break-system-packages -q
```

## Critical Anti-Patterns

- **Do not use `python-pptx`** for embedded OLE objects. It lacks robust support for reading/modifying embedded Excel files. Use `zipfile` + `openpyxl`.
- **Do not modify the PPTX ZIP in-place**. Always create a new archive to avoid corruption or partial writes.
- **Do not overwrite formula cells** unless explicitly told to. Reciprocal or dependent cells often rely on formulas (e.g., `=ROUND(1/C4, 4)`).
- **Do not assume sheet names**. Always inspect the workbook structure first. Embedded sheets are often named "Sheet1", "Spot Grid", or similar.

## Common Pitfalls

| Mistake | Consequence | Prevention |
|---------|-------------|------------|
| Overwriting formula cells | Breaks auto-calculation | Always check `cell.data_type` before editing |
| Editing cached values | Changes lost on recalc | Edit the source value cell, not derived cells |
| Wrong embed path | File corruption | Verify exact path with `unzip -l` |
| ZIP compression mismatch | Office may reject file | Use `zipfile.ZIP_DEFLATED` consistently |

## Decision Rules

- **If cell contains formula (`data_type == 'f'`)**: Find and edit the upstream value cell it references
- **If multiple Excel embeddings exist**: Extract all, identify correct one by sheet content, update, repackage all
- **If openpyxl unavailable**: Consider `xlrd`/`xlwt` for older .xls, or install with `--break-system-packages`

## Fallback: Manual ZIP Editing

If Python zipfile fails:
```bash
# Extract entire PPTX
unzip document.pptx -d pptx_extracted/
# Replace Excel file
cp updated.xlsx pptx_extracted/ppt/embeddings/
# Repackage
cd pptx_extracted && zip -r ../new_document.pptx .
```

## Verification Checklist

- [ ] Embedded workbook extracted and loaded successfully.
- [ ] Target cell(s) updated to correct values.
- [ ] Formula cells remain intact and reference updated cells correctly.
- [ ] Output file contains all original files plus the modified workbook.
- [ ] Re-extracted workbook matches expected state.

## Known invariants (by sub-task)

(No sub-task variants identified yet in R0. Update this section when verifier messages reveal task-specific invariants.)