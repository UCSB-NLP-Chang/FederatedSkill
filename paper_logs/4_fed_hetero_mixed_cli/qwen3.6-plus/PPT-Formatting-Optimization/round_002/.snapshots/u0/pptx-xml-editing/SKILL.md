---
name: pptx-xml-editing
description: Edit PowerPoint (.pptx) files via direct ZIP/XML manipulation when python-pptx is unavailable or insufficient. Use for formatting text, repositioning elements, adding slides, or fine-grained OOXML control.
---

# PowerPoint XML Editing

## When to Use
- python-pptx library is unavailable or cannot perform the operation
- You need precise control over XML attributes (font size, color, position, dimensions)
- You need to add/modify slides, shapes, or text styling at the XML level
- You're working with non-standard or corrupted PPTX files

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

## Core Workflow

### Step 1: Register Namespaces (REQUIRED FIRST)

```python
import xml.etree.ElementTree as ET
ET.register_namespace('', 'http://schemas.openxmlformats.org/presentationml/2006/main')
ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')
ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
```

**NEVER use `ET.register_namespace('ns2', ...)`** — `ns\d+` prefixes are reserved and raise ValueError.

**If the source XML already contains `ns2`, `ns3`, or similar prefixes**, do NOT register them. ElementTree preserves existing prefixes automatically. Only register namespaces you need for `find()`/`findall()` queries.

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
# Use full namespace URIs for find():
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

# Find text run properties
rPr = root.find('.//a:rPr', NS)
rPr.set('sz', '1500')  # 15pt font
rPr.set('b', '1')      # Bold on

# Find position/size
xfrm = root.find('.//a:xfrm', NS)
off = xfrm.find('a:off', NS)
off.set('x', '1096000')  # X position in EMUs
off.set('y', '6258000')  # Y position in EMUs
ext = xfrm.find('a:ext', NS)
ext.set('cx', '2500000')  # Width in EMUs
ext.set('cy', '400000')   # Height in EMUs
```

### Step 4: Write Modified XML Back

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

### Step 5: VALIDATE (MANDATORY — DO NOT SKIP)

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

## Adding a New Slide (4-Step Sync)

Update ALL FOUR files atomically:

### 1. Create slide XML
Create `ppt/slides/slide{N}.xml` with valid structure (copy from existing slide as template).

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
**Slide ID must be unique** — typically start at 256, increment for each new slide.

## Text Formatting Attributes

| Attribute | Element | Values | Notes |
|-----------|---------|--------|-------|
| sz | a:rPr | 1500 = 15pt | Hundredths of a point |
| b | a:rPr | 0/1 | Bold |
| i | a:rPr | 0/1 | Italic |
| val | a:srgbClr | 6F6C64 | RGB hex without # |
| algn | a:pPr | l/r/ctr/just | Alignment |

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

## Anti-Patterns

- **Do NOT** use `ET.register_namespace('ns2', ...)` — ValueError
- **Do NOT** guess EMU values — use constants above
- **Do NOT** skip Step 5 validation — verifier will fail
- **Do NOT** forget Content_Types when adding slides — PowerPoint shows repair dialog
- **Do NOT** reuse rId values — must be unique per .rels file
- **Do NOT** read from and write to the same ZIP file — causes `BadZipFile: Truncated file header`. Always use separate input/output paths.
- **Do NOT** place `endParaRPr` as a direct child of `txBody` — must be inside the last `a:p`.
- **Do NOT** check `z.namelist()` with short names like `'slide7.xml'` — it returns full paths like `'ppt/slides/slide7.xml'`.

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

### Museum caption formatting
- Text box width must be ≥2,500,000 EMUs for single-line titles (values in hundreds produce invisible boxes)
- Position values must account for parent shape transforms
- Font sz attribute is in hundredths of points, not EMUs

### Slide addition
- All 4 files must be updated atomically
- rId in presentation.xml must match exactly the Id in .rels
- Slide ID (id attribute) must not collide with existing IDs

## References

- `references/pptx-structure.md` — Detailed EMU conversions, font width estimates, XML element hierarchies
- `scripts/pptx_helpers.py` — Helper functions for text extraction, shape finding, bulk formatting