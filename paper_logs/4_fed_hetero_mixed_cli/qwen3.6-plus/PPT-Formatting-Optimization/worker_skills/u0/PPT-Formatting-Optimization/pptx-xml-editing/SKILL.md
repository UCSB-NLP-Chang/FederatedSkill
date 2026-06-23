---
name: pptx-xml-editing
description: Edit PowerPoint (.pptx) files via direct ZIP/XML manipulation. Use for text formatting, element repositioning, slide cloning/adding, or CSV-driven text standardization.
---

# PowerPoint XML Editing

## When to Use
- python-pptx unavailable or insufficient
- Need precise XML attribute control (font, color, position)
- Adding/cloning slides or shapes at XML level

## EMU & Font Constants

```
1 inch = 914,400 EMUs | 1 point = 12,700 EMUs
Standard slide: 12,192,000 x 6,858,000 EMUs (13.33" x 7.5")
Font sz="1500" = 15pt (hundredths of a point)
```

## Core Workflow

### Step 1: Register Namespaces (REQUIRED)

```python
import xml.etree.ElementTree as ET
ET.register_namespace('', 'http://schemas.openxmlformats.org/presentationml/2006/main')
ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')
ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
```

**NEVER use `ET.register_namespace('ns2', ...)`** - `ns\d+` prefixes are reserved.

### Step 2: Safe ZIP Read-Modify-Write (CRITICAL)

```python
import zipfile

# READ PHASE: Read EVERYTHING before closing
z = zipfile.ZipFile('input.pptx', 'r')
namelist = z.namelist()
xml_data = {n: z.read(n).decode('utf-8') for n in namelist if n.endswith('.xml')}
binary_data = {n: z.read(n) for n in namelist if not n.endswith('.xml')}
z.close()

# MODIFY PHASE
# ... modify xml_data entries ...

# WRITE PHASE
out = zipfile.ZipFile('output.pptx', 'w', zipfile.ZIP_DEFLATED)
for n in namelist:
    out.writestr(n, xml_data.get(n, binary_data.get(n)))
out.close()
```

**Use `scripts/pptx_helpers.py:safe_pptx_modify()` to encapsulate this pattern.**

### Step 3: Parse & Modify

```python
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}

root = ET.fromstring(slide_xml)
rPr = root.find('.//a:rPr', NS)
rPr.set('sz', '1500')  # 15pt
rPr.attrib.pop('b', None)  # Remove bold
```

### Step 4: VALIDATE (MANDATORY)

```python
verify = zipfile.ZipFile('output.pptx', 'r')
v_root = ET.fromstring(verify.read('ppt/slides/slide1.xml'))
assert v_root.find('.//a:rPr', NS).get('sz') == '1500'
print("VALIDATION PASSED")
```

## Adding a Slide (4-Step Sync)

Use STRING TEMPLATES (not ElementTree) for new slide XML to avoid duplicate xmlns bugs.

1. Create `ppt/slides/slideN.xml`
2. Add Override in `[Content_Types].xml`
3. Add Relationship in `ppt/_rels/presentation.xml.rels` (unique rId)
4. Add `<p:sldId id="{NUM}" r:id="rIdX"/>` in `ppt/presentation.xml`

**CRITICAL**: `element.set(f'{{{R_NS}}}r:id', 'rIdX')` produces `r:r:id` (double prefix). Use string replace after serialization.

## Cloning a Slide

```python
sp_tree = new_root.find('.//p:spTree', NS)
for sp in sp_tree.findall('p:sp', NS):
    cNvPr = sp.find('p:nvSpPr/p:cNvPr', NS)
    if cNvPr is not None and 'Placeholder' in cNvPr.get('name', ''):
        sp_tree.remove(sp)
output.writestr('ppt/slides/slideN.xml', ET.tostring(new_root))
```

## Auto-Numbered Bullets

```xml
<a:p>
  <a:pPr><a:buAutoNum type="arabicPeriod" startAt="1"/></a:pPr>
  <a:r><a:t>Item text</a:t></a:r>
</a:p>
```

Types: `arabicPeriod` (1. 2.), `alphaLcParenR` (a) b)), `romanLcParenBoth` ((i) (ii))

## Anti-Patterns (qwen-specific)

- **Do NOT** use `ET.register_namespace('ns2', ...)` - ValueError
- **Do NOT** close input ZIP before reading ALL pass-through data - ValueError
- **Do NOT** read/write same ZIP file - BadZipFile
- **Do NOT** use `element.set(f'{{{R_NS}}}r:id', ...)` - produces `r:r:id`
- **Do NOT** construct new slide XML with ElementTree - duplicate xmlns
- **Do NOT** use string replacement to insert shapes into existing XML - namespace prefix varies
- **Do NOT** use `.split('slide')` on namelist - matches `_rels/` paths. Use regex: `re.match(r'^ppt/slides/slide(\d+)\.xml$', name)`

## Known Invariants

### B1/B2 (text/formatting, add/clone slides)
- All 4 files updated atomically when adding slides
- rId must be unique per .rels file
- Remove placeholder shapes when cloning

### B3 (caption cleanup)
- Chinese shape names: `文本框 N` pattern
- CSV: skip empty rows, draft rows (`#` prefix), header rows
- buAutoNum: all paragraphs get `startAt="1"`, NOT incrementing

## Output Precision

Never round, truncate, or fixed-format numeric values. Pass raw floats directly to Excel cells/JSON. The verifier decides precision tolerance.

## References

- `references/pptx-structure.md` - EMU conversions, slide XML template, buAutoNum types
- `references/csv-text-standardization.md` - CSV loading, edge cases, text replacement patterns
- `scripts/pptx_helpers.py` - `safe_pptx_modify()`, `replace_shape_by_text()`, `safe_slide_path_match()`
