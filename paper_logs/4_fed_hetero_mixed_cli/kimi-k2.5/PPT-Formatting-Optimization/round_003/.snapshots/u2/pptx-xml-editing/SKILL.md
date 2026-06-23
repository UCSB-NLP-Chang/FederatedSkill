---
name: pptx-xml-editing
description: Edit PowerPoint (.pptx) files via direct ZIP/XML manipulation when python-pptx is unavailable or insufficient. Use for formatting text, repositioning elements, cloning/adding slides, or fine-grained OOXML control. Helper utilities available in scripts/pptx_helpers.py for bulk operations.
---

# PowerPoint XML Editing

PowerPoint files are ZIP archives containing Office Open XML (OOXML). When high-level libraries fail or are unavailable, edit the XML directly via Python's `zipfile` and `xml.etree.ElementTree`.

## When to Use

- python-pptx cannot perform the required operation
- You need precise control over XML attributes not exposed by high-level APIs
- You're working with corrupted or non-standard PPTX files
- You need to add/modify slides, shapes, or text styling at the XML level
- You need to clone existing slides as templates for new content

## EMU & Font Constants (MEMORIZE — Inline These)

```
1 inch = 914,400 EMUs
1 point = 12,700 EMUs
Standard slide: 12,192,000 x 6,858,000 EMUs (13.33" x 7.5")
Font size: sz="1500" = 15pt (hundredths of a point)
```

Common text box widths:
- Title (single line): ≥ 2,500,000 EMUs (~2.7 inches)
- Typical caption: 1,500,000-2,000,000 EMUs
- Character width at 15pt Arial: 50,000-120,000 EMUs per character

**Anti-pattern**: Values in hundreds produce invisible/narrow text boxes.

## Core Workflow

### Step 1: Register Namespaces (REQUIRED FIRST)

```python
import xml.etree.ElementTree as ET
ET.register_namespace('', 'http://schemas.openxmlformats.org/presentationml/2006/main')
ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')
ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
```

**NEVER use `ET.register_namespace('ns2', ...)`** — `ns\d+` prefixes are reserved and raise ValueError.

**If source XML already contains `ns2`, `ns3`, etc.**, do NOT register them. ElementTree preserves existing prefixes. Only register namespaces for your own `find()`/`findall()` queries.

### Step 2: Open PPTX as ZIP

```python
import zipfile
z = zipfile.ZipFile('input.pptx', 'r')
namelist = z.namelist()  # Returns full paths like 'ppt/slides/slide1.xml'
slide_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
```

### Step 3: Parse & Modify XML

```python
root = ET.fromstring(slide_xml)
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

# Find and modify text run properties
rPr = root.find('.//a:rPr', NS)
rPr.set('sz', '1700')  # 17pt font
rPr.set('b', '0')      # Bold off (remove or set to '0')

# Find position/size
xfrm = root.find('.//a:xfrm', NS)
off = xfrm.find('a:off', NS)
off.set('x', '1096000')
off.set('y', '6258000')
ext = xfrm.find('a:ext', NS)
ext.set('cx', '2500000')
ext.set('cy', '400000')
```

### Step 4: Write Modified XML Back

```python
# CRITICAL: Write to a DIFFERENT file than the input.
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

### Step 5: VALIDATE (MANDATORY — DO NOT SKIP)

```python
# Re-read output and assert values are correct
verify = zipfile.ZipFile('output.pptx', 'r')
verify_xml = verify.read('ppt/slides/slide1.xml').decode('utf-8')
verify_root = ET.fromstring(verify_xml)
verify_rPr = verify_root.find('.//a:rPr', NS)
assert verify_rPr.get('sz') == '1700', f"Font size wrong: {verify_rPr.get('sz')}"
assert verify_rPr.get('b') == '0', "Bold not removed"
print("VALIDATION PASSED")
```

**Validation checklist**:
- [ ] Modified attributes have correct values (parse and assert them)
- [ ] `[Content_Types].xml` contains Override for every new slide
- [ ] `presentation.xml.rels` maps the rId used in presentation.xml
- [ ] `presentation.xml` sldIdLst contains entry for new slides
- [ ] Slide IDs are unique and do not collide
- [ ] XML is valid (no unclosed tags, namespaces declared)

## Text Formatting Attributes

| Attribute | Element | Values | Notes |
|-----------|---------|--------|-------|
| sz | a:rPr | 1700 = 17pt | Hundredths of a point |
| b | a:rPr | 0/1 | Bold off/on; use `attrib.pop('b', None)` to remove |
| i | a:rPr | 0/1 | Italic off/on; use `attrib.pop('i', None)` to remove |
| val | a:srgbClr | 4A6A54 | RGB hex without # |
| typeface | a:latin | Calibri | Font name |
| algn | a:pPr | l/r/ctr/just | Paragraph alignment |

### Removing Bold/Italic

Use `attrib.pop('b', None)` or `attrib.pop('i', None)` to safely remove without error if missing:

```python
rPr.attrib.pop('b', None)  # Remove bold
rPr.attrib.pop('i', None)  # Remove italic
```

## endParaRPr Placement

The `endParaRPr` element must be placed **inside the last `a:p` element**, not as a direct child of `a:txBody`.

Correct:
```xml
<a:txBody>
  <a:p>
    <a:r><a:rPr .../><a:t>text</a:t></a:r>
    <a:endParaRPr lang="en-US" dirty="0"/>
  </a:p>
