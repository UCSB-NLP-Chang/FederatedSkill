# PPTX Structure Reference

## ZIP Layout

```
.pptx (ZIP)
├── [Content_Types].xml
├── _rels/
├── ppt/
│   ├── presentation.xml          # Slide order & rId references
│   ├── _rels/presentation.xml.rels # rId -> slide/media mappings
│   ├── slides/
│   │   ├── slide1.xml
│   │   └── _rels/slide1.xml.rels
│   ├── slideMasters/
│   └── theme/
```

## Slide XML Structure

```xml
<p:sld xmlns:p="..." xmlns:a="..." xmlns:r="...">
  <p:cSld>
    <p:spTree>
      <p:sp>  <!-- Shape -->
        <p:nvSpPr>
          <p:cNvPr id="N" name="..."/>
          <p:cNvSpPr txBox="1"/>  <!-- Text box flag -->
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm>
            <a:off x="X" y="Y"/>  <!-- Position in EMUs -->
            <a:ext cx="W" cy="H"/>  <!-- Size in EMUs -->
          </a:xfrm>
        </p:spPr>
        <p:txBody>  <!-- Text content -->
          <a:p>
            <a:pPr algn="ctr"/>  <!-- Alignment: l/r/ctr/just -->
            <a:r>
              <a:rPr lang="en-US" sz="1500" b="0">
                <a:solidFill>
                  <a:srgbClr val="6F6C64"/>
                </a:solidFill>
                <a:latin typeface="Arial"/>
              </a:rPr>
              <a:t>Text content here</a:t>
            </a:r>
          </a:p>
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>
```

## EMU Conversions

- 1 inch = 914,400 EMUs
- 1 cm = 360,000 EMUs
- 1 point = 12,700 EMUs
- 15pt font size = sz="1500" (hundredths of a point)
- Standard slide: 12,192,000 x 6,858,000 EMUs (13.33" x 7.5")

## Arial Font Width Estimates (at 15pt, in EMUs)

Use these for `cx` (width) calculations to ensure single-line text fit:

- Narrow (`i, l, I, j, ., ;, :, !, '`): ~50,000
- Medium (`f, t, s, r, -, (, ), [, ]`): ~70,000
- Average (`a, c, e, g, m, n, o, p, q, u, v, x, z`): ~85,000
- Wide (`A-Z, 0-9`): ~100,000
- Extra Wide (`M, Q, O, &, %, $, #, @, ~, +, =, <, >`): ~120,000
- Space: ~40,000

Add padding: `total_width + 2 * 91440` (for left/right insets).

## Text Styling Attributes

| Attribute | Element | Values | Notes |
|-----------|---------|--------|-------|
| sz | a:rPr | 1500 = 15pt | In hundredths of a point |
| b | a:rPr | 0/1 | Bold on/off |
| i | a:rPr | 0/1 | Italic on/off |
| u | a:rPr | none/sng/dbl | Underline |
| typeface | a:latin | Font name | Latin fonts |
| val | a:srgbClr | 6-char hex | RGB color without # |
| algn | a:pPr | l/r/ctr/just | Text alignment |

## Auto-Numbered Bullets (buAutoNum)

Bullet numbering is controlled by `buAutoNum` in paragraph properties:

```xml
<a:p>
  <a:pPr>
    <a:buFont typeface="Arial"/>
    <a:buAutoNum type="arabicPeriod" startAt="1"/>
  </a:pPr>
  <a:r>
    <a:t>Bullet text</a:t>
  </a:r>
</a:p>
```

### buAutoNum Types

| Type | Example | Use Case |
|------|---------|----------|
| arabicPeriod | 1. 2. 3. | Standard numbered lists |
| arabicParenR | 1) 2) 3) | Alternative numbering |
| romanLcParenBoth | (i) (ii) (iii) | Lowercase roman |
| alphaLcPeriod | a. b. c. | Alphabetic |
| romanUcParenBoth | (I) (II) (III) | Uppercase roman |

### Critical Implementation Notes

