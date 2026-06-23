---
name: edit-embedded-office-xml
description: Modify embedded OLE objects (Excel workbooks, Word docs) inside PowerPoint or Word files by treating them as ZIP archives and editing the underlying XML. Use when high-level libraries (python-pptx, openpyxl) are unavailable, fail to parse embedded objects, or when precise low-level XML control is required.
---

# Edit Embedded Office XML

## When to Use
- Update values, formulas, or formatting in an Excel workbook embedded inside a `.pptx` or `.docx`.
- High-level libraries (`python-pptx`, `openpyxl`) cannot access or modify the embedded OLE object directly.
- You need to preserve exact file structure, macros, or custom XML that high-level tools might strip.

## Core Workflow
1. **Treat as ZIP**: Office files are ZIP archives. Use Python's `zipfile` module.
2. **Locate Embedding**:
   - PowerPoint: `ppt/embeddings/Microsoft_Excel_Worksheet.xlsx` (or similar)
   - Word: `word/embeddings/Microsoft_Excel_Worksheet.xlsx`
   - List contents to find the exact path.
3. **Extract & Inspect**: Extract the embedded `.xlsx` to memory or `/tmp`. Inspect `xl/worksheets/sheet1.xml` for structure.
4. **Identify Target Sheet(s)**:
   - Read `xl/workbook.xml` to map sheet names to sheet IDs/files.
   - If the task specifies modifying only certain sheets (e.g., "Live Pack Matrix" but not "Readme"), identify the correct `xl/worksheets/sheetN.xml` file.
   - **Decision rule**: If multiple sheets exist, always verify sheet names before modifying. Never assume `sheet1.xml` is the target.
5. **Modify**:
   - **Option A (Recommended for standard updates)**: Use `openpyxl` on the *extracted* `.xlsx` file. It safely handles values, formulas, and types.
   - **Option B (Low-level XML)**: Use `xml.etree.ElementTree` to parse `sheetN.xml` directly. Update `<v>` for values; preserve `<f>` for formulas. Use `scripts/update_embedded_xlsx.py` for deterministic, namespace-safe updates.
   - **String replacement**: Only use if the exact target string is guaranteed unique and you've verified it won't match other cells. Prefer XML parsing.
6. **Repack**: Write modified `.xlsx` back into the host `.pptx`/`.docx` using `zipfile`. Preserve all original entries, especially `_rels/` and `[Content_Types].xml`.
7. **Verify**: Re-open the output file with `zipfile`, extract the embedded `.xlsx`, and confirm changes with `openpyxl` or XML inspection.

## Critical Decision Rules
- **If `unzip` CLI fails**: Fall back to Python `zipfile` immediately. It's always available and handles Office ZIPs reliably.
- **If string replacement on XML is tempting**: Avoid it unless the exact string is guaranteed unique. Use `xml.etree.ElementTree` or `openpyxl` to prevent namespace corruption or whitespace issues.
- **If formulas reference updated cells**: Ensure dependent cells use formulas (e.g., `ROUND(1/C4, 4)`) rather than hardcoded values, so they recalculate on open.
- **If multiple sheets exist**: Check `xl/workbook.xml` for sheet names and `xl/worksheets/` for corresponding files. Only modify sheets explicitly required by the task.
- **If verifier fails on numeric match**: Check if you pre-rounded the value. Always write the full-precision float.
- **If task mentions "live" vs "archived" data**: Only modify live/current sheets. Archived or reference sheets should remain untouched.

## Finding Correction Values
- If the task says "the note contains the correction", the value may be in the task prompt *or* embedded as text in the slide XML.
- Extract all text from `ppt/slides/slide*.xml` by searching for `<a:t>` tags. Do not assume it's only in the prompt.
- **Do not confuse slide notes with text boxes**: Slide notes (`notesSlide`) are separate from text boxes/shapes on the slide itself. If notes are empty, check `slide.shapes` for text boxes or parse slide XML for `<a:t>` elements.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Calculation precision (critical)
When computing derived values, use full precision throughout:
- DO NOT: `1/0.8645 ≈ 1.1567` (rounded intermediate)
- DO: Compute in Python: `value = 1 / 0.8645` then write `repr(value)` or pass it to the helper script
- Never round intermediate calculations — the target precision is unknown
- For inverse rates: if target is `X`, compute `1/X` in Python and write the full result, not a rounded approximation

