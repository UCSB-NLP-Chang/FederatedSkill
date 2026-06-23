# Common python-pptx Patterns and Pitfalls

Reference for using the python-pptx high-level API effectively, with workarounds for common limitations.

## Installation in Isolated Environment

```bash
python3 -m venv /tmp/pptx_venv
/tmp/pptx_venv/bin/pip install python-pptx
```

Use `/tmp/pptx_venv/bin/python3` for all subsequent commands.

If system Python requires `--break-system-packages`:
```bash
pip install python-pptx --break-system-packages
```

## Critical API Quirks

### RGBColor Import

```python
# CORRECT
from pptx.dml.color import RGBColor

color = RGBColor(0x7A, 0x6F, 0x65)  # hex #7A6F65

# WRONG - wrong capitalization
from pptx.dml.color import RgbColor  # ImportError
```

### Safe Color Access

Color values may be `NoneColor` (inherited or unset). **Always check before accessing `.rgb`:**

```python
from pptx.dml.color import RGBColor

# Safe color reading
def get_rgb_safe(font_color):
    if font_color is None or font_color.type is None:
        return None
    try:
        return font_color.rgb
    except AttributeError:
        return None

# Safe color setting
from pptx.dml.color import RGBColor

run.font.color.rgb = RGBColor(0x7A, 0x6F, 0x65)
```

### Position and Size Units (CRITICAL: Must be Integer)

python-pptx uses EMUs (English Metric Units) natively. **Values must be integers, not floats:**

```python
from pptx.util import Inches, Pt, Emu

# EMU is the native unit (1 inch = 914400 EMUs)
# MUST cast to int - float causes TypeError!
shape.left = int(Inches(1.52))        # 1390656 EMUs
shape.width = int(Inches(10))         # 9144000 EMUs
shape.top = int(Inches(6.09))         # 5562600 EMUs

# Font size in points
run.font.size = Pt(16)                # Works (returns Length object)
```

**Common error:** `TypeError: value must be an integral type, got <class 'float'>`

### Accessing the Underlying XML (lxml)

When high-level API lacks features, access lxml elements directly:

```python
from pptx.oxml.ns import qn

# Get paragraph's XML element
p_elem = paragraph._p  # lxml.etree._Element

# Check for numbering properties
numPr = p_elem.find(qn('a:pPr/a:buAutoNum'))
has_numbering = numPr is not None

# Add numbering to paragraph
from lxml import etree
pPr = p_elem.get_or_add_pPr()
buAutoNum = etree.SubElement(pPr, qn('a:buAutoNum'))
buAutoNum.set('type', 'arabicPeriod')  # 1., 2., 3.
```

**Common numbering types:**
- `arabicPeriod` — 1., 2., 3.
- `alphaLcParen` — a), b), c)
- `alphaUcParen` — A), B), C)
- `romanLcParen` — i), ii), iii)

**Do NOT use `getparent()`** — lxml elements don't have this method. Access `_parent` if needed through python-pptx internals.

### Handling Unrecognized Shape Types

```python
from pptx.enum.shapes import MSO_SHAPE_TYPE

# Wrap shape access in try/except
def safe_get_shape_type(shape):
    try:
        return shape.shape_type
    except NotImplementedError:
        return None  # Unknown shape type, use XML manipulation

# Skip shapes that can't be processed
for shape in slide.shapes:
    shape_type = safe_get_shape_type(shape)
    if shape_type is None:
        continue  # Skip unrecognized shapes
```

## Pattern: Updating Location Captions

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor

def update_location_caption(shape, new_width=Inches(10)):
    """Widen caption and center at bottom of slide."""
    # Standard slide: 13.333" × 7.5"
    slide_width = Inches(13.333)
    slide_height = Inches(7.5)
    
    # Center horizontally, position near bottom
    # CRITICAL: Cast all positions to int!
    new_left = int((slide_width - new_width) / 2)
    new_top = int(Inches(6.09))  # Near bottom
    new_width_int = int(new_width)
    new_height = int(Inches(0.5))
    
    shape.left = new_left
    shape.top = new_top
    shape.width = new_width_int
    shape.height = new_height
    
    # Update font properties
    for paragraph in shape.text_frame.paragraphs:
        for run in paragraph.runs:
            run.font.name = 'Arial'
            run.font.size = Pt(16)
            run.font.bold = False
            run.font.color.rgb = RGBColor(0x7A, 0x6F, 0x65)

