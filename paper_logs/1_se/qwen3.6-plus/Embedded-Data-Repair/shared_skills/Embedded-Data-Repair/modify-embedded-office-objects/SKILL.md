---
name: modify-embedded-office-objects
description: How to locate, extract, modify, and repackage embedded OLE objects (like Excel workbooks or Word docs) inside Office files (.pptx, .docx, .xlsx). Use when a task requires updating data inside an embedded spreadsheet, chart, or document within a presentation or report.
---

# Modify Embedded Office Objects

Office files (`.pptx`, `.docx`, `.xlsx`) are ZIP archives. Embedded objects (OLE) are stored as separate files inside the archive. To modify them, locate the embedding, edit it, and repackage.

## Pre-flight & Environment
1. **Check `openpyxl` availability**: Run `python3 -c "import openpyxl"`. If missing, install via `pip install --break-system-packages openpyxl` or create a `venv`.
2. **Do NOT install `python-pptx` or `python-docx` unless strictly necessary for high-level text extraction.** They trigger PEP 668 restrictions, have unstable internal APIs, and often corrupt OLE relationships. Prefer `zipfile` + regex for all structural inspection.

## Tool Selection Decision
- **Standard Edit**: Use `openpyxl` + In-Memory ZIP Replacement. Best for most tasks.
- **Strict Verifier / Byte-Exact**: Use Direct XML Patch. `openpyxl` rewrites internal XML (namespaces, dimensions, sheet order), which fails hash-based or strict structural verifiers.
- **Inspection**: Prefer `zipfile` + regex over `python-pptx`. `python-pptx` requires installation (PEP 668 issues) and has unstable internal APIs for OLE blobs. Use `zipfile` to list paths and parse slide text.

## Preferred Workflow: In-Memory ZIP Replacement
For single-file edits, avoid full extraction. Read the host ZIP into memory, replace the target embedded file's bytes, and write a new archive. This automatically preserves all internal paths, `.rels`, and `[Content_Types].xml`.

```python
import zipfile, openpyxl, io

# 1. Load host archive
with zipfile.ZipFile('input.pptx', 'r') as z_in:
    # 2. Read and modify the embedded file in memory
    xlsx_bytes = z_in.read('ppt/embeddings/Microsoft_Excel_Worksheet.xlsx')
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=False)
    
    # 3. Apply changes (preserve formulas, update values)
    ws = wb['SheetName']
    ws['D8'].value = 1.5625  # Example: update value cell only
    
    # 4. Save modified workbook to memory
    out_buffer = io.BytesIO()
    wb.save(out_buffer)
    new_xlsx_bytes = out_buffer.getvalue()
    
    # 5. Write new host archive, replacing only the target entry
    # NOTE: Always use 'w' mode. Never use 'a' (append) as it creates duplicate entries.
    with zipfile.ZipFile('output.pptx', 'w', zipfile.ZIP_DEFLATED) as z_out:
        for item in z_in.infolist():
            if item.filename == 'ppt/embeddings/Microsoft_Excel_Worksheet.xlsx':
                z_out.writestr(item, new_xlsx_bytes)
            else:
                z_out.writestr(item, z_in.read(item.filename))
```

## Alternative Workflow: Direct XML Patch (Strict Preservation)
Use when verifiers require byte-exact preservation of the host/embedded file, or when `openpyxl`'s XML rewriting causes failures.
1. Extract the embedded `.xlsx` to a temp dir.
2. Locate the target sheet XML (`xl/worksheets/sheetN.xml`).
3. Use regex or string replacement to update the `<v>` tag for the target cell (e.g., `<c r="F8" t="n"><v>2.1</v></c>` -> `<v>2</v>`).
4. Repackage the `.xlsx` using `scripts/repack_office.py`.
5. Replace the `.xlsx` in the host `.pptx` using the in-memory ZIP pattern above.

## Alternative Workflow: Full Extraction & Repackaging
Use when modifying multiple embedded files, complex directory structures, or when `zipfile` memory usage is prohibitive.
1. Extract the host archive to a temp directory using `zipfile`.
2. Edit the embedded file directly in the extracted tree.
3. Repackage using `scripts/repack_office.py` to avoid duplicate-entry warnings and path corruption.
   ```bash
   python3 scripts/repack_office.py <extracted_dir> <output_file>
   ```

## Locating Instructions & Targets
- **Slide/Document Text**: Instructions are often hidden in slide text boxes, notes, or comments. Parse the extracted XML (`ppt/slides/slide*.xml`) for `<a:t>` elements.
  ```python
  import re
  slide_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
  texts = re.findall(r'<a:t>(.*?)</a:t>', slide_xml)
  ```
- **Instruction Parsing**: Look for keywords like `DRAFT`, `FINAL`, `SUPERSEDED`, `APPROVED`. Apply only the final/approved values.
- **Embedded Paths**: 
  - `.pptx`: `ppt/embeddings/`
  - `.docx`: `word/embeddings/`
  - `.xlsx`: `xl/embeddings/`
- **Cell Mapping**: When updating matrices, map row/column headers to coordinates. Update **value cells**, not formula cells. Formulas recalculate on open.

## Verification & Output
- **Output Path**: Always check task instructions for the exact expected filename (e.g., `output.pptx`, `results.pptx`, or overwrite `input.pptx`). Verifiers frequently fail on incorrect output paths.
- **Structural Integrity**: Open the new archive with `zipfile`, read the modified embedded file, and confirm the target cell/value changed while surrounding formulas/structure remain intact.

## Anti-Patterns & Pitfalls
- **Do not use `zipfile` append mode (`'a'`) to replace entries.** It creates duplicate entries and corrupts the archive. Always rebuild with `'w'` mode.
- **Do not use `python-pptx` or `python-docx` to edit embedded OLE objects directly.** They lack reliable OLE blob replacement and often corrupt relationships.
- **Avoid `python-pptx` internal APIs** (e.g., `slide._slide_part`, `slide.rels`). They are unstable across versions and frequently raise `AttributeError`. Use `zipfile` + regex for all structural inspection and relationship resolution.
- **Do not edit the host ZIP in-place.** Always write to a new output file.
- **Preserve exact paths.** Changing filenames breaks `.rels` links. The in-memory replacement pattern handles this automatically.
- **Formulas vs Values.** Update the raw value cell. Do not overwrite formula cells unless explicitly requested.
- **`zipfile.extract()` path quirks.** Prefer `z.read(member)` and manual file writes over `z.extract()` to avoid accidental directory creation.

## Troubleshooting
- **Broken link after repackaging**: Verify internal paths match exactly. Check `[Content_Types].xml` and `.rels` if using full extraction.
- **Corrupted output**: Ensure `ZIP_DEFLATED` is used. Clean temp directories before repackaging.
- **`unzip` command not found**: Rely exclusively on Python's `zipfile`.
- **PEP 668 `pip install` failures**: Use `pip install --break-system-packages` or a `venv` for `openpyxl`.
