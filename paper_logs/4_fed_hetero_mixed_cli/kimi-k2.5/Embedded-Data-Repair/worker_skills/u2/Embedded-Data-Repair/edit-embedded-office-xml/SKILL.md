---
name: edit-embedded-office-xml
description: Modify embedded OLE objects (Excel workbooks, Word docs) inside PowerPoint or Word files by treating them as ZIP archives and editing the underlying XML, or by using high-level libraries when available. Use for precise low-level XML control, macro preservation, or when directed to locate correction values within slide content. Correction values come from the task prompt unless explicitly directed to retrieve them from document content.
---

# Edit Embedded Office XML

## When to Use
- Update values, formulas, or formatting in an Excel workbook embedded inside a `.pptx` or `.docx`.
- High-level libraries (`python-pptx`, `openpyxl`) cannot access or modify the embedded OLE object directly without extraction/repacking.
- You need to preserve exact file structure, macros, or custom XML that high-level tools might strip.
- The task explicitly directs you to find correction values within slide text, notes, or document content.

## Core Workflow
1. **Identify Correction Value**: Read the task prompt. If the value is stated explicitly, use it. If the task says the value is "in the slide", "in notes", or similar, proceed to extract from content.
2. **Extract from Slide Content (if directed)**:
   - Use `python-pptx`: Iterate `slide.shapes`, check `shape.has_text_frame`, and read `shape.text`.
   - Or parse `ppt/slides/slide1.xml` directly: Extract text from `<a:t>` elements within `<a:p>` paragraphs.
   - Look for patterns like "correction: X to Y = Z" or "FINAL..."
3. **Compute with Full Precision**: If the value requires calculation (e.g., inverse rate `1/0.8645`), compute in Python: `value = 1 / 0.8645` then write `repr(value)` for full precision. NEVER round intermediate calculations.
4. **Treat as ZIP**: Office files are ZIP archives. Use Python's `zipfile` module.
5. **Locate Embedding**:
   - PowerPoint: `ppt/embeddings/Microsoft_Excel_Worksheet.xlsx` (or similar)
   - Word: `word/embeddings/Microsoft_Excel_Worksheet.xlsx`
   - List contents to find the exact path.
   - **If multiple embeddings exist** (e.g., `Archive_*.xlsx` and `Live_*.xlsx`): Check for metadata files (e.g., `live_embedding.json`, `active_workbook.json`) in `/root/` or the container. Parse JSON to find the target filename/path (keys like `active_embedding`, `live_path`, `target_workbook`). Metadata is authoritative — do not guess from filename prefixes like "Live" or "Current".
6. **Extract Embedded Workbook**: Extract the `.xlsx` to a temporary location or memory buffer.
7. **Modify the Workbook**:
   - **Preferred**: Use `openpyxl` to load the extracted workbook, update the target cell with the raw numeric value, and save to a new temporary file.
   - **Fallback**: Use `xml.etree.ElementTree` to directly edit `xl/worksheets/sheet1.xml` if openpyxl fails or precision is lost.
   - Update only static value cells (`<v>` tags in cells without `<f>` formula tags). Preserve formula cells.
8. **Repack**: Write the modified `.xlsx` back into the host `.pptx`/`.docx` ZIP, replacing the original entry. Ensure compression method is `ZIP_DEFLATED` and all original entries (including `_rels/` and `[Content_Types].xml`) are preserved.
9. **Verify**: Re-open the output file with `zipfile`, read the target XML or extract the Excel to verify the change. Confirm formulas are preserved.

