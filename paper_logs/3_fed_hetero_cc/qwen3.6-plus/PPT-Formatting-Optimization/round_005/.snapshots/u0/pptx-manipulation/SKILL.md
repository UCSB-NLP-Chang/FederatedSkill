---
name: pptx-manipulation
description: Edit, format, and verify PowerPoint (.pptx) files using python-pptx and lxml. Use for text formatting, shape positioning, slide modifications, or structural changes.
---

# PowerPoint Manipulation

## Workflow

1. Load: `prs = Presentation(path)`
2. Iterate slides/shapes with safe guards
3. Apply changes at paragraph level
4. Save: `prs.save(output_path)`
5. Verify by reopening

## Safe Shape Iteration

```python
for slide in prs.slides:
    for shape in slide.shapes:
        if not hasattr(shape, 'text_frame'):
            continue  # Skip non-text shapes
        if hasattr(shape, 'shapes'):  # GroupShape
            for child in shape.shapes:
                if hasattr(child, 'text_frame'):
                    process(child)
        else:
            process(shape)
```

**Anti-pattern**: Never access `shape.shape_type` directly — raises `NotImplementedError` for unrecognized shapes.

## Text Formatting (Paragraph Level)

```python
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor

tf = shape.text_frame
for paragraph in tf.paragraphs:
    paragraph.font.name = 'Arial'
    paragraph.font.size = Pt(16)
    paragraph.font.bold = False
    paragraph.font.color.rgb = RGBColor(0x49, 0x60, 0x7A)
```

**Anti-pattern**: `shape.font` has no effect — always use `paragraph.font`.

## Positioning and Sizing

```python
from pptx.util import Inches, Emu

shape.left = Inches(2.17)
shape.top = Inches(6.6)
shape.width = Inches(9)
shape.height = Inches(0.4)
```

**Anti-pattern**: Raw floats cause `TypeError` — always wrap with `Inches()` or `Emu()`.

## Multi-Run Text

PPTX splits text into multiple `<a:r>` runs per paragraph. When verifying text content:

```python
def get_full_text(shape):
    texts = []
    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            texts.append(run.text)
    return ''.join(texts)
```

## Safe Font Color Access

```python
font = paragraph.font
if font.color.type is not None:
    rgb = font.color.rgb
else:
    rgb = None  # Color not set (inherits from theme)
```

## Caption Identification

To distinguish content captions from UI labels:

```python
def is_caption(shape):
    if not hasattr(shape, 'text_frame'):
        return False
    text = shape.text.strip()
    return len(text) > 40 and shape.top > Inches(5)
```

## Known Invariants (by sub-task)

### hwpx-caption-formatting (B2)
- Captions: `len(text) > 40`, `top > Inches(5)` (lower half of slide)
- Font: Arial, 16pt, non-bold, #49607A
- Position after cleaning: top=6.6in, width=9in, height=0.4in

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. The verifier's
tolerance (often 1e-4) decides acceptable precision.

## Anti-Patterns

- Do NOT use `shape.shape_type` — check `hasattr(shape, 'text_frame')` instead
- Do NOT set `shape.font` — use `paragraph.font`
- Do NOT pass raw floats to position/size — wrap with `Inches()` or `Emu()`
- Do NOT assume single-run text — concatenate all runs in paragraph
- Do NOT access `.rgb` on unset color — check `color.type is not None` first