# Usage
prs = Presentation('input.pptx')
for slide_num, slide in enumerate(prs.slides, 1):
    for shape in slide.shapes:
        if shape.has_text_frame and 'caption' in shape.name.lower():
            update_location_caption(shape)
prs.save('output.pptx')
```

## Pattern: Creating Numbered Lists

python-pptx doesn't expose numbering well. Use XML manipulation:

```python
from pptx.oxml.ns import qn
from lxml import etree

def set_numbered_list(text_frame, items):
    """Replace text frame content with auto-numbered items."""
    # Clear existing paragraphs except first
    while len(text_frame.paragraphs) > 1:
        p = text_frame.paragraphs[-1]
        p._p.getparent().remove(p._p)  # Remove via lxml
    
    first_para = text_frame.paragraphs[0]
    first_para.clear()  # Remove runs
    
    # Add items
    for i, item_text in enumerate(items):
        if i == 0:
            p = first_para
        else:
            p = text_frame.add_paragraph()
        
        run = p.add_run()
        run.text = item_text
        
        # Add numbering via XML
        pPr = p._p.get_or_add_pPr()
        buAutoNum = etree.SubElement(pPr, qn('a:buAutoNum'))
        buAutoNum.set('type', 'arabicPeriod')

# Usage
items = ['Harbor Point Logistics Center', 'Maple Terrace Apartments']
set_numbered_list(shape.text_frame, items)
```

## Pattern: Finding Shapes by Name or Type

```python
from pptx.enum.shapes import MSO_SHAPE_TYPE

# Find by shape type and name pattern
def find_captions(slide):
    captions = []
    for shape in slide.shapes:
        try:
            if (shape.shape_type == MSO_SHAPE_TYPE.TEXT_BOX and
                shape.has_text_frame and
                '文本框' in shape.name):  # Chinese "text box"
                captions.append(shape)
        except NotImplementedError:
            continue  # Skip unrecognized shapes
    return captions

# Find content placeholders
def find_content_placeholder(slide):
    for shape in slide.shapes:
        if shape.is_placeholder:
            placeholder_format = shape.placeholder_format
            if placeholder_format.type == 2:  # BODY placeholder
                return shape
    return None
```

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| `AttributeError: no .rgb property on color type '_NoneColor'` | Color is inherited/unset | Check `font.color.type` before accessing `.rgb` |
| `AttributeError: '_Paragraph' object has no attribute 'getparent'` | Wrong lxml access pattern | Use `p._p.getparent()` not `p.getparent()` |
| `ImportError: cannot import name 'RgbColor'` | Wrong capitalization | Use `RGBColor` (all caps) |
| `TypeError: value must be an integral type, got <class 'float'>` | EMU position is float | Cast to `int()`: `int(Inches(1.5))` |
| `NotImplementedError: Shape instance of unrecognized shape type` | Unknown shape type | Wrap in try/except, use XML fallback |
| Changes not visible in PowerPoint | File caching or wrong save path | Verify output path, close/reopen PowerPoint |
| Font name not applied | Font not installed on system | Check font availability or embed fonts |
| Numbering not showing | Wrong namespace or missing `buAutoNum` | Use `qn('a:buAutoNum')` for namespace |

## When to Abandon python-pptx for Direct XML

Switch to direct XML manipulation when you encounter:

1. **Unrecognized shape types** — `NotImplementedError` on `shape.shape_type`
2. **Color read failures** — Persistent `_NoneColor` errors despite checks
3. **Precision requirements** — Need exact EMU values without rounding
4. **Complex numbering** — Multi-level lists or custom bullet formats
5. **Bulk operations** — Faster to regex-replace across all slides
6. **Missing properties** — Features not exposed in high-level API

See main `SKILL.md` for XML manipulation workflow.
