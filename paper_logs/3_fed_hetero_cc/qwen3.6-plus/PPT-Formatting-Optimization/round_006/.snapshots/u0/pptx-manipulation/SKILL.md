---
name: pptx-manipulation
description: Edit, format, and verify PowerPoint (.pptx) files using python-pptx and lxml. Use for text formatting, shape positioning, slide modifications, list formatting, or structural changes.
---

# PowerPoint Manipulation

## Workflow

1. Load: `prs = Presentation(path)`
2. Iterate slides/shapes with safe guards
3. Collect ALL target shapes before modifying (avoid stale content)
4. Apply changes at paragraph level
5. Save: `prs.save(output_path)`
6. Verify by reopening AND run external tests — self-verification alone is insufficient

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

## Auto-Numbered Bullets (XML Manipulation)
`python-pptx` lacks a high-level API for bullet numbering types. Use `lxml`/`oxml` directly:

```python
from pptx.oxml.ns import qn

def set_auto_number(paragraph, num_type='arabicPeriod'):
    pPr = paragraph._p.get_or_add_pPr()
    # Remove existing bullet elements if any
    for child in list(pPr):
        if child.tag in (qn('a:buChar'), qn('a:buNone'), qn('a:buAutoNum')):
            pPr.remove(child)
    buAutoNum = pPr.makeelement(qn('a:buAutoNum'), {'type': num_type})
    pPr.append(buAutoNum)
```
Common `num_type` values: `arabicPeriod`, `alphaLcParenBoth`, `romanUcPeriod`.

**Verification**:
```python
def get_bullet_type(paragraph):
    pPr = paragraph._p.find(qn('a:pPr'))
    if pPr is None: return None
    buAutoNum = pPr.find(qn('a:buAutoNum'))
    if buAutoNum is not None: return buAutoNum.get('type')
    return 'none'
```

## Text Standardization via CSV
When a task provides a mapping file (CSV/JSON) to standardize labels or captions:
1. Load mapping into a dict: `mapping = {row['original']: row['standardized'] for row in csv_reader}`
2. Iterate shapes, extract full text (handle multi-run), check if `text in mapping`.
3. Replace text: clear all runs, add single run with new text, or modify first run and delete others.
4. Preserve existing paragraph formatting; apply font/size overrides only if specified.

**Anti-pattern**: Do not replace `shape.text` directly — it destroys formatting and runs. Always manipulate `text_frame.paragraphs[0].runs`.

## Multi-Shape Replacement (CRITICAL)

When replacing content, **always check for multiple shapes** with similar text. Failure to replace ALL matching shapes leaves stale content:

```python
# CORRECT: Collect ALL matches first
targets = []
for shape in slide.shapes:
    if hasattr(shape, 'text_frame') and 'old text' in shape.text:
        targets.append(shape)

for shape in targets:
    # Replace content in each shape
    tf = shape.text_frame
    tf.clear()
    p = tf.paragraphs[0] if tf.paragraphs else tf.add_paragraph()
    p.text = 'New standardized text'
```

**Stale-content verification** (run after save):
```python
prs_check = Presentation(output_path)
for slide_idx, slide in enumerate(prs_check.slides, 1):
    for shape in slide.shapes:
        if hasattr(shape, 'text_frame'):
            text = shape.text
            if 'old text' in text.lower():
                print(f"STALE CONTENT on slide {slide_idx}: {text[:50]}")
```

**Anti-pattern**: `break` after first match leaves duplicate shapes unmodified.

## Verification (External Tests Required)

Self-verification can pass while external tests fail. After save:

1. Re-open file: `prs_check = Presentation(output_path)`
2. Verify ALL target shapes (not just samples)
3. **Run external test suite** if available — self-reported success is insufficient
4. Check for stale content (old text strings that should be replaced)

## Known Invariants (by sub-task)

### B1: Structural manipulation (auto-numbered bullets)
- **buAutoNum duplicates**: Remove existing `<a:buAutoNum>` before adding new ones — duplicates cause verifier failure (R3, R5). Verify: `pPr.find(qn('a:buAutoNum'))` is None before adding.
- See `references/bullets-numbering.md` for numbering patterns.

### hwpx-caption-formatting (B2)
- Captions: `len(text) > 40`, `top > Inches(5)` (lower half of slide)
- Font: Arial, 16pt, non-bold, #49607A
- Position after cleaning: top=6.6in, width=9in, height=0.4in
- **Multiple caption shapes**: Evidence Log slide had TWO text shapes — collect ALL targets before processing

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
- Do NOT rely on `python-pptx` high-level API for bullet numbering — use `oxml` XML manipulation
- Do NOT assign `shape.text = "new"` — it strips formatting and breaks multi-run structures
- Do NOT `break` after first shape match — collect ALL targets, then process
- Do NOT trust self-verification alone — run external tests