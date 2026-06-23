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

```python
import zipfile
with zipfile.ZipFile('document.pptx', 'r') as z:
    for name in z.namelist():
        if 'embeddings' in name and name.endswith('.xlsx'):
            print(name)
```

### 2. Extract the Excel File

```python
with zipfile.ZipFile('document.pptx', 'r') as z:
    z.extract('ppt/embeddings/Microsoft_Excel_Sheet1.xlsx', '/tmp/workdir/')
```

### 3. Inspect Before Editing

**Critical:** Check if target cells are formulas or values before modifying.

```python
import openpyxl
wb = openpyxl.load_workbook('/tmp/workdir/ppt/embeddings/Microsoft_Excel_Sheet1.xlsx')
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

| Pattern | Why it fails | Alternative |
|---------|--------------|-------------|
| **python-pptx for OLE** | No robust support for embedded Excel objects | Use `zipfile` + `openpyxl` |
| **In-place ZIP modification** | Risk of corruption or partial writes | Create new archive, copy all entries |
| **Overwriting formula cells** | Breaks auto-calculation chain | Check `data_type == 'f'` first |
| **Assuming sheet names** | Embedded sheets vary (Sheet1, Spot Grid, etc.) | Inspect workbook first |
| **Shell `unzip` command** | Often unavailable in restricted environments | Use Python `zipfile` module |

## Common Pitfalls

| Mistake | Consequence | Prevention |
|---------|-------------|------------|
| Overwriting formula cells | Breaks auto-calculation | Always check `cell.data_type` before editing |
| Editing cached values | Changes lost on recalc | Edit the source value cell, not derived cells |
| Wrong embed path | File corruption | Verify exact path with `zipfile.namelist()` |
| ZIP compression mismatch | Office may reject file | Use `zipfile.ZIP_DEFLATED` consistently |
| Missing `[Content_Types].xml` | PPTX won't open | Copy ALL original entries to new archive |

## Decision Rules

- **If cell contains formula (`data_type == 'f'`)**: Find and edit the upstream value cell it references
- **If multiple Excel embeddings exist**: Extract all, identify correct one by sheet content, update, repackage all
- **If openpyxl unavailable**: Use `scripts/update_cell_zipfile.py` (pure zipfile/XML approach) or install with `--break-system-packages`

## Helper Scripts

- `scripts/update_embedded_excel.py`: Full argparse CLI with openpyxl, formula safety checks
- `scripts/update_cell_zipfile.py`: Pure zipfile/XML approach, no openpyxl dependency

## Fallback: Manual ZIP Editing

If Python zipfile fails:
```bash
unzip document.pptx -d pptx_extracted/
cp updated.xlsx pptx_extracted/ppt/embeddings/
cd pptx_extracted && zip -r ../new_document.pptx .
```

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### pptx-embedded-excel-edit
- Embedded Excel path format: `ppt/embeddings/Microsoft_Excel_Worksheet*.xlsx` or `Microsoft_Excel_Sheet*.xlsx`
- Formula cells auto-recalculate when opened in PowerPoint/Excel; do not pre-compute values

### docx-embedded-excel-edit
- Embedded Excel path format: `word/embeddings/Microsoft_Excel_Worksheet*.xlsx`