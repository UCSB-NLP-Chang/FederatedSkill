---
name: pptx-manipulation
description: Edit, format, and verify PowerPoint (.pptx) files using python-pptx and lxml. Use when tasks require modifying slide content, text formatting, shape properties, or adding slides. Trigger phrases: "format pptx", "clean up presentation", "modify slide", "caption", "text box".
---

# PowerPoint Manipulation with python-pptx

Programmatically edit and format .pptx files. Covers both high-level python-pptx API and XML fallback for complex operations.

## Core Workflow

1. **Load**: `prs = Presentation(path)`
2. **Iterate safely**: Handle `NotImplementedError` on `shape_type`, iterate into group shapes
3. **Modify at correct level**: Paragraph-level for fonts (NOT shape-level), EMU wrappers for positions
4. **Handle multi-run text**: PPTX splits text into multiple `<a:r>` runs per paragraph
5. **Verify**: Re-open saved file and check properties
6. **Save**: `prs.save(output_path)` — never overwrite input during iteration

## Critical Type Requirements

**Always use EMU wrappers for position/size properties:**

```python
from pptx.util import Inches, Pt, Emu

# CORRECT - use Inches() or Emu() wrappers
shape.left = Inches(0.5)
shape.width = Inches(10.0)
shape.top = Emu(914400)  # 914400 EMUs = 1 inch

# WRONG - causes TypeError
shape.left = 0.5   # TypeError: value must be integral type
shape.width = 10.0  # TypeError!
```

## Font Formatting (MUST be paragraph-level)

**Never set `shape.font` directly — it has no effect. Always use `paragraph.font`:**

```python
from pptx.util import Pt
from pptx.dml.color import RGBColor

tf = shape.text_frame
for paragraph in tf.paragraphs:
    paragraph.font.name = 'Arial'
    paragraph.font.size = Pt(16)
    paragraph.font.bold = False
    paragraph.font.color.rgb = RGBColor(0x49, 0x60, 0x7A)
```

## Multi-Run Text Handling

PPTX splits text into multiple `<a:r>` runs. Never assume single run per paragraph:

```python
# Concatenate all runs to get full paragraph text
full_text = "".join(run.text for run in paragraph.runs)

# Iterate all runs when modifying
for paragraph in shape.text_frame.paragraphs:
    for run in paragraph.runs:
        run.font.name = 'Arial'
```

## Safe Shape Iteration

Some shapes throw `NotImplementedError` on `shape_type`. Use defensive access:

```python
for shape in slide.shapes:
    # Check text_frame exists before accessing
    if not hasattr(shape, 'text_frame'):
        continue

    # Handle grouped shapes
    if hasattr(shape, 'shapes'):  # GroupShape
        for nested in shape.shapes:
            if hasattr(nested, 'text_frame'):
                process(nested)
        continue

    # Safe to process shape
    process(shape)
```

## Safe Font Color Access

Font color may be unset. Always check before accessing `.rgb`:

```python
font = paragraph.font
if font.color.type is not None:
    rgb = font.color.rgb  # Safe to access
else:
    rgb = None  # Color uses theme/master
```

## Identifying Captions vs UI Elements

When distinguishing content captions from badges/labels:

| Characteristic | Caption | UI Element |
|----------------|---------|------------|
| Text length | > 40 chars | < 50 chars |
| Position | `top > Inches(5)` (lower half) | `top < Inches(2)` (upper) |
| Content | Descriptive sentences | Labels, badges, alerts |

```python
def is_platform_caption(shape):
    if not hasattr(shape, 'text_frame'):
        return False
    text = shape.text.strip()
    return len(text) > 40 and shape.top > Inches(5)
```

## Positioning and Sizing

```python
from pptx.util import Inches, Emu

# Set position (top-left corner)
shape.left = Inches(2.17)
shape.top = Inches(6.6)

# Set dimensions
shape.width = Inches(9)
shape.height = Inches(0.4)

# Read existing position (convert EMU to inches)
left_inches = Emu(shape.left).inches
top_inches = Emu(shape.top).inches
```

## Adding Slides

```python
# Copy layout from existing or use built-in
blank_layout = prs.slide_layouts[6]  # Often blank
new_slide = prs.slides.add_slide(blank_layout)

# Add text box
left, top, width, height = Inches(1), Inches(1), Inches(8), Inches(5.5)
txBox = new_slide.shapes.add_textbox(left, top, width, height)

# Add and format text
tf = txBox.text_frame
tf.text = "Slide Title"  # First paragraph
p = tf.add_paragraph()
p.text = "Bullet item"
p.level = 0  # First level bullet
```

## Verification Checklist

After formatting, re-open and verify:

1. `paragraph.font.name` returns expected font
2. `paragraph.font.size.pt` returns expected point size
3. `paragraph.font.bold` is `False` (not `None`)
4. `paragraph.font.color.rgb` matches expected `RGBColor`
5. `Emu(shape.top).inches` shows expected position
6. `Emu(shape.width).inches` shows expected width

**Note**: Font properties may show `None` when text inherits from theme/master. This is normal — explicit settings override theme.

## Anti-Patterns

- **Don't** set `shape.font` — always use `paragraph.font`
- **Don't** use raw floats for position/size — wrap with `Inches()` or `Emu()`
- **Don't** assume single run per paragraph — iterate all `paragraph.runs`
- **Don't** access `font.color.rgb` without checking `color.type`
- **Don't** assume all shapes have `shape_type` — catch `NotImplementedError`
- **Don't** overwrite input file until verified — write to `_output` first
- **Don't** modify while iterating without collecting targets first

## Fallback: Direct XML (if python-pptx fails)

If shape manipulation fails, presentations are ZIP files with XML:

```bash
unzip presentation.pptx -d pptx_extracted/
# Edit pptx_extracted/ppt/slides/slide1.xml
zip -r new_presentation.pptx pptx_extracted/
```

Use `lxml` for XML modifications. See `references/pptx-xml-notes.md` for namespaces.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Font changes not visible | Set on shape, not paragraph | Use `paragraph.font` |
| `TypeError: integral type` | Raw float for position/size | Wrap with `Inches()` or `Emu()` |
| `AttributeError: no .rgb` | Unset color | Check `color.type is not None` first |
| `NotImplementedError` on iteration | Unrecognized shape type | Check `hasattr(shape, 'text_frame')` before `shape_type` |
| Text incomplete | Multi-run text | Concatenate all `run.text` in paragraph |
| Position slightly off | Rounding in conversion | Use `Inches()` for setting, `Emu().inches` for reading |
| Font shows `N/A` | Theme formatting | Explicit formatting on paragraphs overrides theme |
