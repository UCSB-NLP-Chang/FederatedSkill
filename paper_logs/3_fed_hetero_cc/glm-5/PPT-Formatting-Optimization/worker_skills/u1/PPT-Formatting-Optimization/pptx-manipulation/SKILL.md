---
name: pptx-manipulation
description: Edit, format, and verify PowerPoint (.pptx) files using python-pptx and lxml. Use when tasks require modifying slide content, text formatting, shape properties, adding slides, standardizing text, bullet numbering, or creating summary/archive slides. Trigger phrases: "format pptx", "clean up presentation", "modify slide", "caption", "text box", "standardize", "replace text", "bullet", "numbering", "archive sheet", "index slide".
---

# PowerPoint Manipulation with python-pptx

Programmatically edit and format .pptx files. Covers both high-level python-pptx API and XML fallback for complex operations.

## Core Workflow

1. **Load**: `prs = Presentation(path)`
2. **Iterate safely**: Handle `NotImplementedError` on `shape_type`, iterate into group shapes
3. **Identify targets precisely**: Collect ALL matching shapes before processing
4. **Modify at correct level**: Run-level for existing text fonts, paragraph-level for new text, EMU wrappers for positions
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

## Font Formatting (MUST be paragraph/run-level)

**Never set `shape.font` directly — it has no effect. Always use `paragraph.font` or `run.font`:**

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

## Text Frame Clearing (CRITICAL)

**`tf.clear()` leaves one empty paragraph. Handle it properly to avoid empty first lines:**

```python
# WRONG: Creates empty first paragraph, breaks numbering display
tf = shape.text_frame
tf.clear()
for item in items:
    p = tf.add_paragraph()  # First add_paragraph() after clear adds AFTER empty para
    p.text = item

# CORRECT: Reuse the existing empty paragraph for first item
tf = shape.text_frame
tf.clear()
for i, item in enumerate(items):
    if i == 0:
        p = tf.paragraphs[0]  # Reuse the empty paragraph left by clear()
    else:
        p = tf.add_paragraph()
    p.text = item
    p.font.name = 'Arial'
```

**Verification**: After clearing and populating, check for empty paragraphs:

```python
for i, para in enumerate(tf.paragraphs):
    if not para.text.strip():
        print(f"WARNING: Empty paragraph at index {i}")
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
    tf.clear()
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

## CSV-Driven Content Standardization (Idempotent)

When standardizing captions or labels from a CSV mapping, handle both raw AND already-standardized values:

```python
import csv

# Load mapping
caption_map = {}
with open('mapping.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        caption_map[row['raw'].strip()] = row['canonical'].strip()

# Include BOTH observed AND preferred values when checking matches
all_valid_captions = set(caption_map.keys()) | set(caption_map.values())

# Track unique values in order of first appearance
seen = []
for slide in prs.slides:
    for shape in slide.shapes:
        if not hasattr(shape, 'text_frame'):
            continue
        text = shape.text.strip()
        if text in all_valid_captions:
            # Get standardized form (may already be standardized)
            canonical = caption_map.get(text, text)  # Returns text if already canonical
            if canonical not in seen:
                seen.append(canonical)
            # Replace text while preserving formatting...
```

**Key insight**: Some captions may already be in standardized form. Use `caption_map.get(text, text)` to handle both cases idempotently.

## Distinguishing Captions from Zone Badges

When standardizing location names, some text may be zone badges (not in mapping) that should be preserved:

```python
# Zone badges: short location names NOT in mapping, typically at top of slide
# Captions: longer descriptive text at bottom, often in mapping

def is_caption_to_standardize(shape, caption_map, min_length=15, min_top_inches=5):
    """Check if shape is a caption that needs standardization."""
    if not hasattr(shape, 'text_frame'):
        return False
    text = shape.text.strip()
    
    # Must be in mapping to need standardization
    if text not in caption_map:
        return False  # Zone badge or other element - preserve
    
    # Additional heuristics for caption position
    try:
        top_inches = Emu(shape.top).inches
        return top_inches >= min_top_inches
    except (AttributeError, NotImplementedError):
        return True  # If can't check position, assume it's a caption
```

**Important**: If a location name is NOT in the CSV mapping, preserve it unchanged. Do not attempt to standardize unmapped values.

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

## Creating Summary/Archive Sheet Slides (CRITICAL)

**CRITICAL**: Create ONE text frame with multiple paragraphs, NOT multiple shapes. Duplicate shapes cause verifier failure.

```python
from pptx.enum.shapes import MSO_SHAPE

def add_archive_sheet(prs, items, title="Archive Sheet"):
    """Add a summary slide with properly numbered items.

    WARNING: Do NOT create multiple shapes with the same text.
    Create ONE text frame with multiple paragraphs using XML numbering.
    """
    # Use blank layout (index 6 is typically blank)
    blank_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 7 else prs.slide_layouts[-1]
    slide = prs.slides.add_slide(blank_layout)

    # Add title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12), Inches(1))
    title_frame = title_box.text_frame
    title_frame.text = title
    title_frame.paragraphs[0].font.size = Pt(24)
    title_frame.paragraphs[0].font.bold = True

    # Add list with ONE shape, multiple paragraphs with XML numbering
    list_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(12), Inches(5))
    tf = list_box.text_frame
    tf.clear()

    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]  # Reuse empty paragraph
        else:
            p = tf.add_paragraph()
        p.text = item  # Text WITHOUT numbers - numbering is XML-level
        p.font.size = Pt(14)
        p.font.name = 'Calibri'

        # Apply native PowerPoint numbering via XML
        set_auto_number(p, num_type='arabicPeriod')

    return slide
