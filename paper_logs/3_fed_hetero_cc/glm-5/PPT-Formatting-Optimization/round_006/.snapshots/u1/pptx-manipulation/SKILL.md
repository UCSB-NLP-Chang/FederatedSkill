---
name: pptx-manipulation
description: Edit, format, and verify PowerPoint (.pptx) files using python-pptx and lxml. Use when tasks require modifying slide content, text formatting, shape properties, adding slides, standardizing text, or bullet numbering. Trigger phrases: "format pptx", "clean up presentation", "modify slide", "caption", "text box", "standardize", "replace text", "bullet", "numbering".
---

# PowerPoint Manipulation with python-pptx

Programmatically edit and format .pptx files. Covers both high-level python-pptx API and XML fallback for complex operations.

## Core Workflow

1. **Load**: `prs = Presentation(path)`
2. **Iterate safely**: Handle `NotImplementedError` on `shape_type`, iterate into group shapes
3. **Identify targets precisely**: Collect ALL matching shapes before processing
4. **Modify at correct level**: Paragraph-level for fonts (NOT shape-level), EMU wrappers for positions
5. **Handle multi-run text**: PPTX splits text into multiple `<a:r>` runs per paragraph
6. **Verify exhaustively**: Re-open saved file AND run external tests — self-verification alone is insufficient
7. **Save**: `prs.save(output_path)` — never overwrite input during iteration

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

## Multi-Shape Replacement (CRITICAL)

When replacing content on a slide, **always check for multiple shapes** that might contain similar content. Collect ALL targets first, then process:

```python
# WRONG: Only processes first match
target_shape = None
for shape in slide.shapes:
    if hasattr(shape, 'text_frame') and 'old text' in shape.text:
        target_shape = shape
        break  # DANGEROUS: misses duplicates

# CORRECT: Collect ALL matches, process each
targets = []
for shape in slide.shapes:
    if hasattr(shape, 'text_frame') and 'old text' in shape.text:
        targets.append(shape)

for shape in targets:
    # Replace content in each shape
    tf = shape.text_frame
    tf.clear()  # Remove all paragraphs
    p = tf.paragraphs[0] if tf.paragraphs else tf.add_paragraph()
    p.text = 'New standardized text'
    p.font.name = 'Arial'
```

**After replacement, verify zero stale shapes remain:**

```python
# Re-open and check for stale content
prs_check = Presentation(output_path)
for slide_idx, slide in enumerate(prs_check.slides, 1):
    for shape in slide.shapes:
        if hasattr(shape, 'text_frame'):
            text = shape.text
            if 'old text' in text.lower() or 'placeholder' in text.lower():
                print(f"STALE CONTENT on slide {slide_idx}: {text[:50]}")
```

## CSV-Driven Content Standardization

When standardizing captions or labels from a CSV mapping:

```python
import csv

# Load mapping
caption_map = {}
with open('mapping.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        caption_map[row['raw'].strip()] = row['canonical'].strip()

# Track unique values in order of first appearance
seen = []
for slide in prs.slides:
    for shape in slide.shapes:
        if not hasattr(shape, 'text_frame'):
            continue
        text = shape.text.strip()
        if text in caption_map:
            canonical = caption_map[text]
            if canonical not in seen:
                seen.append(canonical)
            # Replace text while preserving formatting...
```

## Auto-Numbered Bullets (XML Manipulation)

`python-pptx` lacks high-level API for bullet numbering. Use `lxml`/`oxml` directly:

```python
from pptx.oxml.ns import qn

def set_auto_number(paragraph, num_type='arabicPeriod'):
    """Apply auto-numbering to a paragraph via XML."""
    pPr = paragraph._p.get_or_add_pPr()

    # CRITICAL: Remove existing bullet elements FIRST
    # Duplicates cause verifier failure (R3 u0, R5 u0)
    for child in list(pPr):
        if child.tag in (qn('a:buChar'), qn('a:buNone'), qn('a:buAutoNum')):
            pPr.remove(child)

    # Verify removal succeeded before adding new
    buAutoNum = pPr.makeelement(qn('a:buAutoNum'), {'type': num_type})
    pPr.append(buAutoNum)
```

Common `num_type` values: `arabicPeriod`, `alphaLcParenBoth`, `romanUcPeriod`.

**Verification checkpoint** - confirm no duplicate buAutoNum:

