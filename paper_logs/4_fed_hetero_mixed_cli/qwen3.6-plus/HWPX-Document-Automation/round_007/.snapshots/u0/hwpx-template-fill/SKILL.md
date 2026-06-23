---
name: hwpx-template-fill
description: Fill templates in .hwpx (Hancom Office) documents by replacing {{...}} placeholders or exact existing text with values from JSON. Use when given an .hwpx template and a JSON mapping of field names or old strings to new values. Handles ZIP extraction, multi-section XML text replacement, layout cache invalidation, and custom data preprocessing.
---

# Fill HWPX Template

HWPX files are ZIP archives containing XML content. To fill placeholders or update existing text safely:

## Workflow
1. **Inspect structure**: Use Python `zipfile` to list contents. Main text lives in `Contents/section0.xml`, `Contents/section1.xml`, etc. **Always process all `section*.xml` files**, as placeholders or target text may span multiple sections.
2. **Identify replacement mode**:
   - **Placeholder mode**: Look for `{{key}}` patterns inside `<hp:t>` tags. Use `scripts/fill_hwpx.py`.
   - **Direct text mode**: Target existing strings or paragraph IDs. Use `scripts/update_hwpx_direct.py` or the custom pattern below.
3. **Preprocess Data (if needed)**: If values require computation (e.g., age calculation, phone normalization, conditional text, appending metadata, array mapping, or risk enrichment), transform the JSON or build a replacement dictionary before applying it to the XML. See `references/value-preprocessing.md`.
4. **Replace & Invalidate Cache**:
   - Replace target text.
   - **Critical**: Remove `<hp:linesegarray>...</hp:linesegarray>` or `<hp:linesegarray />` from any modified `<hp:p>` element. HWPX caches layout coordinates here; leaving them causes overlapping/garbled text when string lengths change.
5. **Repackage**: Write modified XML back into a new ZIP with `ZIP_DEFLATED` compression, preserving original `ZipInfo` metadata and file order.
6. **Verify**: Open the output ZIP, read *all* section XMLs, and confirm zero `{{...}}` patterns remain (if applicable) and all target strings were updated.

## Direct Text Replacement (No Placeholders)
When the template lacks `{{...}}` markers and requires updating specific existing text:
- **Handle `<hp:run>` splitting**: HWPX often splits text across multiple `<hp:run>` tags. Do not run `str.replace()` on raw XML if it might cross tag boundaries. Instead, replace text inside `<hp:t>` tags or replace the entire `<hp:p>` content.
- **Use paragraph-aware regex**: Match `<hp:p id="...">...</hp:p>`, apply replacements, track modified paragraph IDs, and strip `linesegarray` from those IDs.
- Run `scripts/update_hwpx_direct.py <template.hwpx> <mapping.json> <output.hwpx>` where `mapping.json` is `{"old_text": "new_text", ...}`.

## Custom Transformation Pattern
When data requires preprocessing or direct replacement, use this robust pattern to avoid `zipfile` context manager scope errors:
```python
import zipfile, json, re, copy

# 1. Load & preprocess data
with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
# Apply transformations to `data` dict here...

# 2. Read entire archive into memory FIRST
with zipfile.ZipFile('template.hwpx', 'r') as zin:
    namelist = zin.namelist()
    zipinfos = {n: copy.copy(zin.getinfo(n)) for n in namelist}
    filedata = {n: zin.read(n).decode('utf-8') for n in namelist}

# 3. Process sections
sections = [n for n in namelist if 'section' in n and n.endswith('.xml')]
for sec in sections:
    xml = filedata[sec]
    # Replace placeholders & remove linesegarray from modified <hp:p>
    # ... (use regex or XML parser)
    filedata[sec] = xml

# 4. Repackage (outside the read context)
with zipfile.ZipFile('output.hwpx', 'w', zipfile.ZIP_DEFLATED) as zout:
    for n in namelist:
        zout.writestr(zipinfos[n], filedata[n].encode('utf-8'))
```

## Verification Notes
- `linesegarray` elements **will remain** on static/unmodified paragraphs. This is expected and correct.
- Only verify that paragraphs containing replaced values do *not* contain `linesegarray`.
- A simple regex check for remaining `{{...}}` across all sections is usually sufficient for placeholder validation.

## Known invariants (by sub-task)
### B1: HWPX Template Placeholder Fill
- `<hp:linesegarray>` elements must be removed from any modified `<hp:p>` paragraphs. Failure causes overlapping/garbled characters.
- Regex for linesegarray removal must match both self-closing `<hp:linesegarray />` and full `<hp:linesegarray>...</hp:linesegarray>` without overlapping; incorrect patterns leave orphaned `</hp:linesegarray>` closing tags.
- Text is often split across multiple `<hp:run>` tags within a single `<hp:p>`. Direct `str.replace()` on raw XML breaks when old text spans a run boundary; always work at the `<hp:p>` or `<hp:t>` level.

## Anti-Patterns
- Do not treat `.hwpx` as a plain text file. It is a binary ZIP archive.
- Do not skip `<hp:linesegarray>` removal. Modified paragraphs will render incorrectly.
- Do not rely on external HWP libraries unless necessary; standard `zipfile` + `re` is sufficient and more reliable in constrained environments.
- Do not add/remove files from the HWPX archive unless explicitly required. Preserve the original `namelist` and `ZipInfo` objects.
- Do not assume placeholders only exist in `section0.xml`. Always scan and process all `section*.xml` files.
- **Do not read from the ZIP file after its `with` block closes.** Always load all XML strings into a dictionary before closing the read context.
- **Avoid blind `str.replace()` on raw XML** when text is split across `<hp:run>` tags. It can break XML structure. Always operate at the `<hp:p>` or `<hp:t>` level.

## Automation
- Run `scripts/fill_hwpx.py <template.hwpx> <data.json> <output.hwpx>` for direct 1:1 `{{...}}` placeholder replacement across all sections.
- Run `scripts/update_hwpx_direct.py <template.hwpx> <mapping.json> <output.hwpx>` for exact string replacement in existing text.
- If data transformation is required, adapt the script or run a preprocessing step to generate a ready-to-use JSON mapping before invoking the ZIP/XML workflow. For common preprocessing patterns (unit stripping, rating reformatting, phone normalization, array mapping, conditional enrichment), see `references/value-preprocessing.md`.
- For pattern-based replacement (prefix matching, date ranges, table cells, CSV integration), see `references/advanced-replacement.md`.