```

**Verification - Archive Sheet must have exactly ONE list shape:**

```python
def verify_archive_sheet(prs):
    """Verify Archive Sheet has correct structure."""
    archive_slides = [s for s in prs.slides
                      if any('Archive Sheet' in sh.text for sh in s.shapes
                             if hasattr(sh, 'text_frame'))]
    assert len(archive_slides) <= 1, "Should have at most one Archive Sheet"

    if archive_slides:
        archive_slide = archive_slides[0]
        list_shapes = [sh for sh in archive_slide.shapes
                       if hasattr(sh, 'text_frame') and 'Archive Sheet' not in sh.text]
        assert len(list_shapes) == 1, f"Archive Sheet should have ONE list shape, found {len(list_shapes)}"
```

## Updating Existing Index Slides (CRITICAL)

**CRITICAL DIFFERENCE from creating new slides**: When REPLACING existing bullet content, ensure you create SEPARATE paragraphs for each item.

```python
def replace_index_bullets(shape, items, font_name='Arial', font_size=14):
    """Replace ALL content of an index shape with separate bullets.
    
    COMMON FAILURE (R7): Setting p.text to multi-line string creates ONE paragraph.
    MUST use add_paragraph() for each item.
    """
    tf = shape.text_frame
    tf.clear()
    
    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]  # Reuse empty paragraph after clear
        else:
            p = tf.add_paragraph()
        p.text = item  # NO "\n" separators!
        p.font.name = font_name
        p.font.size = Pt(font_size)
        p.font.bold = False
        set_auto_number(p, num_type='arabicPeriod')
    
    return len(items)  # Return count for verification
```

| Scenario | Approach | Common Failure |
|----------|----------|----------------|
| Create NEW Archive Sheet | `add_paragraph()` + XML numbering | Creating multiple shapes instead of one text frame |
| Update EXISTING index slide | Clear + `add_paragraph()` per item | Setting single paragraph text to multi-line string |

**When updating existing bullets**: Never do `p.text = "item1\nitem2\nitem3"` — this creates ONE paragraph with embedded newlines. Always loop and call `add_paragraph()` for each item.

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

**Anti-pattern**: Do NOT index `prs.slides` with lists or slices — iterate directly or use `enumerate`.

## Safe Font Color Access

Font color may be unset. Always check before accessing `.rgb`:

```python
font = paragraph.font
color = font.color
if color.type is not None and color.rgb is not None:
    rgb = color.rgb  # Safe to access
else:
    rgb = None  # Color uses theme/master or is inherited
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
8. **No empty paragraphs**: Check `tf.paragraphs` for unintended empty entries
9. **Paragraph count matches items**: `len(tf.paragraphs) == len(items)`
10. **Run external test suite** — tests may fail even when script output looks correct (R3 u1, R5 u1, R6 u1, R7 all)

Run `scripts/verify_formatting.py` or `scripts/verify_pptx.py` for automated check, but **do NOT rely on it alone**.

## Known Invariants (by sub-task)

### B1: Structural manipulation (auto-numbered bullets, slide additions)

- **buAutoNum duplicates**: Remove existing `<a:buAutoNum>` BEFORE adding new — duplicates cause verifier failure (R3 u0, R5 u0, R6 all)
- **Slide additions**: Need unique rId + entry in presentation.xml + `[Content_Types].xml` Override entry
- **Identifier capture**: Sample attributes BEFORE modifying — sampling after invalidates identification (R3 u2)
- **False-positive verification**: Self-verification can pass while external tests fail — always run external tests (R3 u1, R5 u1, R6 u1)

### B2: Caption formatting & CSV standardization

