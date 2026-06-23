---
name: pptx-xml-editing
description: Edit PowerPoint (.pptx) files via direct ZIP/XML manipulation when python-pptx is unavailable or insufficient. Use for formatting text, repositioning elements, cloning/adding slides, CSV-driven text standardization, or fine-grained OOXML control.
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

Bottom-center positioning: `x = (SLIDE_WIDTH - box_width) // 2`

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

### Step 2: SAFE ZIP Read-Modify-Write (CRITICAL)

**NEVER close input ZIP before reading ALL data.** Common failure: close `z` early, then try to read pass-through files → ValueError.

```python
import zipfile, re

# READ PHASE: Read EVERYTHING before closing
z = zipfile.ZipFile('input.pptx', 'r')
namelist = z.namelist()

# Read all XML you'll modify
xml_data = {n: z.read(n).decode('utf-8') for n in namelist if n.endswith('.xml')}

# Read ALL binary pass-through BEFORE closing
binary_data = {n: z.read(n) for n in namelist if not n.endswith('.xml')}
z.close()

# MODIFY PHASE: Work on in-memory strings
# ... modify xml_data entries ...

# WRITE PHASE
out = zipfile.ZipFile('output.pptx', 'w', zipfile.ZIP_DEFLATED)
for n in namelist:
    if n in xml_data:
        out.writestr(n, xml_data[n])
    else:
        out.writestr(n, binary_data[n])
out.close()
```

**CRITICAL: `namelist()` order is arbitrary** - Use regex for slide matching:
```python
slide_files = [n for n in namelist if re.match(r'ppt/slides/slide\d+\.xml$', n)]
slide_files.sort(key=lambda x: int(re.search(r'slide(\d+)', x).group(1)))
```

See `scripts/pptx_helpers.py` for `safe_pptx_modify()` helper that encapsulates this pattern.

### Step 3: Parse & Modify XML

```python
root = ET.fromstring(slide_xml)
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

rPr = root.find('.//a:rPr', NS)
rPr.set('sz', '1500')  # 15pt font
rPr.attrib.pop('b', None)  # Remove bold safely
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

```python
verify = zipfile.ZipFile('output.pptx', 'r')
verify_xml = verify.read('ppt/slides/slide1.xml').decode('utf-8')
verify_root = ET.fromstring(verify_xml)
verify_rPr = verify_root.find('.//a:rPr', NS)
assert verify_rPr.get('sz') == '1500', f"Font size wrong: {verify_rPr.get('sz')}"
print("VALIDATION PASSED")
```

**Use the validation script for comprehensive checks:**
```python
# Run scripts/validate_pptx.py for full structural validation
python3 scripts/validate_pptx.py output.pptx --slides 2-6 --slide7
```

**Validation must be consistent**: If any check fails, the overall result must be FAIL. Contradictory output (error messages followed by "all passed") indicates a bug in validation logic.

## Finding Shapes by Text Content

When shape names are unstable or unknown:
```python
for sp in root.findall('.//p:sp', NS):
    texts = [t.text for t in sp.findall('.//a:t', NS) if t.text]
    full_text = ''.join(texts)
    if target_text in full_text:
        # Found the shape
        pass
```

**Chinese shape names**: PowerPoint may use localized names like `文本框 N` ("Text Box N"). Match by pattern: `name.startswith(('文本框', 'Text Box', 'Caption'))`

## CSV-Driven Text Standardization

```python
import csv

# Load mapping: raw -> canonical
caption_map = {}
with open('mapping.csv', 'r') as f:
    reader = csv.reader(f)
    next(reader)  # Skip header if present
    for row in reader:
        if len(row) >= 2:
            caption_map[row[0].strip()] = row[1].strip()

# Apply - check both exact match and containment
for t_elem in root.findall('.//a:t', NS):
    if t_elem.text in caption_map:
        t_elem.text = caption_map[t_elem.text]
```

See `references/csv-text-standardization.md` for full patterns including handling empty rows, draft rows, and comment rows.

## Extracting Text (Multi-Run Safe)

Text can be split across multiple `<a:r>` runs. Always concatenate:
```python
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

See `references/grouped-caption-cleanup.md` for complete workflow.

## Replacing or Inserting Shapes via DOM (NOT String Replacement)

**Do NOT use string replacement** to insert shapes. ElementTree serializes with varying namespace prefixes (e.g., `</spTree>` vs `</p:spTree>`).

```python
sp_tree = root.find('.//p:spTree', NS)
new_sp = ET.SubElement(sp_tree, '{http://schemas.openxmlformats.org/presentationml/2006/main}sp')
# ... populate new_sp ...
```

See `scripts/pptx_helpers.py` for `replace_shape_by_text()` helper.

## Auto-Numbered Bullets (buAutoNum)

```xml
<a:p>
  <a:pPr><a:buAutoNum type="arabicPeriod" startAt="1"/></a:pPr>
  <a:r><a:t>First item</a:t></a:r>
</a:p>
```

| type | Output |
|------|--------|
| arabicPeriod | 1. 2. 3. |
| alphaLcParenR | a) b) c) |
| romanLcParenBoth | (i) (ii) |

