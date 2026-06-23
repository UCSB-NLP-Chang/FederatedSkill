---
name: pptx-xml-editing
description: Edit PowerPoint (.pptx) files via direct ZIP/XML manipulation when python-pptx is unavailable. Use for formatting text, repositioning elements, cloning/adding slides, CSV-driven text standardization, or fine-grained OOXML control.
---

# PowerPoint XML Editing

## When to Use
- python-pptx is unavailable or cannot perform the operation
- Precise control over XML attributes (font size, color, position, dimensions)
- Add/clone/modify slides, shapes, or text styling at XML level
- Non-standard, grouped, or corrupted PPTX files
- CSV-driven text standardization

## EMU & Font Constants

```
1 inch = 914,400 EMUs | 1 point = 12,700 EMUs
Standard slide: 12,192,000 x 6,858,000 EMUs
Font size: sz="1500" = 15pt (hundredths of a point)
Bottom-center: x = (SLIDE_WIDTH - box_width) // 2
```

## Core Workflow (4 Steps)

### Step 1: Register Namespaces (REQUIRED)

```python
ET.register_namespace('', 'http://schemas.openxmlformats.org/presentationml/2006/main')
ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')
ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
```
**NEVER use `ns2`, `ns3` prefixes** - reserved, raises ValueError.

### Step 2: SAFE ZIP Read-Modify-Write

**Read ALL data before closing input ZIP:**
```python
z = zipfile.ZipFile('input.pptx', 'r')
namelist = z.namelist()
xml_data = {n: z.read(n).decode('utf-8') for n in namelist if n.endswith('.xml')}
binary_data = {n: z.read(n) for n in namelist if not n.endswith('.xml')}
z.close()
# Modify xml_data in-memory...
out = zipfile.ZipFile('output.pptx', 'w')
for n in namelist: out.writestr(n, xml_data.get(n) or binary_data[n])
out.close()
```
See `scripts/pptx_helpers.py` for `safe_pptx_modify()` helper.

### Step 3: Parse & Modify XML

```python
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
root = ET.fromstring(slide_xml)
rPr = root.find('.//a:rPr', NS)
rPr.set('sz', '1500')  # 15pt font
rPr.attrib.pop('b', None)  # Remove bold
```

### Step 4: VALIDATE (MANDATORY)

```python
verify = zipfile.ZipFile('output.pptx', 'r')
verify_rPr = ET.fromstring(verify.read('ppt/slides/slide1.xml')).find('.//a:rPr', NS)
assert verify_rPr.get('sz') == '1500', f"Font wrong: {verify_rPr.get('sz')}"
```

## Key Operations

### Finding Shapes by Text/Name
```python
for sp in root.findall('.//p:sp', NS):
    full_text = ''.join(t.text for t in sp.findall('.//a:t', NS) if t.text)
    if target_text in full_text: # Found
```
**Chinese names**: Match `文本框 N` or `Caption` in `cNvPr name`.

### Shape Replacement (DOM, NOT String)
```python
sp_tree = root.find('.//p:spTree', NS)
new_sp = ET.SubElement(sp_tree, '{http://schemas.openxmlformats.org/presentationml/2006/main}sp')
```

### Adding New Slide (4-File Sync)
1. Create `ppt/slides/slide{N}.xml` (use string template, not ElementTree)
2. Register in `[Content_Types].xml`
3. Add `<Relationship Id="rId{X}" Target="slides/slideN.xml"/>` in `ppt/_rels/presentation.xml.rels`
4. Add `<p:sldId id="{NUM}" r:id="rId{X}"/>` in `ppt/presentation.xml`

**New slides NOT in source namelist** - write explicitly.

### buAutoNum (Auto-Numbered Bullets)
```xml
<a:p><a:pPr><a:buAutoNum type="arabicPeriod" startAt="1"/></a:pPr>
  <a:r><a:t>Item text</a:t></a:r></a:p>
```
| type | Output |
|------|--------|
| arabicPeriod | 1. 2. 3. |
| alphaLcParenR | a) b) c) |
**Use `startAt="1"` on ALL paragraphs** - do NOT increment.

### Text Formatting Attributes

| Attr | Element | Example | Notes |
|------|---------|---------|-------|
| sz | a:rPr | 1500 = 15pt | Hundredths of a point |
| b | a:rPr | 0/1 | Bold |
| val | a:srgbClr | 6F6C64 | RGB hex without # |
| algn | a:pPr | l/r/ctr/just | Alignment |

## Anti-Patterns (CRITICAL)

- **ns2/ns3 prefixes** → ValueError; use 'p14' or don't register
- **Read/write same ZIP** → BadZipFile; separate input/output paths
- **Close ZIP before reading all data** → ValueError; read ALL before close
- **ElementTree for new slides** → duplicate xmlns; use string templates
- **String replacement for shapes** → namespace prefix variation; use DOM
- **`element.set(f'{{{R_NS}}}r:id', ...)`** → `r:r:id` double prefix
- **`.split('slide')` for paths** → matches `_rels/`; use regex
- **Incrementing buAutoNum startAt** → use `startAt="1"` on all
- **Skip validation** → verifier fails

## Known Invariants (by sub-task)

### CSV-driven text standardization
- Filter empty/draft/comment rows from CSV
- Check containment `in` not just equality `==`
- Track unique items in list (preserves order)

### Grouped caption cleanup
- Groups named "Caption Group N" contain badge + text
- Preserve badge shapes; see `references/grouped-caption-cleanup.md`

### Auto-numbered lists
- Each `<a:p>` with buAutoNum = one numbered item
- Validation must FAIL on any error (no contradictory pass/fail)

## References

- `references/pptx-structure.md` - EMU conversions, string template, buAutoNum types
- `references/grouped-caption-cleanup.md` - Grouped caption workflow
- `references/csv-text-standardization.md` - CSV mapping patterns
- `scripts/pptx_helpers.py` - `safe_pptx_modify()`, `replace_shape_by_text()`
- `scripts/validate_pptx.py` - Comprehensive validation
