---
name: pptx-xml-editing
description: Edit PowerPoint (.pptx) files via direct ZIP/XML manipulation when python-pptx is unavailable or insufficient. Use for formatting text, repositioning elements, cloning/adding slides, working with grouped shapes, or fine-grained OOXML control.
---

# PowerPoint XML Editing

## When to Use
- python-pptx library is unavailable or cannot perform the operation
- You need precise control over XML attributes (font size, color, position, dimensions)
- You need to add/clone/modify slides, shapes, or text styling at the XML level
- You're working with non-standard or corrupted PPTX files
- You need to extract or modify text within grouped shapes

## EMU & Font Constants (MEMORIZE)

```
1 inch = 914,400 EMUs
1 point = 12,700 EMUs
Standard slide: 12,192,000 x 6,858,000 EMUs (13.33" x 7.5")
Font size attribute: sz="1500" means 15pt (hundredths of a point)
```

Common text box widths:
- Title width (single line): >= 2,500,000 EMUs (~2.7 inches)
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

**NEVER use `ET.register_namespace('ns2', ...)`** - `ns\d+` prefixes are reserved and raise ValueError.

**If the source XML already contains `ns2`, `ns3`, or similar prefixes**, do NOT register them. ElementTree preserves existing prefixes automatically.

### Step 2: Open PPTX as ZIP

```python
import zipfile
z = zipfile.ZipFile('input.pptx', 'r')
namelist = z.namelist()  # Returns full paths like 'ppt/slides/slide1.xml'
slide_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
```

**CRITICAL: `namelist()` order is arbitrary** - Files are NOT returned in sorted order. When processing slides sequentially or when order matters, explicitly sort:

```python
# WRONG: namelist order is random, may process slide3 before slide1
for name in namelist:
    if 'slide' in name:
        process(name)

# CORRECT: Process in explicit numerical order
import re
slide_files = [n for n in namelist if re.match(r'ppt/slides/slide\d+\.xml$', n)]
slide_files.sort(key=lambda x: int(re.search(r'slide(\d+)', x).group(1)))
for slide_path in slide_files:
    process(slide_path)
```

### Step 3: Parse & Modify XML

```python
root = ET.fromstring(slide_xml)
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

# Find text run properties
rPr = root.find('.//a:rPr', NS)
rPr.set('sz', '1500')  # 15pt font
rPr.set('b', '1')      # Bold on

# Remove bold/italic safely
rPr.attrib.pop('b', None)  # Remove if exists
rPr.attrib.pop('i', None)
```

### Step 4: Write Modified XML Back

```python
# CRITICAL: Always write to a DIFFERENT file than the input.
output = zipfile.ZipFile('output.pptx', 'w', zipfile.ZIP_DEFLATED)
for name in namelist:
    if name == 'ppt/slides/slide1.xml':
        output.writestr(name, ET.tostring(root, encoding='unicode'))
    else:
        output.writestr(name, z.read(name))
output.close()
z.close()
```

### Step 5: VALIDATE (MANDATORY - DO NOT SKIP)

Use `scripts/validate_pptx.py` for robust validation, or run inline:

```python
verify = zipfile.ZipFile('output.pptx', 'r')
verify_xml = verify.read('ppt/slides/slide1.xml').decode('utf-8')
verify_root = ET.fromstring(verify_xml)
verify_rPr = verify_root.find('.//a:rPr', NS)
assert verify_rPr.get('sz') == '1500', f"Font size wrong: {verify_rPr.get('sz')}"
print("VALIDATION PASSED")
```

## Extracting Text from Shapes

Text in PPTX shapes can be split across multiple `<a:r>` (run) elements within a single paragraph. **Always concatenate all `<a:t>` elements**:

```python
# WRONG: Only gets first run, misses text split across runs
text = shape.find('.//a:t', NS).text

# CORRECT: Get all text runs and concatenate
texts = [t.text for t in shape.findall('.//a:t', NS) if t.text]
full_text = ''.join(texts).strip()
```

This is common when text has formatting changes mid-sentence or was edited incrementally (e.g., "Civic Center " and "Transfer Hall" as separate runs).

## Working with Grouped Shapes

Shapes can be nested inside `<p:grpSp>` (group shape) elements. When modifying grouped shapes:

```python
# Find group by name pattern
for grp in root.findall('.//p:grpSp', NS):
    cNvPr = grp.find('p:nvGrpSpPr/p:cNvPr', NS)
    if cNvPr is not None and 'Caption Group' in cNvPr.get('name', ''):
        # Iterate shapes within the group (direct children of grpSp)
        for sp in grp.findall('p:sp', NS):
            sp_cNvPr = sp.find('p:nvSpPr/p:cNvPr', NS)
            if sp_cNvPr is not None:
                name = sp_cNvPr.get('name', '')
                if 'Caption Banner Text' in name:
                    grp.remove(sp)  # Remove from group, preserves siblings
                elif 'Badge' in name or 'Note' in name:
                    pass  # Preserve these shapes
```