**CRITICAL: startAt Rule** - Use `startAt="1"` on EVERY paragraph. Do NOT increment. PowerPoint continues numbering automatically.

## Text Formatting Attributes

| Attribute | Element | Values | Notes |
|-----------|---------|--------|-------|
| sz | a:rPr | 1500 = 15pt | Hundredths of a point |
| b | a:rPr | 0/1 | Bold |
| i | a:rPr | 0/1 | Italic |
| val | a:srgbClr | 6F6C64 | RGB hex without # |
| algn | a:pPr | l/r/ctr/just | Alignment |

## Adding a New Slide (4-Step Sync)

**PREFER STRING TEMPLATES over ElementTree** for new slide XML to avoid duplicate xmlns bugs.

Update ALL FOUR files atomically:

1. Create `ppt/slides/slide{N}.xml` with valid structure
2. Register in `[Content_Types].xml`:
   ```xml
   <Override PartName="/ppt/slides/slideN.xml"
             ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
   ```
3. Add relationship in `ppt/_rels/presentation.xml.rels`:
   ```xml
   <Relationship Id="rId{X}" Type="...slide" Target="slides/slideN.xml"/>
   ```
4. Reference in `ppt/presentation.xml`:
   ```xml
   <p:sldId id="{NUM}" r:id="rId{X}"/>
   ```

**CRITICAL**: New slides are NOT in source namelist. Write explicitly: `output.writestr('ppt/slides/slide7.xml', slide7_xml)`

## Anti-Patterns

- **Do NOT** use `ET.register_namespace('ns2', ...)` - ValueError
- **Do NOT** guess EMU values - use constants above
- **Do NOT** skip validation - verifier will fail
- **Do NOT** reuse rId values - must be unique per .rels file
- **Do NOT** read/write same ZIP file - BadZipFile
- **Do NOT** close input ZIP before reading ALL pass-through data - ValueError: ZIP archive already closed
- **Do NOT** use `.split('slide')` for slide paths - matches `_rels/`. Use regex `re.match(r'^ppt/slides/slide(\d+)\.xml$', name)`
- **Do NOT** use `element.set(f'{{{R_NS}}}r:id', ...)` - produces `r:r:id` double prefix
- **Do NOT** construct new slide XML with ElementTree - duplicate xmlns. Use string templates.
- **Do NOT** use string replacement for shape insertion - namespace prefixes vary. Use DOM manipulation.
- **Do NOT** use incrementing startAt for buAutoNum - use `startAt="1"` on all paragraphs
- **Do NOT** assume text is in a single `<a:r>` - concatenate all runs
- **Do NOT** remove grouped shapes from slide's spTree - remove from parent `<p:grpSp>`
- **Do NOT** output contradictory validation results - if any check fails, overall result must be FAIL

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| ValueError: Prefix reserved | Using ns\d+ prefix | Use 'p14' or don't register if in source |
| BadZipFile: Truncated header | Read/write same ZIP | Separate input/output paths |
| ValueError: ZIP archive already closed | Closed input ZIP before reading all data | Read ALL data (XML + binary) before z.close() |
| Repair dialog on open | Missing Content_Types | Add Override for new slide |
| Slide wrong order/blank | rId mismatch | Verify rId matches between files |
| `r:r:id` in output | ElementTree double-prefix | `.replace('r:r:id=', 'r:id=')` or string template |
| Shape not found after insertion | String replacement failed | Use ElementTree DOM manipulation |
| ValueError on slide number extraction | `_rels/` paths matched | Use regex `re.match(r'^ppt/slides/slide(\d+)\.xml$', name)` |
| Numbering shows "1. 1. 1." | Incrementing startAt | Use `startAt="1"` on ALL paragraphs |
| Caption not found | Non-English name | Search by `文本框` pattern or text content |
| Validation shows pass after errors | Bug in validation logic | Fix validation to fail on any error |

## Known Invariants (by sub-task)

### Museum caption formatting
- Text box width >= 2,500,000 EMUs for single-line titles
- Position values account for parent shape transforms

### CSV-driven text standardization
- Load mapping with `csv.reader`, handle headers
- Check containment `in` not just equality `==` for flexible matching
- Track unique items in list (not set) to preserve first-appearance order
- Filter empty rows, draft rows, and comment rows from CSV

### Grouped caption cleanup
- Groups named "Caption Group N" contain badge + text shapes
- Preserve badge shapes (route labels, status indicators)
- See `references/grouped-caption-cleanup.md` for workflow

### Auto-numbered lists
- Use `startAt="1"` on ALL paragraphs (PowerPoint continues sequence)
- Do NOT increment startAt values

## References

- `references/pptx-structure.md` - EMU conversions, font widths, string template, buAutoNum types
- `references/grouped-caption-cleanup.md` - Complete workflow for cleaning grouped captions
- `references/csv-text-standardization.md` - Patterns for CSV-driven text replacement including edge cases
- `scripts/validate_pptx.py` - Run for comprehensive PPTX validation
- `scripts/pptx_helpers.py` - Importable utilities (`replace_shape_by_text`, `safe_slide_path_match`, etc.)
