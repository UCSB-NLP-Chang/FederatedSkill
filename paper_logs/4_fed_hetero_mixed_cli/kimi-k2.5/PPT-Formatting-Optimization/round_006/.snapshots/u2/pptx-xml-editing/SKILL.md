---
name: pptx-xml-editing
description: Edit PowerPoint (.pptx) files via direct ZIP/XML manipulation when python-pptx is unavailable or insufficient. Use for formatting text, repositioning elements, cloning/adding slides, grouped shape cleanup, CSV-driven text standardization, or fine-grained OOXML control.
---

# PowerPoint XML Editing

## When to Use
- python-pptx library is unavailable or cannot perform the operation
- You need precise control over XML attributes (font size, color, position, dimensions)
- You need to add/clone/modify slides, shapes, or text styling at the XML level
- You're working with non-standard, grouped, or corrupted PPTX files
- You need to standardize text content using an external mapping (e.g., CSV)

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

Bottom-center positioning formula:
```python
x = (SLIDE_WIDTH - box_width) // 2
y = SLIDE_HEIGHT - box_height - bottom_margin
```

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
import re
z = zipfile.ZipFile('input.pptx', 'r')
namelist = z.namelist()  # Returns full paths like 'ppt/slides/slide1.xml'
```

**CRITICAL: `namelist()` order is arbitrary** - Files are NOT returned in sorted order. When processing slides sequentially, explicitly sort:

```python
slide_files = [n for n in namelist if re.match(r'ppt/slides/slide\d+\.xml$', n)]
slide_files.sort(key=lambda x: int(re.search(r'slide(\d+)', x).group(1)))
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
rPr.attrib.pop('b', None)
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

## Finding Shapes by Text Content

When shape names are unstable or unknown, search by text content:

```python
for sp in root.findall('.//p:sp', NS):
    texts = [t.text for t in sp.findall('.//a:t', NS) if t.text]
    full_text = ''.join(texts)
    if target_text in full_text:
        # Found the shape
        pass
```

## Handling Non-English Shape Names

PowerPoint may use localized names. Common Chinese placeholder names:
- `文本框 N` = "Text Box N"
- Match by pattern: `name.startswith(('文本框', 'Text Box', 'Caption'))`

## CSV-Driven Text Standardization

For tasks requiring text replacement via mapping file:

```python
import csv

def load_caption_map(csv_path):
    """Load raw -> canonical mapping from CSV.
    
    CSV format: raw,canonical
    Handles headers automatically if present.
    """
    mapping = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and not row[0].lower() in ('raw', 'source', 'from'):
                mapping[row[0].strip()] = row[1].strip()
    return mapping

# Apply to slide - check both exact match and containment
for t_elem in root.findall('.//a:t', NS):
    if t_elem.text in caption_map:
        t_elem.text = caption_map[t_elem.text]
```

See `references/csv-text-standardization.md` for patterns.

## Extracting Text (Multi-Run Safe)

Text can be split across multiple `<a:r>` runs. Always concatenate:

```python
# WRONG: Only gets first run
text = shape.find('.//a:t', NS).text

# CORRECT: Join all runs
texts = [t.text for t in shape.findall('.//a:t', NS) if t.text]
full_text = ''.join(texts).strip()
```

## Working with Grouped Shapes

Shapes can be nested inside `<p:grpSp>` (group shape) elements:

```python
for grp in root.findall('.//p:grpSp', NS):
    cNvPr = grp.find('p:nvGrpSpPr/p:cNvPr', NS)
    if cNvPr is not None and 'Caption Group' in cNvPr.get('name', ''):
        for sp in grp.findall('p:sp', NS):
            # Process shapes within group
            pass
```

See `references/grouped-caption-cleanup.md` for complete grouped caption workflow.

## Shape Targeting & Batch Formatting

When cleaning up or reformatting existing slides:
1. **Identify shapes** by `p:cNvPr name` attribute or by searching text content.
2. **Modify multiple attributes** in one pass: font (`a:latin typeface`), size (`a:rPr sz`), color (`a:solidFill/a:srgbClr val`), bold/italic (`a:rPr b/i`), alignment (`a:pPr algn`).
3. **Adjust geometry** via `a:xfrm`: `a:off` (x, y) and `a:ext` (cx, cy).
4. **Remove unwanted attributes** safely: `rPr.attrib.pop('b', None)`.
5. **Validate** by re-reading the output ZIP and asserting key attributes.

## Repositioning Text Boxes

For bottom-center captions:

```python
SLIDE_WIDTH = 12192000
SLIDE_HEIGHT = 6858000
MARGIN = 200000  # ~0.22 inch

def bottom_center_position(box_width, box_height):
    x = (SLIDE_WIDTH - box_width) // 2
    y = SLIDE_HEIGHT - box_height - MARGIN
    return x, y

# Update shape position
spPr = shape.find('p:spPr', NS)
xfrm = spPr.find('a:xfrm', NS)
off = xfrm.find('a:off', NS)
ext = xfrm.find('a:ext', NS)

off.set('x', str(x))
off.set('y', str(y))
ext.set('cx', str(box_width))
ext.set('cy', str(box_height))
```

## Replacing or Inserting Shapes via DOM (NOT String Replacement)