**Key points:**
- Grouped shapes are direct children of `<p:grpSp>`, not the slide's `<p:spTree>`
- Remove shapes from their parent group using `grp.remove(sp)`
- Sibling shapes (Badge, Note, etc.) are preserved by only removing the target
- Group position/transform is in `<p:grpSpPr><a:xfrm>`; child positions are relative

## Shape Targeting & Batch Formatting
When cleaning up or reformatting existing slides:
1. **Identify shapes** by `p:cNvPr name` attribute or by searching text content.
2. **Modify multiple attributes** in one pass: font (`a:latin typeface`), size (`a:rPr sz`), color (`a:solidFill/a:srgbClr val`), bold/italic (`a:rPr b/i`), alignment (`a:pPr algn`).
3. **Adjust geometry** via `a:xfrm`: `a:off` (x, y) and `a:ext` (cx, cy).
4. **Remove unwanted attributes** safely: `rPr.attrib.pop('b', None)`.
5. **Validate** by re-reading the output ZIP and asserting key attributes.

## Replacing Text with Auto-Numbered Bullets
To replace existing paragraph content with `buAutoNum`:
1. Locate the target `<a:p>` element.
2. Clear existing `<a:r>` children.
3. Add `<a:pPr><a:buAutoNum type="arabicPeriod" startAt="1"/></a:pPr>`.
4. Append new `<a:r><a:rPr lang="en-US"/><a:t>Item text</a:t></a:r>`.
5. Ensure each numbered item gets its own `<a:p>` with `buAutoNum`.

**CRITICAL: buAutoNum startAt Rule**
- Use `startAt="1"` on EVERY paragraph in the sequence, NOT incrementing values.
- PowerPoint automatically continues numbering (1, 2, 3...) when each paragraph has `startAt="1"`.
- Using `startAt="2"`, `startAt="3"`, etc. resets numbering on each paragraph, producing "1. 1. 1." instead of "1. 2. 3."

## Adding a New Slide (4-Step Sync)

**PREFER STRING TEMPLATES over ElementTree** for creating new slide XML. ElementTree produces duplicate xmlns and `r:r:id` double-prefix bugs. See `references/pptx-structure.md` for string template.

Update ALL FOUR files atomically:

### 1. Create slide XML
Create `ppt/slides/slide{N}.xml` with valid structure. Use string template.

### 2. Register in `[Content_Types].xml`
```xml
<Override PartName="/ppt/slides/slideN.xml"
          ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
```

### 3. Add relationship in `ppt/_rels/presentation.xml.rels`
```xml
<Relationship Id="rId{X}"
              Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
              Target="slides/slideN.xml"/>
```
**rId must be unique** - check existing rIds first.

### 4. Reference in `ppt/presentation.xml`
```xml
<p:sldId id="{NUM}" r:id="rId{X}"/>
```
**Slide ID must be unique** - typically start at 256+.

**CRITICAL: When using ElementTree to add sldId**, do NOT use `element.set(f'{{{R_NS}}}r:id', 'rIdX')` - this produces `r:r:id` (double prefix). Use:
- `xml_str.replace('r:r:id=', 'r:id=')` after serialization
- Or string template approach

**CRITICAL: New slide writing pattern**
When rebuilding the PPTX, new slides are NOT in the source namelist. You must:
1. Iterate source namelist, writing modified entries
2. AFTER the loop, explicitly write new slide XML: `output.writestr('ppt/slides/slide7.xml', slide7_xml)`
3. Do NOT rely on conditional replacement inside the namelist loop for new files

## Cloning a Slide (Template Pattern)

```python
template_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
new_root = ET.fromstring(template_xml)

# Remove unwanted placeholder shapes
sp_tree = new_root.find('.//p:spTree', NS)
for sp in sp_tree.findall('p:sp', NS):
    cNvPr = sp.find('p:nvSpPr/p:cNvPr', NS)
    if cNvPr is not None and 'Placeholder' in cNvPr.get('name', ''):
        sp_tree.remove(sp)

# MUST explicitly write new slide - not in source namelist
output.writestr('ppt/slides/slide7.xml', ET.tostring(new_root, encoding='unicode'))
```

## Auto-Numbered Bullets (buAutoNum)

```xml
<a:p>
  <a:pPr>
    <a:buAutoNum type="arabicPeriod" startAt="1"/>
  </a:pPr>
  <a:r><a:t>First item</a:t></a:r>
</a:p>
```

| type | Output |
|------|--------|
| arabicPeriod | 1. 2. 3. |
| alphaLcParenR | a) b) c) |
| romanLcParenBoth | (i) (ii) |

## Text Formatting Attributes

| Attribute | Element | Values | Notes |
|-----------|---------|--------|-------|
| sz | a:rPr | 1500 = 15pt | Hundredths of a point |
| b | a:rPr | 0/1 | Bold |
| i | a:rPr | 0/1 | Italic |
| val | a:srgbClr | 6F6C64 | RGB hex without # |
| algn | a:pPr | l/r/ctr/just | Alignment |

