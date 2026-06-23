---
name: edit-embedded-office-xml
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

### 4. Identify the Correct Sheet (Multi-Sheet Workbooks)
Many embedded workbooks have multiple sheets. Always check which sheet contains the target data:

1. Read `xl/workbook.xml` to see sheet names and relationship IDs:
```xml
<sheets>
  <sheet name="Readme" sheetId="1" r:id="rId1"/>
  <sheet name="Live Pack Matrix" sheetId="2" r:id="rId2"/>
</sheets>
```
2. Map rId to sheet file: `rId1` → `xl/worksheets/sheet1.xml`, `rId2` → `xl/worksheets/sheet2.xml`
3. Edit the correct sheet based on the task context (e.g., ignore "Readme" sheets)

### 5. Edit the XML Directly
For Excel workbooks:
- Worksheet data: `xl/worksheets/sheetN.xml` (use step 4 to identify N)
- Cell values: `<c r="A1" t="n"><v>1.234</v></c>`
- Cell formulas: `<c r="B1"><f>ROUND(A1, 2)</f><v/></c>`
- Preserve formulas when editing values; formulas are in `<f>` tags, values in `<v>` tags

**Helper script available**: See `scripts/update_embedded_xlsx.py` for a deterministic, namespace-safe cell update.

### 6. Repackage the Embedded Document
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

### 7. Replace in Container and Repackage
```bash
cp /root/updated_workbook.xlsx /root/pptx_extract/ppt/embeddings/Microsoft_Excel_Worksheet.xlsx
```

Then repackage the PPTX using the same ZIP method.

### 8. Verify the Result
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
- Do not search for correction instructions in slide content unless the task explicitly indicates they are there. Correction values typically come from the task prompt; only look in slide text boxes or notes when instructed.
- Do not use arbitrary correction values if the specific value is unclear — list candidates and identify the target from task instructions
- Do not assume sheet1.xml contains the target data — check workbook.xml for sheet names and edit the correct sheet

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Calculation precision (critical)
When computing derived values, use full precision throughout:
- DO NOT: `1/0.8645 ≈ 1.1567` (rounded intermediate)
- DO: Write `1/0.8645` directly or use `repr(1/0.8645)` for full precision string
- Compute in Python: `value = 1 / 0.8645` then write `repr(value)` or `str(value)`
- Never round intermediate calculations — the target precision is unknown
- For inverse rates: if target is `X`, write `1/X` exactly, not a rounded approximation

## Known invariants (by sub-task)

### embedded-excel-fx-rate-update
- Formulas referencing updated cells (e.g., `ROUND(1/C4, 4)` for cross-rates) must be preserved — they recalculate on open.
- Base rate cells are static values (`t="n"` without `<f>`); derived rates are formula cells.
- Correction value is provided in the task prompt, not within the file.
- When target specifies a derived rate (e.g., "EUR to GBP = 0.8645"), compute the inverse for the base rate cell with full precision: `1/0.8645`, not `1.1567`.

### embedded-excel-conversion-matrix-update
- Conversion matrices have row labels (from-unit) and column labels (to-unit).
- Identify target cells by matching row/column labels to task description (e.g., "cart to bay" → row labeled "cart", column labeled "bay").
- Diagonal cells are typically 1 (self-conversion); off-diagonal cells may be static values or reciprocal formulas.
- Preserve formulas that reference updated cells — they will recalculate when opened.
- Correction values may appear in slide text boxes when the task indicates to look there.
- **Multi-sheet workbooks**: Check `xl/workbook.xml` for sheet names. Readme/instruction sheets are common — do not edit them. Target the sheet with actual data (e.g., "Live Pack Matrix").
- **Archived corrections**: If task mentions both current and archived/historical corrections, apply only the current one. Archived values are for reference only.

## Troubleshooting
- If the file won't open after editing, check XML well-formedness
- If formulas show errors, verify cell references are correct
- If changes don't appear, confirm you edited the correct sheet in the correct embedded file
- If `unzip` CLI fails, use Python `zipfile` module as fallback
- If verifier fails on numeric precision, re-check that you wrote full-precision values without any rounding
- If you edited sheet1 but changes don't appear, verify sheet1 is the target sheet (check workbook.xml for sheet names)

## Helper Scripts
- `scripts/update_embedded_xlsx.py`: Run this script for deterministic, namespace-safe cell updates in embedded workbooks. Pass host file, embed path, cell reference, new value, and output path as arguments. Accepts raw float values and preserves full precision.