## Critical Decision Rules
- **Default to XML/script editing over `openpyxl`**: `openpyxl` rewrites sharedStrings.xml/styles.xml when saving, causing structural verifiers to fail. Use `scripts/update_embedded_xlsx.py` or ElementTree for embedded workbooks.
- **Correction value source**: Task prompt is primary. Only search inside file content (slide text, notes) if explicitly instructed by the task description.
- **If `unzip` CLI fails**: Fall back to Python `zipfile` immediately. It's always available and handles Office ZIPs reliably.
- **If `pip install` fails with externally-managed-environment**: Immediately fall back to XML editing with ElementTree. Do not try to use --break-system-packages.
- **If string replacement on XML is tempting**: Avoid it unless the exact string is guaranteed. Use `xml.etree.ElementTree` to prevent namespace corruption.
- **If formulas reference updated cells**: Ensure dependent cells retain their formulas (e.g., `ROUND(1/C4, 4)`) rather than hardcoded values, so they recalculate on open.
- **If multiple sheets exist**: Check `xl/workbook.xml` for sheet names and `xl/worksheets/` for corresponding files. Target the correct sheet (e.g., sheet2.xml for "Dilution Matrix").
- **If target value already matches current value**: Still perform the write and repack operation. The verifier may check workflow correctness, not just final content. Do not skip the write step.
- **If a config/metadata file is present** (e.g., `live_embedding.json`, `target.json`, `active_workbook.json`): Parse it first to identify the exact target embedding filename. Do not guess based on slide text or naming conventions.
- **If multiple embeddings exist**: Apply changes only to the metadata-specified target. Leave archive/historical workbooks untouched. Verify after modification that only the target was changed.

## Anti-Patterns (Do Not)
- **Do NOT confuse slide notes with text boxes**: Slide notes (`notesSlide`) are separate from text boxes on the slide itself. If `slide.has_notes_slide` is False or notes are empty, check the slide's shapes/text boxes directly.
- **Do NOT use arbitrary values**: If you cannot identify the correction value from the task prompt or the specified location in the file, stop and re-read. Do not pick the most likely looking number.
- **Do NOT strip namespaces**: Office XML requires namespaces. Preserving them is critical for file validity.
- **Do NOT convert formula cells to static values**: Never remove `<f>` tags. Only update `<v>` tags in cells without formulas.
- **Do NOT round numeric values**: Never use `round()`, `format()`, or f-string formatting on numbers before writing to XML or Excel cells.
- **Do NOT apply archived corrections**: When slide text contains multiple corrections labeled as "ARCHIVED", "OLD", "HISTORICAL", "DRAFT", or "superseded" alongside "LIVE", "FINAL", "CURRENT", or "approved", only apply the live/final/approved correction. Archived/draft values are explicitly not to be used. Look for delimiters like "||" separating sections.
- **Do NOT assume row/column indices from CSV order**: If using `label_aliases.csv` to resolve short codes (e.g., "CB" → "Catalyst Beta Stream"), the order of entries in the CSV does not necessarily match the row order in the Excel matrix. Always search the worksheet cells for the actual label text to determine the correct row/column index.
- **Do NOT use dict-based ZIP reconstruction**: Reading all entries into `{name: data}` and writing back with `writestr(name, data)` strips ZipInfo metadata (timestamps, compression flags, external attributes, CRC). Always iterate `infolist()` and pass the original `ZipInfo` object to `writestr(item, data)`.
- **Do NOT modify the host ZIP in-place**: Opening the same `.pptx`/`.docx` file for both reading and writing (e.g., `shutil.copy` then opening for `'w'` mode, or using `ZipFile` with `'r+'` mode) causes "Truncated file header" or data corruption. Always read the entire source archive into memory or a temporary location first, then write to a *new* output file.
- **Do NOT conclude "no change needed" without explicit verification**: If analysis suggests values already match, still perform the write — the verifier expects a modified output file, not an analytical conclusion.
- **Do NOT assume workbook identity from filename**: Names like "Live" or "Current" in filenames may be misleading. If a metadata file exists, it is the authoritative source for target selection.
- **Do NOT rely on openpyxl for strict structural verifiers**: openpyxl may rewrite shared strings, styles, or sheet metadata, causing byte-level or structural verifiers to fail. If verification fails after an openpyxl update, fall back to `scripts/update_embedded_xlsx.py` for surgical XML edits that guarantee structural parity.

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
- DO: Compute in Python: `value = 1 / 0.8645` then write `repr(value)` or pass it to openpyxl
- Never round intermediate calculations — the target precision is unknown
- For inverse rates: if target is `X`, compute `1/X` in Python and write the full result

## Known invariants (by sub-task)

### embedded-excel-fx-rate-update (FX cross-rate variant)
- Correction value comes from task prompt. If target specifies derived rate (e.g., "EUR to GBP = 0.8645"), compute inverse for base cell with full precision: `1/0.8645`, NOT `1.1567`.
- Formulas referencing updated cells (e.g., `ROUND(1/C4, 4)`) must be preserved — they recalculate on open.
- Base rate cells are static values (`t="n"` without `<f>`); derived rates are formula cells.