## Known invariants (by sub-task)

### embedded-excel-in-pptx
- Correction values come from task prompt or slide XML text, not from hidden file metadata.
- Preserve all `<f>` formula tags; only update `<v>` value tags in static cells.
- Dependent formulas (reciprocals, cross-rates) recalculate on open if base cells are updated.

### embedded-excel-conversion-matrix-update
- Conversion matrices have row labels (from-unit) and column labels (to-unit). Identify target cells by row/column label intersection.
- Diagonal cells are typically 1 (self-conversion); off-diagonal cells may be static values or reciprocal formulas.
- Correction values may appear in slide text boxes when the task indicates to look there.
- Preserve formulas that reference updated cells — they recalculate when opened.

### embedded-excel-fx-rate-update
- Base rate cells are static values (`t="n"` without `<f>`); derived rates are formula cells with `<f>` tags.
- When target specifies a derived rate (e.g., "EUR to GBP = 0.8645"), compute the inverse for the base rate cell with full precision: `1/0.8645` in Python, not `1.1567` by mental math.
- Correction value is provided in the task prompt or slide XML.

## Verification Checklist
After modifying and repacking, always verify:
1. **Target cell updated**: Extract the modified sheet XML and confirm the new value is present at the correct cell reference.
2. **Old value removed**: Confirm the original value no longer appears in the sheet (unless it's legitimately used elsewhere).
3. **Formulas preserved**: Check that `<f>` tags for dependent cells are intact and reference the updated cell correctly.
4. **Other sheets untouched**: If the workbook has multiple sheets, verify non-target sheets remain unchanged.
5. **File opens**: Re-open the output PPTX/DOCX with `zipfile` to confirm it's a valid archive.

## Anti-Patterns
- **Do not** use `python-pptx` or `openpyxl` directly on the host `.pptx`/`.docx` — they cannot access embedded OLE objects. (Using `openpyxl` on the *extracted* `.xlsx` is safe and recommended.)
- **Do not** strip XML namespace declarations when repackaging; preserve the original encoding and structure.
- **Do not** convert formula cells to static values by removing `<f>` tags.
- **Do not** round or format numeric outputs before writing them to XML.
- **Do not** assume `sheet1.xml` is the target sheet — always map sheet names from `xl/workbook.xml` first.

## Troubleshooting
- **File won't open after repacking**: Ensure ZIP compression method is `ZIP_DEFLATED` and all original entries are preserved. Do not drop `_rels/` or `[Content_Types].xml`.
- **Value not updating**: Check cell reference format (`r="C4"`). Excel XML uses absolute references. Verify the target cell isn't cached in a `<v>` tag alongside a `<f>` tag.
- **Namespace errors**: Office XML uses default namespaces. Register them when using XPath or ElementTree: `{'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}`.
- **Verifier precision mismatch**: If tests fail despite correct logic, you likely rounded the input value or computed by hand. Re-compute in Python with `repr()`, then rewrite the cell.
- **Wrong sheet modified**: If changes appear in the wrong sheet, re-check `xl/workbook.xml` sheet name mappings. Sheet IDs in `workbook.xml` correspond to `sheetN.xml` files in order.

## Helper Scripts
- `scripts/update_embedded_xlsx.py`: Run this script when you need a deterministic, namespace-safe update to a cell in an embedded Excel workbook. Pass host file, embed path, cell reference, new value, and output path as arguments. The script enforces full precision via `repr()` and safely preserves formula cells.

## References
- `references/openxml-structures.md`: XML schema details, namespace mappings, cell type patterns, slide text extraction, and common failure patterns.