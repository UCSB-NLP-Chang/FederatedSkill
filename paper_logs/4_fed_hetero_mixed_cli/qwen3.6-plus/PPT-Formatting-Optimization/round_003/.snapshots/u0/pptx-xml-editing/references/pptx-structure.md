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
- Standard slide: 12,192,000 x 6,858,000 EMUs (13.33" x 7.5")

## Arial Font Width Estimates (at 15pt, in EMUs)

Use these for `cx` (width) calculations:

- Narrow (`i, l, I, j, ., ;, :, !, '`): ~50,000
- Medium (`f, t, s, r, -, (, ), [, ]`): ~70,000
- Average (`a, c, e, g, m, n, o, p, q, u, v, x, z`): ~85,000
- Wide (`A-Z, 0-9`): ~100,000
- Extra Wide (`M, Q, O, &, %, $, #, @`): ~120,000
- Space: ~40,000

Add padding: `total_width + 2 * 91440`

## Text Styling Attributes

| Attribute | Element | Values | Notes |
|-----------|---------|--------|-------|
| sz | a:rPr | 1500 = 15pt | Hundredths of a point |
| b | a:rPr | 0/1 | Bold on/off |
| i | a:rPr | 0/1 | Italic on/off |
| u | a:rPr | none/sng/dbl | Underline |
| typeface | a:latin | Font name | Latin fonts |
| val | a:srgbClr | 6-char hex | RGB without # |
| algn | a:pPr | l/r/ctr/just | Alignment |

## Position Reference

For bottom-center positioning:
- x = (slide_width - box_width) / 2
- y = slide_height - box_height - margin

Example: 10,000,000 wide box at bottom:
- x = (12192000 - 10000000) / 2 = 1096000
- y = 6858000 - 400000 - 200000 = 6258000

## Relationship Handling

When adding new slide (`slide7.xml`):

1. Add `<p:sldId id="263" r:id="rId257"/>` to `ppt/presentation.xml`
2. Add relationship to `ppt/_rels/presentation.xml.rels`:
   ```xml
   <Relationship Id="rId257"
                 Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
                 Target="slides/slide7.xml"/>
   ```
3. Add Override to `[Content_Types].xml`:
   ```xml
   <Override PartName="/ppt/slides/slide7.xml"
             ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
   ```
4. Ensure `rId` is unique

## Auto-Numbered Bullets (buAutoNum)

```xml
<a:p>
  <a:pPr>
    <a:buAutoNum type="arabicPeriod" startAt="1"/>
  </a:pPr>
  <a:r><a:t>Bullet text</a:t></a:r>
</a:p>
```

### buAutoNum Types

| Type | Example |
|------|---------|
| arabicPeriod | 1. 2. 3. |
| arabicParenR | 1) 2) 3) |
| alphaLcParenR | a) b) c) |
| romanLcParenBoth | (i) (ii) |

### Key Points

- Each `<a:p>` with buAutoNum = one numbered item
- Numbering continues sequentially in same text body
- Use `startAt="1"` to reset
- Don't put explicit numbers in text content

### Removing Numbering

```python
pPr = paragraph.find('a:pPr', NS)
buAutoNum = pPr.find('a:buAutoNum', NS)
if buAutoNum is not None:
    pPr.remove(buAutoNum)
```

## Creating New Slides via String Template

**Use string templates instead of ElementTree** to avoid duplicate xmlns and `r:r:id` bugs.

```python
def create_slide_xml(title_text, bullet_items):
    bullets_xml = ''
    for i, item in enumerate(bullet_items):
        is_last = (i == len(bullet_items) - 1)
        end_para = '<a:endParaRPr lang="en-US"/>' if is_last else ''
        bullets_xml += f'''          <a:p>
            <a:pPr lvl="0"/>
            <a:r><a:rPr lang="en-US"/><a:t>{item}</a:t></a:r>
            {end_para}
          </a:p>
'''

    return f'''<sld xmlns="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <cSld><spTree>
    <nvGrpSpPr><cNvPr id="1" name=""/><cNvGrpSpPr/><nvPr/></nvGrpSpPr>
    <grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></a:xfrm></grpSpPr>
    <sp>
      <nvSpPr><cNvPr id="2" name="Title 1"/><cNvSpPr txBox="0"/></nvSpPr>
      <spPr/>
      <txBody><a:bodyPr/><a:lstStyle/>
        <a:p><a:r><a:rPr lang="en-US"/><a:t>{title_text}</a:t></a:r><a:endParaRPr lang="en-US"/></a:p>
      </txBody>
    </sp>
  </spTree></cSld>
  <clrMapOvr><a:masterClrMapping/></clrMapOvr>
</sld>'''
```

## Slide Cloning Checklist

### Pre-Clone: Identify Placeholders

```python
template_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
for sp in ET.fromstring(template_xml).findall('.//p:sp', NS):
    cNvPr = sp.find('p:nvSpPr/p:cNvPr', NS)
    print(f"Shape: {cNvPr.get('name')} (id={cNvPr.get('id')})")
```

### During Clone: Remove Unwanted Shapes

```python
sp_tree = new_root.find('.//p:spTree', NS)
for sp in sp_tree.findall('p:sp', NS):
    cNvPr = sp.find('p:nvSpPr/p:cNvPr', NS)
    if cNvPr is not None and 'Placeholder' in cNvPr.get('name', '':
        sp_tree.remove(sp)
```

### Post-Clone Validation

- [ ] Only intended shapes remain
- [ ] Text content is new, not template placeholder text
- [ ] Position/size preserved/modified as intended

## Finding Next Available IDs

```python
import re
rels = z.read('ppt/_rels/presentation.xml.rels').decode('utf-8')
rids = [int(m) for m in re.findall(r'Id="rId(\d+)"', rels)]
new_rid = max(rids) + 1

pres = z.read('ppt/presentation.xml').decode('utf-8')
ids = [int(m) for m in re.findall(r'<p:sldId[^>]+id="(\d+)"', pres)]
new_slide_id = max(ids) + 1
```

## Common Placeholder Shape Names

- `Title 1` - Slide title
- `Content Placeholder 2` - Main content
- `Text Placeholder 3` - Additional text
- `Date Placeholder 4` - Date field
- `Footer Placeholder 5` - Footer
- `Slide Number Placeholder 6` - Page number