---
name: pptx-xml-editing
description: Edit PowerPoint (.pptx) files via direct ZIP/XML manipulation. Use for formatting, repositioning, adding/cloning slides, CSV text standardization.
---

# PowerPoint XML Editing

## When to Use
- python-pptx unavailable or insufficient
- Need precise XML control (font, color, position, dimensions)
- Add/clone slides, shapes, text styling at XML level
- CSV-driven text standardization

## EMU Constants (MEMORIZE)
```
1 inch = 914,400 EMUs | 1 point = 12,700 EMUs
Slide: 12,192,000 x 6,858,000 EMUs (13.33" x 7.5")
Font sz="1500" = 15pt (hundredths of a point)
Bottom-center: x = (SLIDE_WIDTH - box_width) // 2
```

## Core Workflow

### 1. Register Namespaces (REQUIRED FIRST)
```python
import xml.etree.ElementTree as ET
ET.register_namespace('', 'http://schemas.openxmlformats.org/presentationml/2006/main')
ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')
ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
```
**NEVER use 'ns2', 'ns3' prefixes** - ValueError. If source has them, don't re-register.

### 2. SAFE ZIP Pattern (CRITICAL)
**Never close ZIP before reading ALL data.**
```python
import zipfile, re
z = zipfile.ZipFile('input.pptx', 'r')
namelist = z.namelist()
xml_data = {n: z.read(n).decode('utf-8') for n in namelist if n.endswith('.xml')}
binary_data = {n: z.read(n) for n in namelist if not n.endswith('.xml')}
z.close()
# Modify xml_data...
out = zipfile.ZipFile('output.pptx', 'w', zipfile.ZIP_DEFLATED)
for n in namelist:
    out.writestr(n, xml_data.get(n) or binary_data.get(n))
out.close()
```
**namelist() order is arbitrary** - sort slides: `re.match(r'ppt/slides/slide(\d+)\.xml$', n)`

### 3. Parse & Modify
```python
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
root = ET.fromstring(slide_xml)
rPr = root.find('.//a:rPr', NS)
rPr.set('sz', '1500')  # 15pt
```

### 4. VALIDATE (MANDATORY)
```python
verify = zipfile.ZipFile('output.pptx', 'r')
v_root = ET.fromstring(verify.read('ppt/slides/slide1.xml').decode())
assert v_root.find('.//a:rPr', NS).get('sz') == '1500'
print("PASS")
```
**If ANY check fails → overall FAIL.** No contradictory output.

## Key Patterns

### Find Shape by Text
```python
for sp in root.findall('.//p:sp', NS):
    full_text = ''.join(t.text for t in sp.findall('.//a:t', NS) if t.text)
    if target_text in full_text: pass
```
**Chinese names**: match `文本框 N` pattern.

### CSV Text Standardization
```python
import csv
caption_map = {}
with open('mapping.csv') as f:
    for row in csv.reader(f):
        if len(row) >= 2 and row[0].strip() and row[1].strip():
            caption_map[row[0].strip()] = row[1].strip()
for t in root.findall('.//a:t', NS):
    if t.text in caption_map: t.text = caption_map[t.text]
```

### buAutoNum (Auto-Numbered Lists)
```xml
<a:p><a:pPr><a:buAutoNum type="arabicPeriod" startAt="1"/></a:pPr><a:r><a:t>Item</a:t></a:r></a:p>
```
**CRITICAL: startAt="1" on EVERY paragraph.** PowerPoint auto-increments.

### Add New Slide (4-Step Sync)
Use **string templates** (not ElementTree) for slide XML to avoid duplicate xmlns.
1. Create `ppt/slides/slideN.xml`
2. Add to `[Content_Types].xml`: `<Override PartName="/ppt/slides/slideN.xml" ContentType="...slide+xml"/>`
3. Add to `ppt/_rels/presentation.xml.rels`: `<Relationship Id="rIdX" Target="slides/slideN.xml"/>`
4. Add to `ppt/presentation.xml`: `<p:sldId id="NUM" r:id="rIdX"/>`

**New slides NOT in namelist** - write explicitly: `out.writestr('ppt/slides/slide7.xml', xml)`

### Shape Insertion (DOM, NOT String Replacement)
```python
sp_tree = root.find('.//p:spTree', NS)
new_sp = ET.SubElement(sp_tree, '{http://schemas.openxmlformats.org/presentationml/2006/main}sp')
```
Namespace prefixes vary (`</spTree>` vs `</p:spTree>`) - string replacement fails.

## Anti-Patterns

- **Do NOT** use `ns\d+` prefixes - ValueError
- **Do NOT** close ZIP before reading ALL data - ValueError: ZIP archive already closed
- **Do NOT** read/write same ZIP - BadZipFile
- **Do NOT** use `element.set(f'{{{R_NS}}}r:id', ...)` - produces `r:r:id` double prefix
- **Do NOT** use ElementTree for new slide XML - duplicate xmlns. Use string templates.
- **Do NOT** use `.split('slide')` - matches `_rels/`. Use regex.
- **Do NOT** increment buAutoNum startAt - use `startAt="1"` on ALL paragraphs
- **Do NOT** assume text in single `<a:r>` - concatenate all runs
- **Do NOT** remove grouped shapes from spTree - remove from parent `<p:grpSp>`
- **Do NOT** output contradictory validation - if any fail, overall FAIL

## Text Formatting Reference
| Attribute | Element | Values |
|-----------|---------|--------|
| sz | a:rPr | 1500=15pt (hundredths) |
| b/i | a:rPr | 0/1 |
| val | a:srgbClr | 6F6C64 (no #) |
| algn | a:pPr | l/r/ctr/just |

## References
- `scripts/pptx_helpers.py` - `safe_pptx_modify()`, `replace_shape_by_text()`
- `references/csv-text-standardization.md` - CSV edge cases
- `scripts/validate_pptx.py` - Comprehensive validation