**Do NOT use string replacement** to insert shapes into existing slide XML. ElementTree serializes with varying namespace prefixes (e.g., `</spTree>` vs `</p:spTree>`), making string matching brittle.

**Use ElementTree DOM manipulation instead:**

```python
# Parse existing slide
root = ET.fromstring(slide_xml)
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}

# Find spTree
sp_tree = root.find('.//p:spTree', NS)

# Create new shape element
new_sp = ET.SubElement(sp_tree, '{http://schemas.openxmlformats.org/presentationml/2006/main}sp')
# ... populate new_sp with nvSpPr, spPr, txBody ...

# Or remove existing shape and insert replacement
for sp in sp_tree.findall('p:sp', NS):
    texts = [t.text for t in sp.findall('.//a:t', NS) if t.text]
    if 'TargetText' in ''.join(texts):
        sp_tree.remove(sp)
        break

sp_tree.append(new_sp)
```

See `scripts/pptx_helpers.py` for `replace_shape_by_text()` helper.

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

**PREFER STRING TEMPLATES over ElementTree** for creating new slide XML. ElementTree produces duplicate xmlns and `r:r:id` double-prefix bugs.

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
- **Do NOT** use incrementing startAt values for buAutoNum - use startAt="1" on all paragraphs
- **Do NOT** assume `namelist()` returns files in sorted order - explicitly sort when sequence matters
- **Do NOT** assume text is in a single `<a:r>` element - concatenate all `<a:t>` runs
- **Do NOT** remove grouped shapes from slide's spTree - remove from parent `<p:grpSp>`
- **Do NOT** modify caption text without checking both exact match AND containment - CSV mappings may not cover all variations
- **Do NOT** use `.split('slide')` on namelist entries to extract slide numbers - matches `_rels/slideX.xml.rels`. Use `re.match(r'^ppt/slides/slide(\d+)\.xml$', name)`
- **Do NOT** use string replacement to insert shapes into existing slide XML - namespace prefixes vary between `</p:spTree>` and `</spTree>`. Use ElementTree DOM manipulation (`sp_tree.append()`)

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
| Numbering shows "1. 1. 1." | Incrementing startAt values | Use startAt="1" on ALL paragraphs |
| Slides processed wrong order | Assumed namelist sorted | Explicitly sort slide paths by number |
| Incomplete text extracted | Text split across runs | Concatenate all `<a:t>` elements |
| Shape removal fails | Shape in group | Find parent `<p:grpSp>` and remove from it |
| Caption not found | Non-English name | Search by `文本框` pattern or text content |
| CSV mapping missed | Partial match | Check `if text in mapping` not just `==` |
| Shape not found after insertion | String replacement failed due to namespace prefix variation | Use ElementTree DOM manipulation (`sp_tree.append()`) instead of string replacement |
| ValueError on slide number extraction | `_rels/` paths matched by `.split('slide')` | Use `re.match(r'^ppt/slides/slide(\d+)\.xml$', name)` |

## Pre-Flight Checklist (CSV Standardization Tasks)

Before declaring task complete:
- [ ] All captions from CSV appear in output (no missed mappings)
- [ ] No duplicate entries in numbered lists (use `seen` list to track)
- [ ] First-appearance order preserved for Evidence Log slides
- [ ] Position values verified: bottom-center calculated with correct EMUs
- [ ] Font attributes verified: size (hundredths of point), color (no #), bold removed
- [ ] Original timestamps/content preserved in non-target shapes

## Known Invariants (by sub-task)

### Museum caption formatting
- Text box width >= 2,500,000 EMUs for single-line titles
- Position values account for parent shape transforms
- Font sz attribute in hundredths of points, not EMUs

### Grouped caption cleanup
- Groups named "Caption Group N" contain badge + text shapes
- Preserve badge shapes (route labels, status indicators)
- Modify group position via `p:grpSpPr/a:xfrm` for repositioning
- See `references/grouped-caption-cleanup.md` for full workflow

### CSV-driven text standardization
- Load mapping with `csv.reader`, handle headers
- Check containment `in` not just equality `==` for flexible matching
- Track unique items in list (not set) to preserve order
- See `references/csv-text-standardization.md` for patterns

### Slide addition
- All 4 files updated atomically
- rId in presentation.xml matches Id in .rels exactly
- Slide ID does not collide with existing IDs

### Slide cloning
- Remove placeholder shapes before adding content
- Explicitly write new slide XML - not in source namelist

### Auto-numbered lists
- Each `<a:p>` with buAutoNum becomes one numbered item
- Use `startAt="1"` on ALL paragraphs (PowerPoint continues sequence automatically)
- Do NOT use incrementing startAt values

### Sequential slide processing
- `namelist()` returns files in arbitrary order (not sorted)
- Explicitly sort by slide number when sequence matters

### Shape replacement
- Use ElementTree DOM manipulation, not string replacement
- Validate by re-reading output and checking shape text content

## References

- `references/pptx-structure.md` - EMU conversions, font widths, string template, buAutoNum types
- `references/grouped-caption-cleanup.md` - Complete workflow for cleaning grouped captions with badges
- `references/csv-text-standardization.md` - Patterns for CSV-driven text replacement tasks
- `scripts/validate_pptx.py` - Run for comprehensive PPTX validation after modifications
- `scripts/pptx_helpers.py` - `replace_shape_by_text()`, `safe_slide_path_match()`, and other helpers
