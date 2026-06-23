---
name: edit-embedded-excel
description: Edit embedded Excel workbooks inside PowerPoint (.pptx) or Word (.docx) files. Use when tasks require modifying spreadsheet data, updating cell values, or preserving formulas within Office documents that contain embedded Excel objects. Critical for FX rate matrices, financial grids, and cross-rate tables where inverse formulas must be preserved.
---

# Edit Embedded Excel in Office Documents

Extract, modify, and repackage Excel workbooks embedded in .pptx or .docx files.

## When to Use

- Task involves updating data in an Excel table shown in a PowerPoint slide
- Need to modify cell values while preserving formulas that reference those cells
- Working with .pptx or .docx files containing embedded spreadsheets
- FX rate matrices, financial grids, or cross-rate tables need correction

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

## Common Patterns

### FX Cross-Rate Matrices

FX matrices often use inverse formulas like `=ROUND(1/X, N)` to display reciprocal rates. When the target rate is in a formula cell:

1. Identify the source cell the formula references
2. Calculate the inverse: `source_value = 1 / target_rate`
3. **Round to match existing precision** in the matrix (see Precision Consistency below)
4. Update the source cell, not the formula cell

**Example:** If E4 contains `=ROUND(1/D5, 4)` and you need EUR→GBP = 0.8645:
- D5 should be `round(1 / 0.8645, 4) = 1.1567` (4 decimals to match matrix)
- Do NOT overwrite E4's formula

### Precision Consistency

When updating numeric values in financial grids:
- **Match the decimal precision of surrounding data**
- If original values use 4 decimal places (e.g., 1.1498), use 4 decimal places in updates
- Excessive precision (e.g., 1.156737998843262) may cause display issues or test failures
- Use `round(value, decimals)` to match the matrix precision

```python
# Wrong: excessive precision
ws['D5'].value = 1 / 0.8645  # 1.156737998843262

# Correct: match matrix precision (4 decimals)
ws['D5'].value = round(1 / 0.8645, 4)  # 1.1567
```

## Cached Formula Values (Critical for B2)

**Problem:** openpyxl preserves formulas but does NOT recompute the cached `<v>` result values stored in the worksheet XML. Verifiers that read XML directly (not via Excel) see stale `<v>` values.

**Detection:** If the verifier expects formula cells to show updated results after your edit, and tests fail with "expected X, got Y" for formula output cells, the cached values issue is likely the cause.

**Workarounds:**

1. **Manual XML patch:** After openpyxl save, parse the worksheet XML and update `<v>` elements for formula cells to reflect calculated results:
   ```python
   # Extract worksheet XML from saved xlsx
   # Find <c r="E4"><f>ROUND(1/D5,4)</f><v>0.8645</v></c>
   # Update <v> to calculated value based on updated D5
   ```

2. **Formula evaluation library:** Use `xlcalculator` or similar to evaluate formulas after openpyxl edits:
   ```python
   from xlcalculator import ModelCompiler, Model, Evaluator
   # Evaluate and write computed values to <v> tags
   ```

3. **Force recalc trigger:** Some Office apps recalculate on open if workbook has calculation pending flag. Not guaranteed for XML verifiers.

**Decision rule:** If verifier reads XML `<v>` tags directly, you must update them manually. If verifier opens in Excel first, cached values auto-refresh.

## Environment Setup

If `openpyxl` is not available and pip fails with "externally-managed-environment":

```bash
pip install openpyxl --break-system-packages -q
```

## Critical Anti-Patterns

- **Do not use `python-pptx`** for embedded OLE objects. It lacks robust support for reading/modifying embedded Excel files. Use `zipfile` + `openpyxl`.
- **Do not modify the PPTX ZIP in-place**. Always create a new archive to avoid corruption or partial writes.
- **Do not overwrite formula cells** unless explicitly told to. Reciprocal or dependent cells often rely on formulas (e.g., `=ROUND(1/C4, 4)`).
- **Do not assume sheet names**. Always inspect the workbook structure first. Embedded sheets are often named "Sheet1", "Spot Grid", "FX Matrix", or similar.
- **Do not use excessive decimal precision**. Match the precision of existing values in the spreadsheet.

## Common Pitfalls

| Mistake | Consequence | Prevention |
|---------|-------------|------------|
| Overwriting formula cells | Breaks auto-calculation | Always check `cell.data_type` before editing |
| Editing cached values | Changes lost on recalc | Edit the source value cell, not derived cells |
| Wrong embed path | File corruption | Verify exact path with `unzip -l` |
| ZIP compression mismatch | Office may reject file | Use `zipfile.ZIP_DEFLATED` consistently |
| Excessive precision | Display/test failures | Match decimal places of surrounding data |
| Stale cached `<v>` values | XML verifiers see wrong results | Manually update `<v>` tags or use formula evaluator |

## Decision Rules

- **If cell contains formula (`data_type == 'f'`)**: Find and edit the upstream value cell it references
- **If multiple Excel embeddings exist**: Extract all, identify correct one by sheet content, update, repackage all
- **If openpyxl unavailable**: Consider `xlrd`/`xlwt` for older .xls, or install with `--break-system-packages`
- **If updating inverse rate**: Calculate `source = 1/target`, round to match matrix precision
- **If verifier reads XML directly**: Update cached `<v>` values after openpyxl edits

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
- [ ] Updated values match precision of surrounding data.
- [ ] Output file contains all original files plus the modified workbook.
- [ ] Re-extracted workbook matches expected state.
- [ ] If verifier reads XML `<v>` tags, cached values updated appropriately.

## References

- `references/openpyxl_cell_types.md` - Cell data type reference for openpyxl
- `scripts/update_embedded_excel.py` - CLI helper for simple cell updates

## Known invariants (by sub-task)

### B1: Basic embedded Excel cell updates
- Standard workflow applies. No special handling needed.

### B2: FX Cross-Rate Matrix with Inverse Formulas
- Source cell must be updated, not formula cell.
- Precision: round to match matrix decimals (typically 4 for FX rates).
- **Cached `<v>` values in XML do NOT auto-update** — verifiers reading XML directly require manual `<v>` patch or formula evaluation.
- Slide notes may contain update instructions but should be cross-checked with Excel structure.