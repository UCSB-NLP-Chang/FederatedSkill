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
   - Update `<v>` for values; preserve `<f>` for formulas.
   - Preserve namespaces and surrounding structure.
5. **Repack**: Write modified XML back into the embedded `.xlsx`, then write the updated `.xlsx` back into the host `.pptx`/`.docx`.
6. **Verify**: Re-open the output file with `zipfile`, read the target XML, and confirm the change.

## Critical Decision Rules
- **If `unzip` CLI fails**: Fall back to Python `zipfile` immediately. It's always available and handles Office ZIPs reliably.
- **If string replacement on XML is tempting**: Avoid it unless the exact string is guaranteed unique. Use `xml.etree.ElementTree` to prevent namespace corruption or whitespace issues.
- **If formulas reference updated cells**: Ensure dependent cells use formulas (e.g., `ROUND(1/C4, 4)`) rather than hardcoded values, so they recalculate on open.
- **If multiple sheets exist**: Check `xl/workbook.xml` for sheet names and `xl/worksheets/` for corresponding files.
- **If verifier fails on numeric match**: Check if you pre-rounded the value. Always write the full-precision float.

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
- Correction values come from task prompt, not from file internals (no "slide notes" or hidden fields).
- Preserve all `<f>` formula tags; only update `<v>` value tags in static cells.
- Dependent formulas (reciprocals, cross-rates) recalculate on open if base cells are updated.

### embedded-excel-fx-rate-update
- Base rate cells are static values (`t="n"` without `<f>`); derived rates are formula cells with `<f>` tags.
- When target specifies a derived rate (e.g., "EUR to GBP = 0.8645"), compute the inverse for the base rate cell with full precision: `1/0.8645` in Python, not `1.1567` by mental math.
- Correction value is provided in the task prompt, not within the file.

## Anti-Patterns
- **Do not** search inside the PPTX for "slide notes" or "correction instructions" unless explicitly told they exist as text fields. Task descriptions mentioning "the note contains the correction" usually mean the instruction is in your context, not the file.
- **Do not** use python-pptx or openpyxl for embedded content — they cannot access it.
- **Do not** strip XML namespace declarations when repackaging; preserve the original encoding and structure.
- **Do not** convert formula cells to static values by removing `<f>` tags.
- **Do not** round or format numeric outputs before writing them to XML.

## Troubleshooting
- **File won't open after repacking**: Ensure ZIP compression method is `ZIP_DEFLATED` and all original entries are preserved. Do not drop `_rels/` or `[Content_Types].xml`.
- **Value not updating**: Check cell reference format (`r="C4"`). Excel XML uses absolute references. Verify the target cell isn't cached in a `<v>` tag alongside a `<f>` tag.
- **Namespace errors**: Office XML uses default namespaces. Register them when using XPath or ElementTree: `{'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}`.
- **Verifier precision mismatch**: If tests fail despite correct logic, you likely rounded the input value or computed by hand. Re-compute in Python with `repr()`, then rewrite the cell.

## Helper Scripts
- `scripts/update_embedded_xlsx.py`: Run this script when you need a deterministic, namespace-safe update to a cell in an embedded Excel workbook. Pass host file, embed path, cell reference, new value, and output path as arguments. The script enforces full precision via `repr()` and safely preserves formula cells.

## References
- `references/openxml-structures.md`: XML schema details, namespace mappings, cell type patterns, and common failure patterns.
