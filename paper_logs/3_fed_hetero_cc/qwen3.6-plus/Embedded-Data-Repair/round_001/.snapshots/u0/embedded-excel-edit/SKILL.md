---
name: embedded-excel-edit
description: Modify embedded Excel workbooks inside PowerPoint (.pptx) or Word (.docx) files. Use when a task requires updating cell values, formulas, or data in an OLE-embedded Excel sheet within an Office document.
---

# Edit Embedded Excel in Office Documents

## When to Use
- A `.pptx` or `.docx` contains an embedded Excel worksheet (usually visible as a table or chart).
- You need to update specific cell values, ranges, or formulas inside that embedded workbook.
- Instructions are often found in slide notes, text boxes, or external briefs.

## Core Workflow
1. **Inspect the Office document structure**: Treat `.pptx`/`.docx` as a ZIP archive. List contents to locate the embedded workbook, typically at `ppt/embeddings/` or `word/embeddings/` with `.xlsx` extension.
   ```python
   import zipfile
   with zipfile.ZipFile('input.pptx', 'r') as z:
       print('\n'.join(z.namelist()))
   ```

2. **Find the update directive**: Read slide/document notes or text boxes to locate target values or correction instructions.

3. **Extract the workbook**: Use Python's `zipfile` to extract the embedded `.xlsx` to a temporary location.
   ```python
   with zipfile.ZipFile('input.pptx', 'r') as z:
       xlsx_bytes = z.read('ppt/embeddings/Microsoft_Excel_Worksheet.xlsx')
   ```

4. **Modify with `openpyxl`**:
   - Load the workbook: `wb = openpyxl.load_workbook(path)`
   - Identify the target sheet and cells.
   - **Check cell type before editing**: `cell.data_type == 'f'` means formula (do not overwrite).
   - Update values directly: `ws['C4'].value = 1.159`
   - **Preserve formulas**: Do not overwrite cells containing formulas unless explicitly instructed.
   - Save the workbook: `wb.save(path)`
   
   See `references/openpyxl_cell_types.md` for cell type reference.

5. **Repackage the Office document**:
   - Create a new ZIP archive.
   - Copy all original files from the input document into the new archive.
   - Replace the embedded `.xlsx` with the modified version, ensuring the internal path matches exactly.
   - Use `zipfile.ZIP_DEFLATED` for compression.
   ```python
   with zipfile.ZipFile(src, 'r') as zin:
       with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zout:
           for item in zin.infolist():
               if item.filename == embed_path:
                   zout.write(modified_excel, embed_path)
               else:
                   zout.writestr(item, zin.read(item.filename))
   ```

6. **Verify**: Extract the embedded workbook from the output and confirm updated cell values and preserved formulas.

## Critical Anti-Patterns
- **Do not use `python-pptx`** for embedded OLE objects. It lacks robust support for reading/modifying embedded Excel files. Use `zipfile` + `openpyxl`.
- **Do not modify the ZIP in-place**. Always create a new archive to avoid corruption or partial writes.
- **Do not overwrite formula cells** unless explicitly told to. Use `cell.data_type` to check.
- **Do not assume sheet names**. Always inspect the workbook structure first.
- **Do not use shell `unzip` command**. Use Python's zipfile module for reliability.

## Troubleshooting
- **File not found in embeddings**: Check `.rels` files for `rId` references. The path may vary.
- **Corrupted output**: Ensure all original files are copied, including `[Content_Types].xml` and `_rels/`.
- **Formulas not calculating**: `openpyxl` does not evaluate formulas. Host app computes on open. Only update source data cells.
- **openpyxl not installed**: `pip install openpyxl --break-system-packages -q`

## Verification Checklist
- [ ] Embedded workbook extracted and loaded successfully.
- [ ] Target cell(s) updated to correct values.
- [ ] Formula cells remain intact (data_type == 'f').
- [ ] Output document contains all original files plus modified workbook.
- [ ] Re-extracted workbook matches expected state.