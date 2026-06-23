---
name: pptx-xml-editing
description: Edit PowerPoint (PPTX) files by directly manipulating the XML structure inside the ZIP archive. Use when python-pptx is unavailable, insufficient, or when precise low-level control over slide content, styling, structure, or relationships is needed.
---

# PPTX XML Editing

## When to Use
- python-pptx library is unavailable or cannot perform the required operation
- You need precise control over XML attributes not exposed by high-level APIs
- Adding new slides, fixing relationship mappings, or adjusting EMU dimensions
- Working with corrupted or non-standard PPTX files

## EMU & Font Constants (MEMORIZE)

```
1 inch = 914,400 EMUs
1 point = 12,700 EMUs
Standard slide: 12,192,000 x 6,858,000 EMUs (13.33" x 7.5")
Font size attribute: sz="1500" means 15pt (hundredths of a point)
```

Common text box widths:
- Title width (single line): ≥ 2,500,000 EMUs (~2.7 inches)
- Typical caption: 1,500,000-2,000,000 EMUs
- Character width at 15pt Arial: 50,000-120,000 EMUs per character

## Workflow

1. **Register namespaces FIRST** (before any XML parse/write):
   ```python
   import xml.etree.ElementTree as ET
   ET.register_namespace('', 'http://schemas.openxmlformats.org/presentationml/2006/main')
   ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')
   ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
   ```
   **CRITICAL**: Do NOT use `ET.register_namespace('ns2', ...)` — prefixes matching `ns\d+` are reserved and raise ValueError.

   **If the source XML already contains `ns2`, `ns3`, or similar prefixes**, do NOT register them. ElementTree preserves existing prefixes automatically. Only register namespaces you need for `find()`/`findall()` queries.

2. **Open as ZIP**:
   ```python
   import zipfile
   z = zipfile.ZipFile('input.pptx', 'r')
   namelist = z.namelist()  # Returns full paths like 'ppt/slides/slide1.xml'
   slide_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
   ```

3. **Parse XML** with namespaced lookups:
   ```python
   NS = {
       'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
       'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
       'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'
   }
   root = ET.fromstring(slide_xml)
   ```

4. **Modify content**:
   - Text styling: `<a:rPr>` elements (sz for size, b for bold)
   - Colors: `<a:srgbClr val="XXXXXX"/>`
   - Position: `<a:off x="N" y="N"/>` in `<a:xfrm>`
   - Size: `<a:ext cx="N" cy="N"/>`

5. **Write Modified XML Back**:
   ```python
   # CRITICAL: Always write to a DIFFERENT file than the input.
   # Reading and writing the same ZIP file corrupts it (BadZipFile: Truncated file header).
   output = zipfile.ZipFile('output.pptx', 'w', zipfile.ZIP_DEFLATED)
   for name in namelist:
       if name == 'ppt/slides/slide1.xml':
           output.writestr(name, ET.tostring(root, encoding='unicode'))
       else:
           output.writestr(name, z.read(name))
   output.close()
   z.close()  # Close input before any further operations
   ```

6. **VALIDATE (MANDATORY — DO NOT SKIP)**:
   ```python
   # Re-read the output and verify values
   verify = zipfile.ZipFile('output.pptx', 'r')
   verify_xml = verify.read('ppt/slides/slide1.xml').decode('utf-8')
   verify_root = ET.fromstring(verify_xml)
   verify_rPr = verify_root.find('.//a:rPr', NS)
   assert verify_rPr.get('sz') == '1500', f"Font size wrong: {verify_rPr.get('sz')}"
   assert verify_rPr.get('b') == '1', "Bold not set"
   print("VALIDATION PASSED")
   ```

## Text Formatting Operations

### Modifying Font Styling

The `<a:rPr>` element controls text run properties:

```xml
<a:rPr lang="en-US" sz="1700" b="0" i="0">
  <a:solidFill>
    <a:srgbClr val="4A6A54"/>
  </a:solidFill>
  <a:latin typeface="Calibri"/>
</a:rPr>
```

| Attribute | Element | Values | Notes |
|-----------|---------|--------|-------|
| sz | a:rPr | 1700 = 17pt | In hundredths of a point |
| b | a:rPr | 0/1 | Bold off/on |
| i | a:rPr | 0/1 | Italic off/on |
| u | a:rPr | none/sng/dbl | Underline |
| typeface | a:latin | Font name | e.g., "Calibri", "Arial" |
| val | a:srgbClr | 6-char hex | RGB color without # prefix |

### Removing Bold/Italic

To remove bold or italic, either:
- Set `b="0"` or `i="0"` explicitly, OR
- Remove the attribute entirely (absence = off)

When using ElementTree, use `attrib.pop('b', None)` to safely remove without error if missing.

### Paragraph Alignment

Set alignment in `<a:pPr>`:
```xml
<a:pPr algn="ctr"/>  <!-- Center -->
<a:pPr algn="l"/>    <!-- Left -->
<a:pPr algn="r"/>    <!-- Right -->
<a:pPr algn="just"/> <!-- Justified -->
```

