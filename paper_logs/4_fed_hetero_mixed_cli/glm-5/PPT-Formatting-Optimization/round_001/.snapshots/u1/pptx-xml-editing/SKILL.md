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

## Core Concepts

PPTX files are ZIP archives containing Office Open XML (OOXML). Key files:

| File | Purpose |
|------|---------|
| `ppt/slides/slideN.xml` | Individual slide content |
| `ppt/presentation.xml` | Slide order via `<p:sldIdLst>` |
| `ppt/_rels/presentation.xml.rels` | Maps rIds to slide paths |
| `[Content_Types].xml` | Content type declarations |

## Key Measurements

- Slide dimensions: 12,192,000 x 6,858,000 EMUs (16:9 default)
- 1 inch = 914,400 EMUs
- 1 point = 12,700 EMUs
- Font size in hundredths of a point (sz="1500" = 15pt)

## Workflow

1. **Open as ZIP**:
   ```python
   import zipfile
   z = zipfile.ZipFile('file.pptx')
   slide_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
   ```

2. **Register namespaces FIRST** (before any XML parse/write):
   ```python
   import xml.etree.ElementTree as ET
   ET.register_namespace('', 'http://schemas.openxmlformats.org/presentationml/2006/main')
   ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')
   ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
   ```
   **CRITICAL**: Do NOT use `ET.register_namespace('ns2', ...)` — prefixes matching `ns\d+` are reserved and raise ValueError.

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

5. **Rebuild and VERIFY**:
   ```python
   # Write back to ZIP
   # CRITICAL: Re-read and parse the output to verify changes
   z2 = zipfile.ZipFile('output.pptx', 'w', zipfile.ZIP_DEFLATED)
   # ... write files ...
   z2.close()
   
   # VERIFY: Re-parse and check values
   z3 = zipfile.ZipFile('output.pptx')
   verify_xml = z3.read('ppt/slides/slide1.xml').decode('utf-8')
   verify_root = ET.fromstring(verify_xml)
   # Assert expected values are present
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

## Anti-Patterns

- **Do NOT assume XML modification succeeded** — always re-read and verify
- **Do NOT use `ns\d+` prefixes** with ET.register_namespace — raises ValueError
- **Do NOT guess EMU values** — values in hundreds produce invisible text boxes (need hundreds of thousands)
- **Do NOT skip `.rels` updates** — adding slides without relationship entries corrupts the file
- **Do NOT forget `[Content_Types].xml`** — missing Override causes repair dialog
- **Do NOT trust position calculations without testing** — EMU coordinates can display wrong due to parent transforms

## Known Invariants

### Text formatting (B1)
- Font size attribute `sz` is in hundredths of a point (1500 = 15pt)
- Color hex is 6 characters without # prefix
- Position/size in `<a:xfrm>` use EMUs

### Slide addition (B2)
- All four files must be updated atomically
- rId values must be unique and sequential
- Slide IDs (id attribute) must be unique across presentation

## Fallback Strategy

If direct XML manipulation fails verification:
1. Compare before/after XML structures for unexpected changes
2. Validate against a known-good PPTX template
3. Test with multiple PowerPoint viewers (files may open but have hidden corruption)

## References

See `references/pptx-structure.md` for detailed EMU conversions, font width estimates, and XML element hierarchies.