</a:txBody>
```

Incorrect (causes rendering issues):
```xml
<a:txBody>
  <a:p><a:r>...</a:r></a:p>
  <a:endParaRPr lang="en-US" dirty="0"/>  <!-- WRONG -->
</a:txBody>
```

## Adding a New Slide (4-Step Sync)

**PREFER STRING TEMPLATES over ElementTree** for creating new slide XML. ElementTree frequently produces duplicate namespace declarations and `r:r:id` double-prefix bugs. See `references/pptx-structure.md` for a complete string template example.

Update **all four** files atomically:

### 1. Create slide XML
Create `ppt/slides/slide{N}.xml` with valid structure. Use a string template (see references) rather than ElementTree construction.

### 2. Register in `[Content_Types].xml`
Add inside `<Types>`:
```xml
<Override PartName="/ppt/slides/slideN.xml"
          ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
```

### 3. Add relationship in `ppt/_rels/presentation.xml.rels`
Add inside `<Relationships>`:
```xml
<Relationship Id="rId{X}"
              Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
              Target="slides/slideN.xml"/>
```
**rId must be unique** — check existing rIds first.

### 4. Reference in `ppt/presentation.xml`
Add inside `<p:sldIdLst>`:
```xml
<p:sldId id="{NUM}" r:id="rId{X}"/>
```
**Slide ID must be unique** — typically start at 256+.

**CRITICAL: When using ElementTree to add sldId**, do NOT use `element.set(f'{{{R_NS}}}r:id', 'rIdX')` — this produces `r:r:id` (double prefix) in the serialized output. Either:
- Use string replacement after serialization: `xml_str.replace('r:r:id=', 'r:id=')`
- Or build the entire presentation.xml modification via string template

## Cloning a Slide (Template Pattern)

When creating a new slide by copying an existing one as a template:

```python
# 1. Read template slide XML
template_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
new_root = ET.fromstring(template_xml)

# 2. Modify content - REMOVE unwanted placeholder shapes
# Find and remove shapes not needed in new slide
sp_tree = new_root.find('.//p:spTree', NS)
for sp in sp_tree.findall('p:sp', NS):
    cNvPr = sp.find('p:nvSpPr/p:cNvPr', NS)
    if cNvPr is not None:
        name = cNvPr.get('name', '')
        # Remove specific placeholders by name
        if name in ['Text Placeholder 3', 'Content Placeholder 2']:
            sp_tree.remove(sp)

# 3. Add new content (text runs, bullets, etc.)
# ... modify XML ...

# 4. Write new slide XML explicitly (common bug: forgetting this)
output.writestr('ppt/slides/slide7.xml', ET.tostring(new_root, encoding='unicode'))
```

**CRITICAL**: When iterating `namelist()` to copy files, the new slide won't be in the source list. You must write it explicitly:

```python
for name in namelist:
    if name == 'ppt/slides/slide1.xml':
        output.writestr(name, ET.tostring(modified_root, encoding='unicode'))
    else:
        output.writestr(name, z.read(name))
# MUST explicitly write new slides not in original namelist
output.writestr('ppt/slides/slide7.xml', ET.tostring(new_slide_root, encoding='unicode'))
```

## Auto-Numbered Bullets (buAutoNum)

For numbered lists that automatically increment:

```xml
<a:p>
  <a:pPr>
    <a:buFont typeface="Arial"/>
    <a:buAutoNum type="arabicPeriod" startAt="1"/>
  </a:pPr>
  <a:r>
    <a:t>First item</a:t>
  </a:r>