## Anti-Patterns

- **Do NOT** use `ET.register_namespace('ns2', ...)` - ValueError
- **Do NOT** guess EMU values - use constants above
- **Do NOT** skip Step 5 validation - verifier will fail
- **Do NOT** forget Content_Types when adding slides - repair dialog
- **Do NOT** reuse rId values - must be unique per .rels file
- **Do NOT** read/write same ZIP file - BadZipFile: Truncated file header
- **Do NOT** place `endParaRPr` as direct child of `txBody` - inside last `a:p`
- **Do NOT** check namelist() with short names like `'slide7.xml'` - full paths like `'ppt/slides/slide7.xml'`
- **Do NOT** use `element.set(f'{{{R_NS}}}r:id', 'rIdX')` with ElementTree - produces `r:r:id` double prefix
- **Do NOT** construct new slide XML with ElementTree - duplicate xmlns. Use string templates.
- **Do NOT** forget to write new slide XML explicitly when cloning - not in source namelist
- **Do NOT** leave placeholder shapes in cloned slides - remove unwanted `p:sp` elements
- **Do NOT** assume `namelist()` returns files in sorted order - explicitly sort when sequence matters
- **Do NOT** assume text is in a single `<a:r>` element - concatenate all `<a:t>` runs
- **Do NOT** remove grouped shapes from slide's spTree - remove from parent `<p:grpSp>`
- **Do NOT** use incrementing startAt values for buAutoNum - use startAt="1" on all paragraphs
- **Do NOT** rely on XPath predicates in ElementTree - not supported, use iterative search

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| ValueError: Prefix reserved | Using ns\d+ prefix | Use 'p14' or don't register if in source |
| BadZipFile: Truncated header | Read/write same ZIP | Separate input/output paths |
| Repair dialog on open | Missing Content_Types | Add Override for new slide |
| Slide wrong order/blank | rId mismatch | Verify rId in presentation.xml matches .rels |
| Changes not appearing | Wrote wrong path | Check exact path in writestr() |
| Text box invisible | Width in hundreds | Use >=2,500,000 EMUs |
| `r:r:id` in output | ElementTree double-prefix | `.replace('r:r:id=', 'r:id=')` or string template |
| Duplicate xmlns | ElementTree namespace | Use string template |
| New slide missing | Forgot writestr | New slides not in source namelist |
| Numbering wrong | buAutoNum startAt/position | Check each paragraph has buAutoNum |
| Slides processed wrong order | Assumed namelist sorted | Explicitly sort slide paths by number |
| Incomplete text extracted | Text split across runs | Concatenate all `<a:t>` elements in shape |
| Shape removal fails | Shape in group | Find parent `<p:grpSp>` and remove from it |
| Numbering shows "1. 1. 1." | Incrementing startAt values | Use startAt="1" on ALL paragraphs |
| Validation finds empty text | XPath predicate or whitespace issue | Use iterative search, strip whitespace |
| Verifier fails despite local validation | Incomplete validation scope | Run `scripts/validate_pptx.py` for comprehensive checks |

## Known Invariants (by sub-task)

### Museum caption formatting
- Text box width >= 2,500,000 EMUs for single-line titles
- Position values account for parent shape transforms
- Font sz attribute in hundredths of points, not EMUs

### Slide addition
- All 4 files updated atomically
- rId in presentation.xml matches Id in .rels exactly
- Slide ID does not collide with existing IDs

### Slide cloning
- Remove placeholder shapes before adding content
- Explicitly write new slide XML - not in source namelist

### Auto-numbered lists
- Each `<a:p>` with buAutoNum becomes one numbered item
- Numbering continues sequentially across paragraphs
- Use `startAt="1"` to reset numbering

### Sequential slide processing
- `namelist()` returns files in arbitrary order (not sorted)
- When collecting data across slides in order, explicitly sort by slide number
- Use regex to extract slide number for sorting: `int(re.search(r'slide(\d+)', path).group(1))`

### Text extraction
- Text can be split across multiple `<a:r>` runs within one paragraph
- Always concatenate all `<a:t>` text elements, not just the first

### Grouped shapes
- Shapes in `<p:grpSp>` are not direct children of `<p:spTree>`
- Remove from parent group, not from slide root
- Child shape positions are relative to group transform

### Grouped caption cleanup
- Groups named "Caption Group N" contain badge + text shapes
- Preserve badge shapes (route labels, status indicators)
- Modify group position via `p:grpSpPr/a:xfrm` for repositioning
- See `references/grouped-caption-cleanup.md` for full workflow

## References

- `references/pptx-structure.md` - EMU conversions, font widths, string template, buAutoNum types
- `references/grouped-caption-cleanup.md` - Complete workflow for cleaning grouped captions with badges
- `scripts/validate_pptx.py` - Run for comprehensive PPTX validation after modifications
