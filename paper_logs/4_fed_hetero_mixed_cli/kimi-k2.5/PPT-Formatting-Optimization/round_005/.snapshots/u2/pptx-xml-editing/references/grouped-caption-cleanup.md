# Grouped Caption Cleanup Workflow

Complete guide for cleaning up floating captions that exist as grouped shapes with badges/labels.

## Typical Group Structure

```xml
<p:grpSp>
  <p:nvGrpSpPr>
    <p:cNvPr id="7" name="Caption Group 7"/>
  </p:nvGrpSpPr>
  <p:grpSpPr>
    <a:xfrm>
      <a:off x="685800" y="1320000"/>    <!-- Group position -->
      <a:ext cx="3657600" cy="620000"/>  <!-- Group size -->
    </a:xfrm>
  </p:grpSpPr>

  <!-- Badge/Label shape -->
  <p:sp>
    <p:nvSpPr>
      <p:cNvPr id="8" name="Badge 8"/>
    </p:nvSpPr>
    <p:txBody>
      <a:p><a:r><a:t>Route Name</a:t></a:r></a:p>
    </p:txBody>
  </p:sp>

  <!-- Caption text shape -->
  <p:sp>
    <p:nvSpPr>
      <p:cNvPr id="6" name="Caption Banner Text"/>
    </p:nvSpPr>
    <p:txBody>
      <a:p>
        <a:r><a:rPr/><a:t>Caption text here</a:t></a:r>
      </a:p>
    </p:txBody>
  </p:sp>
</p:grpSp>
```

## Finding Caption Groups

```python
NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
}

# Find by group name pattern
for grpSp in root.findall('.//p:grpSp', NS):
    cNvPr = grpSp.find('p:nvGrpSpPr/p:cNvPr', NS)
    if cNvPr is not None and 'Caption Group' in cNvPr.get('name', ''):
        yield grpSp
```

## Modifying Group Position and Size

```python
def reposition_group(grpSp, new_width, new_height, x, y, ns):
    """Reposition and resize a group shape."""
    xfrm = grpSp.find('p:grpSpPr/a:xfrm', ns)
    if xfrm is not None:
        off = xfrm.find('a:off', ns)
        ext = xfrm.find('a:ext', ns)
        if off is not None:
            off.set('x', str(x))
            off.set('y', str(y))
        if ext is not None:
            ext.set('cx', str(new_width))
            ext.set('cy', str(new_height))

# Bottom-center positioning
SLIDE_WIDTH = 12192000
SLIDE_HEIGHT = 6858000
new_width = 4000000
new_height = 600000
x = (SLIDE_WIDTH - new_width) // 2
y = SLIDE_HEIGHT - new_height - 200000  # 200000 EMU margin

reposition_group(grpSp, new_width, new_height, x, y, NS)
```

## Formatting Caption Text (Multi-Run Safe)

**CRITICAL**: Always format ALL `a:r` runs in the caption:

```python
def format_caption_text(grpSp, font_name, font_size_pt, color_hex, remove_bold=True, ns=None):
    """Format caption text across all runs."""
    for sp in grpSp.findall('p:sp', ns):
        cNvPr = sp.find('p:nvSpPr/p:cNvPr', ns)
        if cNvPr is not None and 'Caption' in cNvPr.get('name', ''):
            for p in sp.findall('.//a:p', ns):
                for r in p.findall('a:r', ns):
                    rPr = r.find('a:rPr', ns)
                    if rPr is None:
                        rPr = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}rPr')
                        r.insert(0, rPr)

                    rPr.set('sz', str(font_size_pt * 100))
                    if remove_bold and 'b' in rPr.attrib:
                        del rPr.attrib['b']

                    latin = rPr.find('a:latin', ns)
                    if latin is None:
                        latin = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/drawingml/2006/main}latin')
                    latin.set('typeface', font_name)

                    solidFill = rPr.find('a:solidFill', ns)
                    if solidFill is None:
                        solidFill = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill')
                    for child in list(solidFill):
                        solidFill.remove(child)
                    srgbClr = ET.SubElement(solidFill, '{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr')
                    srgbClr.set('val', color_hex.upper())
```

## Extracting Full Text Content

Join all runs to get the complete caption text:

```python
def get_full_text(grpSp, ns):
    """Extract full text from caption group, joining all runs."""
    texts = []
    for sp in grpSp.findall('p:sp', ns):
        cNvPr = sp.find('p:nvSpPr/p:cNvPr', ns)
        if cNvPr is not None and 'Caption' in cNvPr.get('name', ''):
            for t in sp.findall('.//a:t', ns):
                if t.text:
                    texts.append(t.text)
    return ''.join(texts)
```

## Verification Checklist

After cleanup, verify:
- [ ] All target slides have been processed
- [ ] Group positions are at bottom center (y ~ 6,000,000)
- [ ] Group widths match target (e.g., 4,000,000 EMUs)
- [ ] All text runs have correct font, size, color
- [ ] Bold has been removed from all runs
- [ ] Badge shapes preserved with original formatting
- [ ] Full caption text is preserved (join all runs and compare)