1. **Each paragraph is one item**: Every `<a:p>` with `buAutoNum` becomes one numbered entry
2. **Sequential numbering**: Numbering continues across paragraphs in the same text body
3. **startAt attribute**: Use `startAt="1"` to begin numbering at 1. If omitted, PowerPoint may infer based on position
4. **No explicit number**: The number is generated automatically; don't put "1." in the text content

### Removing Numbering

To convert numbered to unnumbered, remove `buAutoNum` from `a:pPr`:

```python
# Remove buAutoNum element
pPr = paragraph.find('a:pPr', NS)
buAutoNum = pPr.find('a:buAutoNum', NS)
if buAutoNum is not None:
    pPr.remove(buAutoNum)
```

## Slide Cloning Checklist

When using an existing slide as a template for a new slide:

### Pre-Clone: Analyze Template
```python
# List all shapes in template to identify placeholders
template_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
root = ET.fromstring(template_xml)
for sp in root.findall('.//p:sp', NS):
    cNvPr = sp.find('p:nvSpPr/p:cNvPr', NS)
    if cNvPr is not None:
        print(f"Shape: {cNvPr.get('name')} (id={cNvPr.get('id')})")
```

### During Clone: Remove Unwanted Shapes
```python
sp_tree = new_root.find('.//p:spTree', NS)
shapes_to_remove = []

for sp in sp_tree.findall('p:sp', NS):
    cNvPr = sp.find('p:nvSpPr/p:cNvPr', NS)
    if cNvPr is not None:
        name = cNvPr.get('name', '')
        # Remove placeholders not needed in new slide
        if 'Placeholder' in name or name.startswith('Content'):
            shapes_to_remove.append(sp)

for sp in shapes_to_remove:
    sp_tree.remove(sp)
```

### Post-Clone: Validation
- [ ] Only intended shapes remain in new slide
- [ ] Shape IDs don't collide with existing slides (PowerPoint handles this per-slide)
- [ ] Text content is new, not template placeholder text
- [ ] Position and size attributes preserved/modified as intended

## Adding a New Slide (Step-by-Step XML)

1. Create `ppt/slides/slideN.xml` with proper structure
2. Create `ppt/slides/_rels/slideN.xml.rels` for relationships (copy from template)
3. Add entry in `ppt/_rels/presentation.xml.rels`:
   ```xml
   <Relationship Id="rIdN" Type="...slide" Target="slides/slideN.xml"/>
   ```
4. Add entry in `ppt/presentation.xml`:
   ```xml
   <p:sldId id="N" r:id="rIdN"/>
   ```
5. Add entry in `[Content_Types].xml`:
   ```xml
   <Override PartName="/ppt/slides/slideN.xml"
             ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
   ```

### Finding Next Available IDs

```python
# Find max rId in presentation.xml.rels
import re
rels_content = z.read('ppt/_rels/presentation.xml.rels').decode('utf-8')
rids = [int(m) for m in re.findall(r'Id="rId(\d+)"', rels_content)]
new_rid = max(rids) + 1  # Use rId{new_rid}

# Find max slide ID in presentation.xml
pres_content = z.read('ppt/presentation.xml').decode('utf-8')
ids = [int(m) for m in re.findall(r'<p:sldId[^>]+id="(\d+)"', pres_content)]
new_slide_id = max(ids) + 1  # Use id="{new_slide_id}"
```

## Position Reference

For bottom-center positioning:
- x = (slide_width - box_width) / 2
- y = slide_height - box_height - margin

Example: 10,000,000 wide box at bottom with 100,000 margin:
- x = (12192000 - 10000000) / 2 = 1096000
- y = 6858000 - 400000 - 200000 = 6258000

## Relationship Handling

When adding a new slide (`slide7.xml`):
1. Add `<p:sldId id="263" r:id="rId257"/>` to `ppt/presentation.xml`.
2. Add `<Relationship Id="rId257" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide7.xml"/>` to `ppt/_rels/presentation.xml.rels` before `</Relationships>`.
3. Ensure `rId` is unique across the rels file.