```python
def get_bullet_type(paragraph):
    pPr = paragraph._p.find(qn('a:pPr'))
    if pPr is None:
        return None
    buAutoNums = pPr.findall(qn('a:buAutoNum'))
    if len(buAutoNums) > 1:
        print(f"WARNING: {len(buAutoNums)} buAutoNum elements found — duplicates!")
    if buAutoNums:
        return buAutoNums[0].get('type')
    return 'none'
```

See `references/bullets-numbering.md` for explicit numbering patterns.

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

**Warning**: Heuristics can fail. Always enumerate shapes first and verify matches.

## Verification Checklist (CRITICAL)

After modifications, **self-verification alone is insufficient**. Always:

1. Re-open file to confirm changes persisted
2. `paragraph.font.name` returns expected font
3. `paragraph.font.size.pt` returns expected point size
4. `paragraph.font.bold` is `False` (not `None`)
5. `Emu(shape.top).inches` shows expected position
6. **No stale content**: Search for old text strings that should have been replaced
7. **All target shapes processed**: Count matches before and after
8. **Run external test suite** — tests may fail even when script output looks correct (R3 u1, R5 u1)

Run `scripts/verify_formatting.py` for automated check, but **do NOT rely on it alone**.

## Known Invariants (by sub-task)

### B1: Structural manipulation (auto-numbered bullets, slide additions)

- **buAutoNum duplicates**: Remove existing `<a:buAutoNum>` BEFORE adding new — duplicates cause verifier failure (R3 u0, R5 u0)
- **Slide additions**: Need unique rId + entry in presentation.xml + `[Content_Types].xml` Override entry
- **Identifier capture**: Sample attributes BEFORE modifying — sampling after invalidates identification (R3 u2)
- **False-positive verification**: Self-verification can pass while external tests fail — always run external tests (R3 u1, R5 u1)

### B2: Caption formatting & CSV standardization

- **Paragraph-level font**: Setting `shape.font` has NO effect — must use `paragraph.font`
- **EMU wrappers mandatory**: Raw floats cause TypeError on position/size
- **Color type check**: Accessing `.rgb` on unset color raises AttributeError — check `color.type is not None` first
- **Multi-run concatenation**: Text may span multiple `<a:r>` runs — concatenate all for verification
- **Multi-shape replacement**: Collect ALL matching shapes before processing — single replacement leaves stale content (R5 u2)

### hwpx-caption-formatting (B2)

- Captions: `len(text) > 40`, `top > Inches(5)` (lower half of slide)
- Font: Arial, 16pt, non-bold, #49607A
- Position after cleaning: top=6.6in, width=9in, height=0.4in

## Anti-Patterns

- **Don't** set `shape.font` — always use `paragraph.font`
- **Don't** use raw floats for position/size — wrap with `Inches()` or `Emu()`
- **Don't** assume single run per paragraph — iterate all `paragraph.runs`
- **Don't** access `font.color.rgb` without checking `color.type`
- **Don't** assume all shapes have `shape_type` — catch `NotImplementedError`
- **Don't** overwrite input file until verified — write to `_output` first
- **Don't** modify while iterating without collecting targets first
- **Don't** trust heuristics alone — enumerate and verify shape matches
- **Don't** assume one shape per slide — check for duplicates
- **Don't** rely on `python-pptx` high-level API for bullet numbering — use `oxml` XML manipulation
- **Don't** assign `shape.text = "new"` — it strips formatting and breaks multi-run structures
- **Don't** trust self-verification alone — external tests may fail even when script output looks correct
- **Don't** add buAutoNum without removing existing bullet elements first — duplicates cause verifier failure

## Fallback: Direct XML

If python-pptx fails on complex shapes, presentations are ZIP files with XML:

```bash
unzip presentation.pptx -d pptx_extracted/
# Edit pptx_extracted/ppt/slides/slide1.xml
zip -r new_presentation.pptx pptx_extracted/
```

Use `lxml` for XML modifications. See `references/pptx_xml_notes.md` for namespaces.

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
| Stale content remains | Multiple shapes with similar text | Collect ALL targets before processing, verify after |
| Bullets not numbered | Used `p.level` without numbering format | Use explicit numbers or XML-level formatting |
| Verifier fails but script passes | Self-verification insufficient | Run external test suite |

## Scripts and References

- `scripts/verify_formatting.py` — Verify formatting, list shapes, check captions
- `references/emu-conversions.md` — EMU unit conversions and slide dimensions
- `references/pptx_xml_notes.md` — XML namespaces and structure for fallback editing
- `references/bullets-numbering.md` — Bullet and numbering patterns
