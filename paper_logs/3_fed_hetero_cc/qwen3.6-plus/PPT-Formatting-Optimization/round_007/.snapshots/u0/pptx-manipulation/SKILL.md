---
name: pptx-manipulation
description: Edit, format, and verify PowerPoint (.pptx) files using python-pptx and lxml. Use for text formatting, shape positioning, slide modifications, list formatting, or structural changes. Trigger phrases: "format pptx", "clean up presentation", "modify slide", "caption", "archive sheet", "standardize", "replace text", "bullet", "numbering".
---

# PowerPoint Manipulation

## Workflow

1. Load: `prs = Presentation(path)`
2. Iterate slides/shapes with safe guards
3. Collect ALL target shapes before modifying (avoid stale content)
4. Apply changes at run/paragraph level
5. Save: `prs.save(output_path)`
6. Verify by reopening AND run external tests

## Safe Shape Iteration

```python
for slide_idx, slide in enumerate(prs.slides, 1):
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

**Anti-pattern**: Do NOT index `prs.slides` with lists or slices (e.g., `prs.slides[[1,2]]`) — iterate directly or use `enumerate`.

## Text Formatting

Apply at **run level** for changes to persist on existing text:

```python
from pptx.util import Pt
from pptx.dml.color import RGBColor

tf = shape.text_frame
for paragraph in tf.paragraphs:
    for run in paragraph.runs:
        run.font.name = 'Arial'
        run.font.size = Pt(16)
        run.font.bold = False
        run.font.color.rgb = RGBColor(0x49, 0x60, 0x7A)
```

**Anti-pattern**: `shape.font` has no effect. `paragraph.font` works for new text but may not propagate to existing runs.

## Positioning and Sizing

```python
from pptx.util import Inches, Emu

shape.left = Inches(2.17)
shape.top = Inches(6.6)
shape.width = Inches(9)
shape.height = Inches(0.4)
```

**CRITICAL**: Raw floats cause `TypeError`. Always wrap with `Inches()`, `Pt()`, or `Emu()`.

## Multi-Run Text

PPTX splits text into multiple `<a:r>` runs per paragraph:

```python
def get_full_text(shape):
    texts = []
    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            texts.append(run.text)
    return ''.join(texts)
```

## Caption Identification

```python
def is_caption(shape, min_len=40, min_top_inches=5):
    if not hasattr(shape, 'text_frame'):
        return False
    text = get_full_text(shape).strip()
    if len(text) < min_len:
        return False
    try:
        return Emu(shape.top).inches >= min_top_inches
    except (AttributeError, NotImplementedError):
        return False
```

## CSV-Driven Standardization

```python
import csv

# Load mapping
caption_map = {}
with open('mapping.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        caption_map[row['raw'].strip()] = row['canonical'].strip()

# Idempotent: match both original AND already-standardized
all_valid = set(caption_map.keys()) | set(caption_map.values())

for slide in prs.slides:
    for shape in slide.shapes:
        if not hasattr(shape, 'text_frame'):
            continue
        text = get_full_text(shape).strip()
        if text in all_valid:
            canonical = caption_map.get(text, text)  # Returns text if already canonical
            # Replace text...
```

## Multi-Shape Replacement (CRITICAL)

**Always collect ALL matches before processing**:

```python
targets = []
for shape in slide.shapes:
    if hasattr(shape, 'text_frame') and 'old text' in get_full_text(shape):
        targets.append(shape)

for shape in targets:
    tf = shape.text_frame
    tf.clear()
    p = tf.paragraphs[0] if tf.paragraphs else tf.add_paragraph()
    run = p.add_run()
    run.text = 'New text'
```

**Anti-pattern**: `break` after first match leaves duplicate shapes unmodified.

## Auto-Numbered Bullets (XML)

```python
from pptx.oxml.ns import qn

def set_auto_number(paragraph, num_type='arabicPeriod'):
    pPr = paragraph._p.get_or_add_pPr()
    # CRITICAL: Remove existing bullet elements FIRST
    for child in list(pPr):
        if child.tag in (qn('a:buChar'), qn('a:buNone'), qn('a:buAutoNum')):
            pPr.remove(child)
    buAutoNum = pPr.makeelement(qn('a:buAutoNum'), {'type': num_type})
    pPr.append(buAutoNum)
```

Common types: `arabicPeriod`, `alphaLcParenBoth`, `romanUcPeriod`.

**Anti-pattern**: Duplicate `<a:buAutoNum>` elements cause verifier failure. Always remove existing before adding new.

## Archive Sheet Creation (CRITICAL)

**Create ONE text frame with multiple paragraphs, NOT multiple shapes**:

```python
def add_archive_sheet(prs, items, title="Archive Sheet"):
    """Add summary slide with numbered items."""
    blank_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[-1]
    slide = prs.slides.add_slide(blank_layout)

    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12), Inches(1))
    title_frame = title_box.text_frame
    title_frame.text = title
    title_frame.paragraphs[0].font.size = Pt(24)
    title_frame.paragraphs[0].font.bold = True

    # ONE text frame with multiple paragraphs
    list_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(12), Inches(5))
    tf = list_box.text_frame
    tf.clear()

    for item in items:
        p = tf.add_paragraph()
        p.text = item  # NO explicit "1. " prefix
        p.font.size = Pt(14)
        p.font.name = 'Calibri'
        set_auto_number(p, num_type='arabicPeriod')

    return slide
```

**Common failure (R6)**: Creating multiple shapes with same content instead of ONE shape with multiple paragraphs.

## Verification

Self-verification can pass while external tests fail. After save:

1. Re-open file: `prs_check = Presentation(output_path)`
2. Verify ALL target shapes (not just samples)
3. **Run external test suite** if available
4. Check for stale content (old text strings)
5. Verify formatting at run level

## Known Invariants (by sub-task)

### B1: Structural manipulation
- **buAutoNum duplicates**: Remove existing before adding — duplicates cause verifier failure (R3, R5, R6)
- **Slide additions**: Need unique rId + entry in presentation.xml + Content_Types.xml

### B2: Caption formatting & Archive Sheet
- Captions: `len(text) > 40`, `top > Inches(5)` (lower half)
- Font: Arial/Calibri, 15-16pt, non-bold, specific color per task
- **Archive Sheet**: ONE text frame, multiple paragraphs, XML `buAutoNum` — NOT multiple shapes

### hwpx-caption-formatting
- Font: Arial, 16pt, non-bold, #49607A
- Position after cleaning: top=6.6in, width=9in, height=0.4in

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. The verifier's tolerance decides acceptable precision.

## Anti-Patterns

- Do NOT use `shape.shape_type` — check `hasattr(shape, 'text_frame')` instead
- Do NOT set `shape.font` — use `run.font` or `paragraph.font`
- Do NOT pass raw floats to position/size — wrap with `Inches()`, `Pt()`, or `Emu()`
- Do NOT assume single-run text — concatenate all runs
- Do NOT access `.rgb` on unset color — check `color.type is not None` first
- Do NOT rely on `python-pptx` high-level API for bullet numbering — use `oxml` XML
- Do NOT assign `shape.text = "new"` — it strips formatting
- Do NOT `break` after first match — collect ALL targets first
- Do NOT trust self-verification alone — run external tests
- Do NOT create multiple shapes for Archive Sheet list — use ONE text frame with multiple paragraphs