## Common Text Box Positioning

### Bottom Center Caption Box

For a caption box at the bottom center of a 16:9 slide:
- Width: 8,000,000 EMUs (~8.75 inches)
- Height: 400,000-600,000 EMUs depending on text size
- X position: (12,192,000 - 8,000,000) / 2 = 2,096,000 EMUs
- Y position: 6,858,000 - height - margin (e.g., 5,852,160 for 400,000 height + 600,000 margin)

## Shape Identification by Name

Common placeholder shape names in cloned slides:
- `Title 1` - Slide title text box
- `Content Placeholder 2` - Main content area
- `Text Placeholder 3` - Additional text box
- `Date Placeholder 4` - Date field
- `Footer Placeholder 5` - Footer text
- `Slide Number Placeholder 6` - Page number
- `文本框 N` - Chinese "Text Box N" (generic text boxes)

To find shapes when names are unstable, search by text content or iterate and check `cNvPr` attributes.

## Creating New Slides via String Template

**Use string templates instead of ElementTree** to avoid duplicate namespace declarations and `r:r:id` double-prefix bugs.

### Complete Slide Template

```python
def create_slide_xml(title_text, bullet_items, auto_num_type="arabicPeriod"):
    """Create a new slide XML string using template approach.

    Args:
        title_text: Title text for the slide
        bullet_items: List of strings for bullet points
        auto_num_type: Type for auto-numbering (arabicPeriod, alphaLcParenR, etc.)
    """
    # Build bullet paragraphs
    bullets_xml = ''
    for i, item in enumerate(bullet_items):
        is_last = (i == len(bullet_items) - 1)
        end_para = '<a:endParaRPr lang="en-US"/>' if is_last else ''
        bullets_xml += f'''          <a:p>
            <a:pPr lvl="0"/>
            <a:r>
              <a:rPr lang="en-US"/>
              <a:t>{item}</a:t>
            </a:r>
            {end_para}
          </a:p>
'''

    slide_xml = f'''<sld xmlns="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <cSld>
    <spTree>
      <nvGrpSpPr>
        <cNvPr id="1" name=""/>
        <cNvGrpSpPr/>
        <nvPr/>
      </nvGrpSpPr>
      <grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </grpSpPr>
      <sp>
        <nvSpPr>
          <cNvPr id="2" name="Title 1"/>
          <cNvSpPr txBox="0">
            <a:spLocks noGrp="1"/>
          </cNvSpPr>
          <nvPr>
            <ph type="title"/>
          </nvPr>
        </nvSpPr>
        <spPr/>
        <txBody>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p>
            <a:r>
              <a:rPr lang="en-US"/>
              <a:t>{title_text}</a:t>
            </a:r>
            <a:endParaRPr lang="en-US"/>
          </a:p>
        </txBody>
      </sp>
      <sp>
        <nvSpPr>
          <cNvPr id="3" name="Content Placeholder 2"/>
          <cNvSpPr txBox="0">
            <a:spLocks noGrp="1"/>
          </cNvSpPr>
          <nvPr>
            <ph idx="1"/>
          </nvPr>
        </nvSpPr>
        <spPr/>
        <txBody>
          <a:bodyPr/>
          <a:lstStyle>
            <a:lvl1pPr marL="457200" indent="228600" algn="l">
              <a:buAutoNum type="{auto_num_type}"/>
            </a:lvl1pPr>
          </a:lstStyle>
{bullets_xml}        </txBody>
      </sp>
    </spTree>
  </cSld>
  <clrMapOvr>
    <a:masterClrMapping/>
  </clrMapOvr>
</sld>'''
    return slide_xml
```

### Auto-Numbering Types

Common `buAutoNum type` values:
- `arabicPeriod` — 1., 2., 3.
- `alphaLcParenR` — a), b), c)
- `alphaUcParenR` — A), B), C)
- `romanLcParenR` — i), ii), iii)
- `arabicParenR` — 1), 2), 3)
- `none` — no auto-numbering (plain bullets)
