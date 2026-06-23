---
name: edit-embedded-excel
description: Edit embedded Excel workbooks inside PowerPoint (.pptx) or Word (.docx) files. Use when tasks require modifying spreadsheet data, updating cell values, or preserving formulas within Office documents that contain embedded Excel objects. Critical for cross-rate calculations where formulas like =ROUND(1/A1,4) must be preserved while updating source values. Also use when slide notes contain update instructions that must be parsed to identify target cells.
---

# Edit Embedded Excel in Office Documents

Extract, modify, and repackage Excel workbooks embedded in .pptx or .docx files.

## When to Use

- Task involves updating data in an Excel table shown in a PowerPoint slide
- Need to modify cell values while preserving formulas that reference those cells
- Working with .pptx or .docx files containing embedded spreadsheets
- **Cross-rate updates**: When a cell contains `=ROUND(1/A1, 4)`, update A1 (the source rate), not the formula cell
- **Slide note instructions**: Task mentions corrections or updates described in slide notes (e.g., "FINAL slot-factor correction: cart to bay = 0.50")

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

### 3. Extract the Excel File

```python
with zipfile.ZipFile('document.pptx', 'r') as z:
    z.extract('ppt/embeddings/Microsoft_Excel_Worksheet.xlsx', '/tmp/workdir/')
```

### 4. Inspect Before Editing

**Critical:** Check if target cells are formulas or values before modifying.

```python
import openpyxl
wb = openpyxl.load_workbook('/tmp/workdir/ppt/embeddings/Microsoft_Excel_Worksheet.xlsx')
ws = wb['Sheet Name']

# Check cell type
cell = ws['C4']
print(f"Value: {cell.value}")
print(f"Type: {cell.data_type}")  # 'n'=number, 'f'=formula
print(f"Is formula: {cell.data_type == 'f'}")
```

### 5. Update Values (Preserve Formulas)

- Edit **value cells** (`data_type == 'n'` or `'s'`)
- **Never overwrite formula cells** (`data_type == 'f'`) unless explicitly required
- Formulas referencing updated values will recalculate automatically when opened

```python
# Update a numeric value
ws['C4'].value = 1.1590
wb.save('/tmp/embedded.xlsx')
```

### 6. Repackage into Office Document

Replace the embedded Excel in the original ZIP structure. **Ensure the writer context manager fully exits before reading the output.**

```python
import zipfile
import os

src_pptx = '/root/original.pptx'
dst_pptx = '/root/results.pptx'
updated_excel = '/tmp/embedded.xlsx'
embed_path = 'ppt/embeddings/Microsoft_Excel_Worksheet.xlsx'

# Create new PPTX with updated Excel
with zipfile.ZipFile(src_pptx, 'r') as zin:
    with zipfile.ZipFile(dst_pptx, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == embed_path:
                zout.write(updated_excel, embed_path)
            else:
                zout.writestr(item, zin.read(item.filename))

# Verify only AFTER the context manager exits
with zipfile.ZipFile(dst_pptx, 'r') as z:
    print("Archive valid:", z.testzip() is None)
```

### 7. Verify the Update

```python
import zipfile
with zipfile.ZipFile(dst_pptx, 'r') as z:
    excel_data = z.read(embed_path)
    # Load with openpyxl and verify key cells
```

## Cross-Rate Pattern (Critical)

When updating FX rates or reciprocal calculations:

| Scenario | Wrong Approach | Correct Approach |
|----------|---------------|------------------|
| EUR/GBP = 0.8645, cell E4 has `=ROUND(1/D5,4)` | Update E4 directly | Update D5 to `1/0.8645` (full precision) |
| Target rate given | Overwrite formula cell | Calculate reciprocal, update source cell |

**Precision rule**: Use full float precision for reciprocal calculations. Do not round intermediate values:

```python
# Correct: full precision
target_rate = 0.8645
source_cell.value = 1.0 / target_rate  # Pass raw float

# Wrong: premature rounding
source_cell.value = round(1.0 / target_rate, 4)  # Loses precision
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
| **Premature rounding** | Precision loss in cross-rates | Store full float, let Excel round on display |
| **Trusting slide notes alone** | Notes may be stale or ambiguous | Cross-check with Excel structure |
| **Relying on openpyxl for cached values** | openpyxl preserves formulas but does NOT recompute `<v>` tags | Manually patch XML or use formula evaluator |
| **Looking for notes.xml** | Notes often embedded as text boxes in slide XML | Parse `ppt/slides/slide1.xml` for `<a:t>` text elements |
| **Reading output ZIP immediately** | `BadZipFile` if writer buffer not flushed/closed | Wait for `with` block to exit, or call `zout.close()` explicitly |

## Common Pitfalls

| Mistake | Consequence | Prevention |
|---------|-------------|------------|
| Overwriting formula cells | Breaks auto-calculation | Always check `cell.data_type` before editing |
| Editing cached values | Changes lost on recalc | Edit the source value cell, not derived cells |
| Wrong embed path | File corruption | Verify exact path with `zipfile.namelist()` |
| ZIP compression mismatch | Office may reject file | Use `zipfile.ZIP_DEFLATED` consistently |
| Missing `[Content_Types].xml` | PPTX won't open | Copy ALL original entries to new archive |
| Reciprocal precision loss | Rate doesn't match target | Use `1.0 / target` not `round(1/target, 4)` |
| Ignoring slide notes | Miss explicit update instructions | Always check slide XML for `<a:t>` text boxes |
| Verifying before ZIP closes | `BadZipFile` or truncated header | Ensure writer context exits before reading output |

## Decision Rules

- **If cell contains formula (`data_type == 'f'`)**: Find and edit the upstream value cell it references
- **If multiple Excel embeddings exist**: Extract all, identify correct one by sheet content, update, repackage all
- **If openpyxl unavailable**: Use `scripts/update_cell_zipfile.py` (pure zipfile/XML approach) or install with `--break-system-packages`
- **If target rate is given for a formula cell**: Calculate reciprocal with full precision, update the source cell
- **If slide note conflicts with Excel structure**: Trust the Excel structure for cell location; use note's target value
- **If slide notes contain update instructions**: Parse the note text to extract target cell description and value, then map to actual cell coordinates via Excel inspection
- **If slide notes contain multiple instructions**: Split by `||`, newlines, or bullet points. Filter out stale/archived items before applying.

## Troubleshooting

- **File not found in embeddings**: Check `.rels` files for `rId` references. The path may vary.
- **Corrupted output**: Ensure all original files are copied, including `[Content_Types].xml` and `_rels/`.
- **Formulas not calculating**: `openpyxl` does not evaluate formulas. Host app computes on open. Only update source data cells.
- **Verifier checks cached `<v>` values**: If tests read `<v>` tags from XML to verify formula results, openpyxl won't update them automatically. You may need to:
  1. Manually patch the XML `<v>` element inside the xlsx (open xlsx as ZIP, edit `xl/worksheets/sheet*.xml`)
  2. Use a formula evaluation library (e.g., `xlcalculator`) to compute the expected result and write it to `<v>`
  3. Force a recalculation trigger (e.g., set `calcMode` attribute)
- **openpyxl not installed**: `pip install openpyxl --break-system-packages -q`
- **Slide notes not in notes.xml**: Notes are often inline text boxes. Parse `ppt/slides/slide1.xml` for `<a:t>` elements containing instructions.
- **`BadZipFile: Truncated file header` on output**: Caused by reading the archive before the `ZipFile` writer finishes flushing. Always verify *after* the `with zipfile.ZipFile(...) as zout:` block exits.

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

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known Invariants (by sub-task)

### fx-cross-rate-matrix
- Cross-rate formulas typically follow `=ROUND(1/{source_cell}, 4)` pattern
- When target rate given for formula cell, update source cell with reciprocal
- **Critical**: Verifiers may read cached `<v>` values from XML; openpyxl does NOT update these
- Embedded Excel path format: `ppt/embeddings/Microsoft_Excel_Worksheet*.xlsx` or `Microsoft_Excel_Sheet*.xlsx`

### pptx-embedded-excel-edit
- Formula cells auto-recalculate when opened in PowerPoint/Excel; do not pre-compute values
- Embedded Excel path format: `ppt/embeddings/Microsoft_Excel_Worksheet*.xlsx` or `Microsoft_Excel_Sheet*.xlsx`
- Slide notes may contain actionable instructions; parse `<a:t>` elements in `ppt/slides/slide1.xml`

### docx-embedded-excel-edit
- Embedded Excel path format: `word/embeddings/Microsoft_Excel_Worksheet*.xlsx`

### warehouse-slot-factor-refresh
- Slot-factor matrices use reciprocal formulas: `=ROUND(1/{source_cell}, 4)`
- Notes indicate target value (e.g., "cart to bay = 0.50") but cell must be located via Excel inspection
- Update the numeric source cell, not the formula cell that references it

## References

- `references/openpyxl_cell_types.md` - Cell data type reference for openpyxl