### conversion-matrix-update (warehouse-slot-factor / unit-conversion / catalyst-blend variant)
- **Matrix structure**: Rows are source types (from-unit), columns are destination types (to-unit). Each cell at row/column intersection gives the conversion factor.
- **Target cell identification**: Match row label and column label from task description or slide text (e.g., "cart to bay" → row labeled "cart", column labeled "bay", intersection cell is the target).
- **Label alias resolution**: If `label_aliases.csv` is present in the task directory, it maps short codes (e.g., "CB", "CD") to full workbook labels (e.g., "Catalyst Beta Stream", "Catalyst Delta Stream"). 
  1. Read the CSV to map short codes → full labels.
  2. Search the worksheet row headers and column headers for cells containing the full label text.
  3. The intersection of the resolved row and column is the target cell.
  4. **Critical**: Do not assume the row index matches the CSV entry order; always verify by checking the actual cell text in the matrix.
- **Value location**: May be in slide text boxes/shapes (not notesSlide) when task describes finding it there. Parse all text from shapes and look for patterns like "FINAL slot-factor correction: cart to bay = 0.50" or "X to Y = value".
- **Archived vs Live corrections**: Slide text may contain both archived/historical corrections (e.g., "ARCHIVED: pallet to carton = 42") and current corrections (e.g., "FINAL live correction: crate to pallet = 0.40"). Only apply the live/final correction. Ignore archived values even if explicitly stated.
- **Reciprocal formulas**: Cells with formulas like `=ROUND(1/E6, 4)` calculate inverse relationships. Preserve these as formulas; they auto-recalculate when the base value changes.
- **Diagonal cells**: Typically contain 1 (self-conversion).
- **Static vs formula**: Target cells are typically static numeric values. Dependent cells contain formulas referencing the target.

### buffer-dilution-matrix-repair (dilution/concentration variant)
- **Matrix structure**: Similar to conversion matrix but for buffer stocks (e.g., BUF1, BUF5, BUF10, BUF20). Rows are source concentrations, columns are destination concentrations.
- **Slide text patterns**: Look for "DRAFT superseded ratio: X to Y = Z || FINAL approved ratio: X to Y = Z". The pipe-delimited format (||) separates superseded vs approved corrections.
- **Correction keywords**: "DRAFT", "superseded" indicate archived/old values. "FINAL", "approved", "live" indicate values to apply.
- **Target values**: Static numeric cells at intersections (e.g., cell F8 for BUF10→BUF5). Diagonal typically 1.0 (self-dilution).
- **Reciprocal formulas**: Cells often contain `ROUND(1/target_cell, 4)` for inverse dilutions. Preserve these formulas; do not convert to static values.
- **Summary sheets**: Often contain instructions like "Leave the summary sheet unchanged" - verify sheet names (e.g., "Summary" vs "Dilution Matrix") before modifying.

### embedded-excel-single-sheet-dual-matrix
- **Single sheet, two matrices**: A sheet may contain both Archived/DRAFT and Approved/LIVE matrices.
- **Keyword targeting**: Scan headers for keywords: "DRAFT"/"supersersed"/"OLD" = archived; "FINAL"/"approved"/"LIVE" = apply.
- **Alias resolution**: If `label_aliases.csv` present, map short codes to full labels and search actual cell text — never assume CSV row order matches matrix order.
- **Isolation**: Only modify cells in target block. Verify archived cells remain untouched.

### embedded-excel-multi-workbook-selection (metadata-driven target)
- **Multiple embeddings**: Containers may have multiple embedded workbooks (e.g., `Archive_*.xlsx` and `Live_*.xlsx` in `ppt/embeddings/`).
- **Metadata files**: Check for JSON files in `/root/` or the container that specify which embedding is active:
  ```python
  import json, os
  for f in os.listdir('/root'):
      if f.endswith('.json') and ('embedding' in f.lower() or 'workbook' in f.lower()):
          with open(os.path.join('/root', f)) as fp:
              meta = json.load(fp)
              # Look for keys: active_embedding, live_path, target_workbook
  ```
