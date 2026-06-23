---
name: edit-embedded-office-xml
description: Modify embedded OLE objects (Excel workbooks, Word docs) inside PowerPoint or Word files by treating them as ZIP archives and editing the underlying XML. Use when high-level libraries (python-pptx, openpyxl) are unavailable, fail to parse embedded objects, or when precise low-level XML control is required.
---

# Edit Embedded Office XML

## When to Use
- Update values, formulas, or formatting in an Excel workbook embedded inside a `.pptx` or `.docx`.
- High-level libraries (`python-pptx`, `openpyxl`) cannot access or modify the embedded OLE object.
- You need to preserve exact file structure, macros, or custom XML that high-level tools might strip.

## Core Workflow
1. **Treat as ZIP**: Office files are ZIP archives. Use Python's `zipfile` module.
2. **Locate Embedding**:
   - PowerPoint: `ppt/embeddings/Microsoft_Excel_Worksheet.xlsx` (or similar)
   - Word: `word/embeddings/Microsoft_Excel_Worksheet.xlsx`
   - List contents to find the exact path.
3. **Extract & Inspect**: Extract the embedded `.xlsx` to memory or `/tmp`. Inspect `xl/worksheets/sheet1.xml` for structure.
4. **Modify XML**:
   - Use `xml.etree.ElementTree` to safely parse and modify cells (`<c r="A1">`).
   - Update `<v>` for values or `<f>` for formulas.
   - Preserve namespaces and surrounding structure.
5. **Repack**: Write modified XML back into the embedded `.xlsx`, then write the updated `.xlsx` back into the host `.pptx`/`.docx`.
6. **Verify**: Re-open the output file with `zipfile`, read the target XML, and confirm the change.

## Critical Decision Rules
- **If `unzip` CLI fails**: Fall back to Python `zipfile` immediately. It's always available and handles Office ZIPs reliably.
- **If string replacement on XML is tempting**: Avoid it unless the exact string is guaranteed. Use `xml.etree.ElementTree` to prevent namespace corruption or whitespace issues.
- **If formulas reference updated cells**: Ensure dependent cells use formulas (e.g., `ROUND(1/C4, 4)`) rather than hardcoded values, so they recalculate on open.
- **If multiple sheets exist**: Check `xl/workbook.xml` for sheet names and `xl/worksheets/` for corresponding files.

## Known invariants (by sub-task)

### embedded-excel-in-pptx (B1)
- **Correction value source**: The correction value comes from the task prompt, NOT from internal file content. Do not search for "slide notes" or "correction instructions" inside the PPTX unless explicitly stated.
- **Do not use arbitrary values**: If the correction value is not clearly identified, list candidate cells with coordinates and values, then check the task description for the correct value.
- **Preserve namespaces**: XML namespaces (`http://schemas.openxmlformats.org/spreadsheetml/2006/main`) must be preserved during ElementTree parse/repack. Stripping them corrupts the file.
- **Preserve formulas**: Cells with `<f>` tags contain formulas. Only modify sibling `<v>` tags or static value cells. Never remove `<f>` tags unless explicitly converting a formula to a static value.

## Helper Scripts
- `scripts/update_embedded_xlsx.py`: Run this script when you need a deterministic, namespace-safe update to a cell in an embedded Excel workbook. Pass host file, embed path, cell reference, new value, and output path as arguments.

## Troubleshooting
- **File won't open after repacking**: Ensure ZIP compression method is `ZIP_DEFLATED` and all original entries are preserved. Do not drop `_rels/` or `[Content_Types].xml`.
- **Value not updating**: Check cell reference format (`r="C4"`). Excel XML uses absolute references. Verify the target cell isn't cached in a `<v>` tag alongside a `<f>` tag.
- **Namespace errors**: Office XML uses default namespaces. Register them when using XPath or ElementTree: `{'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}`.