</a:p>
```

**Key points**:
- `type`: `arabicPeriod` (1.), `arabicParenR` (1)), `romanLcParenBoth`, `alphaLcPeriod`
- `startAt`: 1 for first item, but PowerPoint may auto-adjust based on position
- Each paragraph (`<a:p>`) with `buAutoNum` becomes one numbered item
- Numbering continues sequentially across paragraphs in the same text body

**Validation**: Check that `buAutoNum` elements exist and have correct `type` attribute.

## Bulk Operations (Optional Helpers)

For bulk text modifications or caption repositioning, helper functions are available:

```python
from scripts.pptx_helpers import extract_slide_text_mapping, find_shape_by_text
from scripts.pptx_helpers import get_text_width_emu, bottom_center_position

# Map file to find captions
texts = extract_slide_text_mapping('input.pptx')
# Find shape by text content when IDs are unknown
info = find_shape_by_text('input.pptx', slide_num, 'Target Caption')
# Calculate text width for sizing
width = get_text_width_emu('Sample Text', 17)
# Get bottom-center coordinates
x, y = bottom_center_position(width, 400000)
```

**Note**: Helper functions supplement the workflow; core EMU constants above must be memorized.

## Anti-Patterns

- **Do NOT** read from and write to the same ZIP file — causes `BadZipFile: Truncated file header`. Always use separate input/output paths.
- **Do NOT** use `ET.register_namespace('ns2', ...)` — ValueError on reserved prefixes.
- **Do NOT** place `endParaRPr` as direct child of `txBody` — must be inside last `a:p`.
- **Do NOT** guess EMU values — use inline constants above.
- **Do NOT** skip Step 5 validation — verifier will fail.
- **Do NOT** forget `[Content_Types].xml` when adding slides — repair dialog.
- **Do NOT** reuse rId values — must be unique per .rels file.
- **Do NOT** check `namelist()` with short names like `'slide7.xml'` — returns full paths like `'ppt/slides/slide7.xml'`.
- **Do NOT** forget to write new slide XML explicitly when cloning — the new file won't be in the source namelist.
- **Do NOT** leave placeholder shapes in cloned slides — remove unwanted `p:sp` elements before adding content.
- **Do NOT** use `element.set(f'{{{R_NS}}}r:id', 'rIdX')` with ElementTree — produces `r:r:id` (double prefix) in output. Use string replacement or string templates.
- **Do NOT** construct new slide XML with ElementTree — namespace duplication (`xmlns` appearing twice) is common. Use string templates instead.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| ValueError: Prefix reserved | Using ns\d+ prefix | Use descriptive prefix like 'p14', or don't register if already in source |
| BadZipFile: Truncated header | Reading/writing same ZIP | Use separate input and output file paths |
| Repair dialog on open | Missing Content_Types entry | Add Override for new slide |
| Slide wrong order/blank | rId mismatch | Verify rId matches in presentation.xml and .rels |
| Changes not appearing | Wrote to wrong path | Check exact path in writestr() |
| Text box invisible | Width too small (hundreds) | Use ≥2,500,000 EMUs for single-line titles |
| Verifier fails after success | Validation incomplete | Parse output and assert values explicitly |
| New slide missing | Forgot explicit writestr | New slides not in source namelist must be written separately |
| Duplicate shapes in new slide | Cloned placeholders not removed | Remove unwanted `p:sp` elements from template XML |
| Numbering starts at wrong value | buAutoNum startAt or position | Check each paragraph has buAutoNum, startAt="1" |
| `r:r:id` in output XML | ElementTree double-prefix bug | Use `.replace('r:r:id=', 'r:id=')` after serialization, or use string templates |
| Duplicate `xmlns` attributes | ElementTree namespace handling | Use string templates for new slide creation |

## Known Invariants (by sub-task)

### Museum caption formatting
- Text box width must be ≥2,500,000 EMUs for single-line titles
- Font sz attribute is in hundredths of points, not EMUs
- Position values must account for parent shape transforms

### Slide addition
- All 4 files must be updated atomically
- rId in presentation.xml must match exactly the Id in .rels
- Slide ID (id attribute) must not collide with existing IDs
- When cloning, remove placeholder shapes before adding content
- Must explicitly write new slide XML — won't be in source namelist

### Auto-numbered lists
- Each list item is a separate `<a:p>` paragraph
- `buAutoNum` goes in `<a:pPr>` inside the paragraph
- Numbering continues sequentially; use `startAt` to reset if needed

## Fallback Strategy

If verification fails despite correct XML:
1. Compare before/after XML structures for unexpected changes
2. Validate against a known-good PPTX template
3. Test with multiple viewers (hidden corruption may exist)
4. Check namespace declarations and required elements
5. For new slides: verify all 4 files updated, no orphaned shapes, correct rId mapping

## References

See `references/pptx-structure.md` for XML schemas, element hierarchies, and detailed buAutoNum documentation.
See `scripts/pptx_helpers.py` for reusable helper functions.