- **Paragraph-level font**: Setting `shape.font` has NO effect — must use `paragraph.font` or `run.font`
- **EMU wrappers mandatory**: Raw floats cause TypeError on position/size
- **Color type check**: Accessing `.rgb` on unset color raises AttributeError — check `color.type is not None` first
- **Multi-run concatenation**: Text may span multiple `<a:r>` runs — concatenate all for verification
- **Multi-shape replacement**: Collect ALL matching shapes before processing — single replacement leaves stale content (R5 u2)
- **Mixed caption states**: Some captions may already be standardized — check both observed AND preferred values (R6 u1)
- **Archive Sheet structure**: Must have ONE text frame with multiple paragraphs, NOT multiple shapes — duplicates cause verifier failure (R6 all)
- **Empty first paragraph**: `tf.clear()` leaves empty paragraph — reuse `tf.paragraphs[0]` for first item (R7 u1)
- **Unmapped locations**: Zone badges not in CSV mapping should be preserved unchanged (R7 u1)
- **Index update failure**: Setting `p.text = "item1\nitem2..."` creates ONE paragraph — use `add_paragraph()` per item (R7 all)

### hwpx-caption-formatting (B2)

- Captions: `len(text) > 40`, `top > Inches(5)` (lower half of slide)
- Font: Arial, 16pt, non-bold, #49607A
- Position after cleaning: top=6.6in, width=9in, height=0.4in

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. The verifier's tolerance decides acceptable precision.

## Anti-Patterns

- **Don't** set `shape.font` — always use `paragraph.font` or `run.font`
- **Don't** use raw floats for position/size — wrap with `Inches()` or `Emu()`
- **Don't** assume single run per paragraph — iterate all `paragraph.runs`
- **Don't** access `font.color.rgb` without checking `color.type is not None`
- **Don't** assume all shapes have `shape_type` — catch `NotImplementedError`
- **Don't** overwrite input file until verified — write to `_output` first
- **Don't** modify while iterating without collecting targets first
- **Don't** trust heuristics alone — enumerate and verify shape matches
- **Don't** assume one shape per slide — check for duplicates
- **Don't** rely on `python-pptx` high-level API for bullet numbering — use `oxml` XML manipulation
- **Don't** assign `shape.text = "new"` — it strips formatting and breaks multi-run structures
- **Don't** trust self-verification alone — external tests may fail even when script output looks correct
- **Don't** add buAutoNum without removing existing bullet elements first — duplicates cause verifier failure
- **Don't** assume all captions need standardization — some may already be in preferred form
- **Don't** create multiple shapes for Archive Sheet list — use ONE text frame with multiple paragraphs (R6 all)
- **Don't** use `tf.add_paragraph()` for first item after `tf.clear()` — reuse `tf.paragraphs[0]` (R7 u1)
- **Don't** standardize unmapped location names — preserve them as zone badges (R7 u1)
- **Don't** set `p.text = "item1\nitem2\n..."` for index bullets — use `add_paragraph()` per item (R7 all)

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
| Font changes not visible | Set on shape, not paragraph/run | Use `paragraph.font` or `run.font` |
| `TypeError: integral type` | Raw float for position/size | Wrap with `Inches()` or `Emu()` |
| `AttributeError: no .rgb` | Unset color | Check `color.type is not None` first |
| `NotImplementedError` on iteration | Unrecognized shape type | Check `hasattr(shape, 'text_frame')` before `shape_type` |
| Text incomplete | Multi-run text | Concatenate all `run.text` in paragraph |
| Position slightly off | Rounding in conversion | Use `Inches()` for setting, `Emu().inches` for reading |
| Font shows `N/A` | Theme formatting | Explicit formatting on paragraphs overrides theme |
| Stale content remains | Multiple shapes with similar text | Collect ALL targets before processing, verify after |
| Bullets not numbered | Used `p.level` without numbering format | Use explicit numbers or XML-level formatting |
| Verifier fails but script passes | Self-verification insufficient | Run external test suite |
| Caption not matched | Already standardized | Check both observed AND preferred values |
| Archive Sheet shows duplicate content | Created multiple shapes | Use ONE text frame with multiple paragraphs |
| Empty first line in list | `tf.clear()` + `add_paragraph()` | Reuse `tf.paragraphs[0]` for first item |
| Numbering starts at 0 or wrong | Empty paragraph before items | Check for empty paragraphs, reuse first one |
| All items on one line | Used `\n` in single paragraph text | Use `add_paragraph()` for each item |

## Scripts and References

- `scripts/verify_formatting.py` — Verify formatting, list shapes, check captions
- `scripts/verify_pptx.py` — Verify PPTX text and formatting with safe color handling
- `references/emu-conversions.md` — EMU unit conversions and slide dimensions
- `references/pptx_xml_notes.md` — XML namespaces and structure for fallback editing
- `references/bullets-numbering.md` — Bullet and numbering patterns
