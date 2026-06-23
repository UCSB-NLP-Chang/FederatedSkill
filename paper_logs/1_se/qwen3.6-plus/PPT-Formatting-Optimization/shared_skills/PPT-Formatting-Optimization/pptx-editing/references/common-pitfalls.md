# python-pptx Common Pitfalls & API Notes

## Import Paths
- `RGBColor`: `from pptx.dml.color import RGBColor` (NOT `pptx.dml` or `pptx.util`)
- `Inches`, `Pt`, `Emu`: `from pptx.util import Inches, Pt, Emu`
- `MSO_PLACEHOLDER_TYPE`: `from pptx.enum.shapes import MSO_PLACEHOLDER_TYPE`

## Color Handling
```python
from pptx.dml.color import RGBColor

# CORRECT: 3 integers or from_string()
color1 = RGBColor(0x7A, 0x6F, 0x65)
color2 = RGBColor.from_string("7A6F65")

# INCORRECT: Raises TypeError
# color_bad = RGBColor("7A6F65")

if run.font.color.type is not None:
    current_rgb = run.font.color.rgb
else:
    # Handle missing color
```

## Run XML Access
```python
# Correct
r_xml = run._r
# Incorrect (raises AttributeError)
r_xml = run._element
```

## Text Frame Properties
- `word_wrap`: Boolean. Set to `False` to force single-line text.
- `auto_size`: `None` disables auto-sizing. `MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT` expands shape.
- Margins: `text_frame.margin_left`, etc. Use `Pt()` or `Inches()`.

## Adding Slides
```python
from pptx.util import Inches, Pt
slide_layout = prs.slide_layouts[6] # Blank layout
slide = prs.slides.add_slide(slide_layout)
```

## Positioning
- 1 inch = 914400 EMU
- Use `Inches(2.17)` for left, `Inches(6.6)` for top.
- Width/Height: `Inches(9.0)`, `Inches(0.4)`

## Bullet XML Injection
When `python-pptx` cannot set bullet styles natively, use `lxml`:
```python
from lxml import etree
from pptx.oxml.ns import qn

pPr = p._pPr
if pPr is None:
    pPr = etree.SubElement(p._p, qn('a:pPr'))

# Clear old bullets
for child in list(pPr):
    if child.tag in (qn('a:buChar'), qn('a:buNone'), qn('a:buAutoNum')):
        pPr.remove(child)

# Set auto-numbering
bu = etree.SubElement(pPr, qn('a:buAutoNum'))
bu.set('type', 'arabicPeriod')
```