## endParaRPr Placement

The `endParaRPr` element must be placed **inside the last `a:p` element**, not as a direct child of `a:txBody`.

Correct:
```xml
<p:txBody>
  <a:p>
    <a:r><a:rPr .../><a:t>text</a:t></a:r>
    <a:endParaRPr lang="en-US" dirty="0"/>
  </a:p>
</p:txBody>
```

Incorrect (causes rendering issues):
```xml
<p:txBody>
  <a:p><a:r>...</a:r></a:p>
  <a:endParaRPr lang="en-US" dirty="0"/>  <!-- WRONG: direct child of txBody -->
</p:txBody>
```

## Adding a New Slide (4-Step Sync)

To add a slide, update **all four** locations atomically:

1. **Create** `ppt/slides/slide{N}.xml` with valid OOXML structure
2. **Register** in `[Content_Types].xml`:
   ```xml
   <Override PartName="/ppt/slides/slideN.xml"
             ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
   ```
3. **Add relationship** in `ppt/_rels/presentation.xml.rels`:
   ```xml
   <Relationship Id="rId{X}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slideN.xml"/>
   ```
4. **Reference** in `ppt/presentation.xml` `<p:sldIdLst>`:
   ```xml
   <p:sldId id="{UNIQUE_ID}" r:id="rId{X}"/>
   ```

**Constraints**: rId must be unique in the rels file; slide IDs must be unique (commonly 256+).

## Critical Validation Steps

**ALWAYS verify after modification — do NOT claim success without verification:**

1. Re-read the generated PPTX and parse the XML
2. Assert the modified values are present in the output
3. Check that `[Content_Types].xml` has entries for all new slides
4. Verify `presentation.xml.rels` maps every rId used in `presentation.xml`
5. Confirm file opens without corruption in PowerPoint/LibreOffice

### Text Formatting Verification Checklist

After modifying text styling, verify:
- [ ] Font size (`sz` attribute) matches expected value in hundredths of points
- [ ] Font color (`a:srgbClr val`) matches expected hex value
- [ ] Font typeface (`a:latin typeface`) is correct
- [ ] Bold/italic attributes are set or removed as intended
- [ ] Paragraph alignment (`a:pPr algn`) is correct
- [ ] Position and size (`a:off`, `a:ext`) are in valid EMU ranges

## Anti-Patterns

- **Do NOT assume XML modification succeeded** — always re-read and verify
- **Do NOT use `ns\d+` prefixes** with ET.register_namespace — raises ValueError
- **Do NOT guess EMU values** — values in hundreds produce invisible text boxes (need hundreds of thousands)
- **Do NOT skip `.rels` updates** — adding slides without relationship entries corrupts the file
- **Do NOT forget `[Content_Types].xml`** — missing Override causes repair dialog
- **Do NOT trust position calculations without testing** — EMU coordinates can display wrong due to parent transforms
- **Do NOT assume verification by XML inspection alone is sufficient** — always test file opens in actual PowerPoint/LibreOffice if possible
- **Do NOT read from and write to the same ZIP file** — causes `BadZipFile: Truncated file header`. Always use separate input/output paths.
- **Do NOT place `endParaRPr` as a direct child of `txBody`** — must be inside the last `a:p`.
- **Do NOT check `z.namelist()` with short names** like `'slide7.xml'` — it returns full paths like `'ppt/slides/slide7.xml'`.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| ValueError: Prefix reserved | Using ns\d+ prefix | Use descriptive prefix like 'p14', or don't register if already in source XML |
| BadZipFile: Truncated file header | Reading and writing same ZIP file | Use separate input and output file paths |
| Repair dialog on open | Missing Content_Types entry | Add Override for new slide |
| Slide wrong order/blank | rId mismatch | Verify rId matches in presentation.xml and .rels |
| Changes not appearing | Wrote to wrong path | Check exact path in writestr() |
| Text box invisible | Width too small (hundreds of EMUs) | Use ≥2,500,000 EMUs for single-line titles |

## Known Invariants (by sub-task)

### Museum caption formatting (B1)
- Text box width must be ≥2,500,000 EMUs for single-line titles (values in hundreds produce invisible boxes)
- Position values must account for parent shape transforms
- Font sz attribute is in hundredths of points, not EMUs
- Color hex is 6 characters without # prefix

### Slide addition (B2)
- All 4 files must be updated atomically
- rId in presentation.xml must match exactly the Id in .rels
- Slide ID (id attribute) must not collide with existing IDs

## Fallback Strategy

If direct XML manipulation fails verification:
1. Compare before/after XML structures for unexpected changes
2. Validate against a known-good PPTX template
3. Test with multiple PowerPoint viewers (files may open but have hidden corruption)
4. If XML looks correct but file fails to open, check for namespace declaration issues or missing required elements

## References

See `references/pptx-structure.md` for detailed EMU conversions, font width estimates, and XML element hierarchies.
