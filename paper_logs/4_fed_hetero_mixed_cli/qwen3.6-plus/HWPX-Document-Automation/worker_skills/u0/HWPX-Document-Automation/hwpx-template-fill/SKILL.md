---
name: hwpx-template-fill
description: Fill templates in .hwpx (Hancom Office) documents by replacing {{...}} placeholders or exact existing text with values from JSON. Use when given an .hwpx template and a JSON mapping of field names or old strings to new values. Handles ZIP extraction, multi-section XML text replacement, layout cache invalidation, and custom data preprocessing.
---

# Fill HWPX Template

HWPX files are ZIP archives containing XML content. To fill placeholders or update existing text safely:

## Preferred Path (Zero-Custom-Code)
1. **Placeholder mode**: Run `scripts/fill_hwpx.py <template.hwpx> <data.json> <output.hwpx>`. It handles multi-section scanning, `{{key}}` replacement, and `linesegarray` removal automatically.
2. **Direct text mode**: Run `scripts/update_hwpx_direct.py <template.hwpx> <mapping.json> <output.hwpx>` for exact string replacement.
3. **Preprocessing**: If values need transformation, run a preprocessing step first, then pass the cleaned JSON to the scripts above. See `references/value-preprocessing.md`.

## Manual Workflow (When Custom Logic is Required)
If you must write a custom script (e.g., for complex conditional logic or non-standard XML structures):
1. **Inspect structure**: Use Python `zipfile` to list contents. Main text lives in `Contents/section0.xml`, `Contents/section1.xml`, etc. **Always process all `section*.xml` files**.
2. **Read entire archive into memory FIRST** to avoid `zipfile` context manager scope errors.
3. **Replace & Invalidate Cache**:
   - Replace target text inside `<hp:p>` or `<hp:t>` tags.
   - **Critical**: Remove `<hp:linesegarray>...</hp:linesegarray>` or `<hp:linesegarray />` from any modified `<hp:p>` element. HWPX caches layout coordinates here; leaving them causes overlapping/garbled text.
4. **Repackage**: Write modified XML back into a new ZIP with `ZIP_DEFLATED` compression, preserving original `ZipInfo` metadata and file order.
5. **Verify**: Open the output ZIP, read *all* section XMLs, and confirm zero `{{...}}` patterns remain and all target strings were updated.

## Direct Text Replacement (No Placeholders)
When the template lacks `{{...}}` markers:
- **Handle `<hp:run>` splitting**: HWPX often splits text across multiple `<hp:run>` tags. Do not run `str.replace()` on raw XML if it might cross tag boundaries. Always work at the `<hp:p>` or `<hp:t>` level.
- **Use paragraph-aware regex**: Match `<hp:p id="...">...</hp:p>`, apply replacements, track modified paragraph IDs, and strip `linesegarray` from those IDs.

## Custom Transformation Pattern
```python
import zipfile, json, re, copy

# 1. Load & preprocess data
with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

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

## Troubleshooting & Anti-Patterns
- **Regex Backreference Error**: If writing custom regex to strip `linesegarray`, avoid complex backreferences (e.g., `\3`) that can trigger `re.error: invalid group reference`. Use a callback function with `re.sub` or a two-pass ID-tracking approach instead.
- **Do not treat `.hwpx` as plain text.** It is a binary ZIP archive.
- **Do not skip `<hp:linesegarray>` removal.** Modified paragraphs will render incorrectly.
- **Do not rely on external HWP libraries** unless necessary; standard `zipfile` + `re` is sufficient.
- **Do not add/remove files from the HWPX archive** unless explicitly required. Preserve the original `namelist` and `ZipInfo` objects.
- **Do not assume placeholders only exist in `section0.xml`.** Always scan all `section*.xml` files.
- **Do not read from the ZIP file after its `with` block closes.** Load all XML strings into a dictionary first.
- **Avoid blind `str.replace()` on raw XML** when text is split across `<hp:run>` tags.

## Automation & References
- Run `scripts/fill_hwpx.py` for direct 1:1 `{{...}}` placeholder replacement.
- Run `scripts/update_hwpx_direct.py` for exact string replacement.
- Run `scripts/verify_hwpx.py <output.hwpx>` to verify output (checks ZIP validity, remaining placeholders, linesegarray presence).
- For common preprocessing patterns (unit stripping, rating reformatting, phone normalization, array mapping, conditional enrichment), see `references/value-preprocessing.md`.
- For pattern-based replacement (prefix matching, date ranges, table cells, CSV integration), see `references/advanced-replacement.md`.
