---
name: pptx-xml-editing
description: Manipulate PowerPoint (.pptx) files via direct XML editing when python-pptx is unavailable or insufficient. Use for formatting text, repositioning elements, adding slides, or fine-grained OOXML control.
---

# PowerPoint XML Editing

PowerPoint files are ZIP archives containing Office Open XML (OOXML). When high-level libraries fail or are unavailable, edit the XML directly via Python's `zipfile` and `xml.etree.ElementTree`.

## When to Use

- python-pptx cannot perform the required operation
- You need precise control over XML attributes not exposed by high-level APIs
- You're working with corrupted or non-standard PPTX files
- You need to add/modify slides, shapes, or text styling at the XML level

## Core Workflow

1. **Open as ZIP**: Use `zipfile.ZipFile()` — never rely on system `unzip` command availability
2. **Read XML**: Extract specific files to strings or BytesIO, parse with `ET.fromstring()`
3. **Modify**: Use namespaced lookups (e.g., `{http://...}tag`)
4. **Write back**: Replace zip entries with `writestr()` (no external extraction required)
5. **Validate**: Re-parse the output and assert expected values are present (MANDATORY)

## Critical Namespaces (REQUIRED FIRST STEP)

Register these prefixes **before any XML parse/write cycle** to avoid arbitrary `ns0`, `ns1` generation:

```python
import xml.etree.ElementTree as ET

ET.register_namespace('', 'http://schemas.openxmlformats.org/presentationml/2006/main')
ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')
ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
```

**Do not** use `ET.register_namespace('ns2', ...)` — prefixes matching `ns\d+` are reserved for internal use and raise ValueError.

## Key Measurements (INLINE — Do Not Guess)

- **1 inch = 914,400 EMUs**
- **1 point = 12,700 EMUs**
- **1 cm = 360,000 EMUs**
- **Standard slide dimensions: 12,192,000 x 6,858,000 EMUs (13.33" x 7.5")**
- **Font size: sz="1500" = 15pt (in hundredths of a point)**
- **Character width at 15pt Arial**: narrow ~50,000, average ~85,000, wide ~100,000 EMUs

**Anti-pattern**: Values in the hundreds will produce invisible/narrow text boxes. Character widths at 15pt Arial are 50,000–120,000 EMUs per character.

## Key File Locations

| File | Purpose |
|------|---------|
| `[Content_Types].xml` | Declares content types for all parts; **must** add Override for new slides |
| `ppt/presentation.xml` | Contains `<p:sldIdLst>` referencing all slides by rId |
| `ppt/_rels/presentation.xml.rels` | Maps rIds to slide file paths (e.g., `slides/slide7.xml`) |
| `ppt/slides/slide{N}.xml` | Individual slide content |
| `ppt/slideLayouts/`, `ppt/slideMasters/` | Layout and master slide definitions |

## Adding a New Slide (4-Step Sync)

To add a slide, update **all four** locations atomically:

1. **Create** `ppt/slides/slide{N}.xml` with valid OOXML structure
2. **Register** in `[Content_Types].xml`:
   `<Override PartName="/ppt/slides/slideN.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>`
3. **Add relationship** in `ppt/_rels/presentation.xml.rels`:
   `<Relationship Id="rId{X}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slideN.xml"/>`
4. **Reference** in `ppt/presentation.xml` `<p:sldIdLst>`:
   `<p:sldId id="{UNIQUE_ID}" r:id="rId{X}"/>`

**Constraints**:
- Relationship IDs (rId) must be unique across the .rels file
- Slide IDs (id attribute) must be unique across the presentation (commonly 256+)
- Type attribute in Content_Types must exactly match the OOXML slide content type

## Modifying Text Formatting

Text inside shapes lives under `<a:t>` elements. Text formatting is on sibling or parent `<a:rPr>` (run properties):

- Font: `<a:latin typeface="Arial"/>` inside `<a:rPr>`
- Size: `sz="1500"` (in hundredths of a point, so 1500 = 15pt)
- Color: `<a:solidFill><a:srgbClr val="6F6C64"/></a:solidFill>` inside `<a:rPr>`
- Bold: `b="1"` attribute present or absent

Position and size are on `<a:xfrm>` in `<p:spPr>`:
- Offset: `<a:off x="..." y="..."/>` (in EMUs: 914400 EMUs = 1 inch)
- Extent: `<a:ext cx="..." cy="..."/>`

## Mandatory Validation (After Every Modification)

**You must re-parse and verify the output. Do NOT claim success without validation:**

```python
# After writestr(), immediately read back and verify:
z = zipfile.ZipFile('output.pptx', 'r')
slide_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
# Parse and assert expected values are present
root = ET.fromstring(slide_xml)
# Check: sz attribute, position, color, text content, etc.
```

**Validation checklist**:
- [ ] `[Content_Types].xml` contains Override for every new slide XML
- [ ] `presentation.xml.rels` maps the rId used in presentation.xml
- [ ] `presentation.xml` sldIdLst contains entry for the new slide
- [ ] Slide ID numbers are unique and do not collide with existing slides
- [ ] XML is valid (no unclosed tags, namespaces declared)
- [ ] Modified elements have correct values (parse and print them)
- [ ] File opens without corruption in PowerPoint/LibreOffice

## Anti-Patterns

- **Do not** assume XML modification succeeded based on string replacement alone — re-parse and verify
- **Do not** guess EMU values — use inline values above (50,000+ for character widths)
- **Do not** use `ET.register_namespace('ns2', ...)` — ValueError on reserved prefixes
- **Do not** write XML with string concatenation — use ElementTree to ensure valid XML
- **Do not** forget to update `[Content_Types].xml` when adding parts — PowerPoint will error
- **Do not** reuse relationship IDs across different target files
- **Do not** skip verification by opening the file in a viewer — parse the XML programmatically

## Troubleshooting

| Symptom | Likely Cause |
|---------|--------------|
| "ValueError: Prefix format reserved for internal use" | Using `ET.register_namespace('ns2', ...)` — change prefix to descriptive name like 'p14' |
| PowerPoint shows repair dialog | Missing Content_Types entry, or malformed XML in new slide |
| Slide appears blank or wrong order | Mismatched rId between presentation.xml and .rels file, or duplicate slide IDs |
| Changes not appearing | Modified XML but didn't write back to zip, or wrote to wrong path in archive |
| Invisible/narrow text boxes | EMU values in hundreds instead of hundreds-of-thousands |

## References

For detailed XML schemas and element hierarchies, see `references/pptx-structure.md`.