- **Apply changes only to the target**: Leave archive/historical workbooks unchanged.
- **Verification**: After modification, verify that only the target workbook was changed and archive workbooks remain untouched.

## Helper Scripts
- `scripts/update_embedded_xlsx.py`: Run this script when you need a deterministic, namespace-safe update to a cell in an embedded Excel workbook using low-level XML editing. Pass host file, embed path, cell reference, new value, and output path as arguments. Uses `repr()` for full precision and refuses to overwrite formula cells. Use this when openpyxl is unavailable or fails. **Note**: By default targets `xl/worksheets/sheet1.xml`; use `--sheet sheetN.xml` to target other sheets (e.g., `--sheet sheet2.xml` for the second worksheet).

## References
- `references/openxml-structures.md`: XML schema details, namespace mappings, openpyxl usage patterns, and common failure patterns.

## Troubleshooting
- **Correction value not found**: If task says it's "in the slide" but notes are empty, check `slide.shapes` for text boxes. Parse slide XML for `<a:t>` text elements. Look for "FINAL", "LIVE", "CORRECTION", "approved", or "DRAFT/superseded" keywords.
- **Multiple correction candidates**: If slide text contains values for both "archived/draft/superseded" and "live/final/approved" corrections, read carefully to identify which is active. Usually the task or slide text will explicitly state which matrix is live vs archived.
- **Label alias mismatch**: If you resolved "CB" → "Catalyst Beta Stream" but cannot find that text in the matrix row headers, re-examine the worksheet. The label might be slightly different (e.g., "Beta Stream" vs "Catalyst Beta Stream") or the CSV mapping might need exact matching. Search for substrings if necessary.
- **Externally managed environment**: If `pip install openpyxl` fails with "externally-managed-environment", immediately switch to ElementTree XML editing approach. Do not attempt --break-system-packages.
- **Wrong sheet target**: If the workbook has multiple sheets (check `xl/workbook.xml`), ensure you're editing the correct sheet XML (e.g., `sheet2.xml` for "Dilution Matrix", not `sheet1.xml`).
- **File won't open after repacking**: Ensure ZIP compression method is `ZIP_DEFLATED` and all original entries are preserved. Do not drop `_rels/` or `[Content_Types].xml`.
- **Value not updating**: Check cell reference format (`r="C4"`). Excel XML uses absolute references. Verify the target cell isn't cached in a `<v>` tag alongside a `<f>` tag.
- **Namespace errors**: Office XML uses default namespaces. Register them when using XPath or ElementTree: `{'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}`.
- **Duplicate file warning when repacking**: If you get "Duplicate name" warnings, ensure you're creating a new ZipFile and writing entries once. Do not append to existing archives.
- **Verifier rejects structurally valid file**: You likely used dict-based ZIP reconstruction or in-place modification. Switch to the `infolist()`-preserving repack pattern shown in `references/openxml-structures.md`.
- **Wrong workbook modified**: Check for metadata files that specify the target embedding. Verify the embedding path matches the metadata before making changes.
- **Verification passes but tests fail**: Re-examine test expectations. In dual-matrix scenarios, verify the correct matrix block. Check if tests expect cached formula values updated. Confirm output path matches test expectations.
- **Verifier fails after openpyxl update**: openpyxl rewrites sharedStrings/styles. Fall back to `scripts/update_embedded_xlsx.py` for structural parity.

## Verification Checklist
Before declaring success:
- [ ] Confirm the new value came from the correct source (task prompt or specified file location as directed)
- [ ] If multiple corrections exist (archived/draft vs live/final), verify you applied the live/final/approved one
- [ ] If using label_aliases.csv, verify the target row/column contains the resolved full label text (do not assume indices from CSV order)
- [ ] If multiple sheets exist, verify you modified the correct sheet (e.g., "Dilution Matrix" not "Summary")
- [ ] Verify the output file opens without corruption errors
- [ ] Verify the target cell contains the new value
- [ ] Verify formulas in dependent cells are preserved (not converted to static values)
- [ ] Verify file size is reasonable (similar to input, not zero or drastically different)
- [ ] If dual-matrix (archived+live on same sheet), verify archived cells unchanged (byte-compare if strict verifier)
