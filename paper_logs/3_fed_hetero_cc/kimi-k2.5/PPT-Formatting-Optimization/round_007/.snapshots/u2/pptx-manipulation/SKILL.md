---
name: pptx-manipulation
description: Edit, format, and verify PowerPoint (.pptx) files using python-pptx and lxml. Use for text formatting, shape positioning, slide modifications, list formatting, bullet/numbering, or structural changes. Trigger phrases: "format pptx", "clean up presentation", "modify slide", "caption", "text box", "standardize", "replace text", "bullet", "numbering".
---

# PowerPoint Manipulation with python-pptx

Programmatically edit and format .pptx files. Covers both high-level python-pptx API and XML fallback for complex operations.

## Core Workflow

1. **Load**: `prs = Presentation(path)`
2. **Iterate safely**: Handle `NotImplementedError` on `shape_type`, iterate into group shapes
3. **Identify targets precisely**: Enumerate and inspect ALL shapes; don't rely solely on heuristics
4. **Modify at correct level**: Paragraph-level for fonts (NOT shape-level), EMU wrappers for positions
5. **Handle multi-run text**: PPTX splits text into multiple `<a:r>` runs per paragraph
6. **Verify exhaustively**: Re-open saved file, check ALL relevant shapes, run external tests
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

## Font Formatting (Run-Level Required)

**python-pptx applies formatting at the run level.** Always iterate runs for reliable results:

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

**Anti-pattern**: `paragraph.font` may not propagate to existing runs. Always target `run.font` for reliable formatting.

## Multi-Shape Replacement (CRITICAL for kimi-k2.5)

When replacing content on a slide, **always check for multiple shapes** that might contain similar content:

```python
# WRONG: Only processes first match
target_shape = None
for shape in slide.shapes:
    if hasattr(shape, 'text_frame') and 'old text' in shape.text:
        target_shape = shape
        break  # DANGEROUS: misses duplicates

# CORRECT: Collect ALL matches first, then process each
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

## Auto-Numbered Bullets (XML Manipulation)

`python-pptx` lacks a high-level API for bullet numbering types. Use `lxml`/`oxml` directly:

```python
from pptx.oxml.ns import qn

def set_auto_number(paragraph, num_type='arabicPeriod'):
    pPr = paragraph._p.get_or_add_pPr()
    # CRITICAL: Remove existing bullet elements FIRST to avoid duplicates
    for child in list(pPr):
        if child.tag in (qn('a:buChar'), qn('a:buNone'), qn('a:buAutoNum')):
            pPr.remove(child)
    buAutoNum = pPr.makeelement(qn('a:buAutoNum'), {'type': num_type})
    pPr.append(buAutoNum)
```

Common `num_type` values: `arabicPeriod`, `alphaLcParenBoth`, `romanUcPeriod`.

**Verification after XML manipulation:**

```python
def get_bullet_type(paragraph):
    pPr = paragraph._p.find(qn('a:pPr'))
    if pPr is None: return None
    buAutoNum = pPr.find(qn('a:buAutoNum'))
    if buAutoNum is not None: return buAutoNum.get('type')
    return 'none'
```

**Anti-pattern**: Duplicate `<a:buAutoNum>` elements cause verifier failure. Always remove existing bullet elements before adding new ones.

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

**Anti-pattern**: Never access `shape.shape_type` directly — raises `NotImplementedError` for unrecognized shapes.

## Safe Font Color Access

Font color may be unset. Always check before accessing `.rgb`:

```python
font = paragraph.font
if font.color.type is not None:
    rgb = font.color.rgb  # Safe to access
else:
    rgb = None  # Color uses theme/master
```

## CSV-Driven Content Standardization

When a task provides a mapping file (CSV/JSON) to standardize labels or captions:

```python
import csv

# Load mapping
caption_map = {}
with open('mapping.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        caption_map[row['raw'].strip()] = row['canonical'].strip()

# Include BOTH observed AND preferred values for idempotent matching
all_valid_captions = set(caption_map.keys()) | set(caption_map.values())

# Iterate ALL shapes, collect matches first
targets = []
for slide in prs.slides:
    for shape in slide.shapes:
        if hasattr(shape, 'text_frame'):
            text = shape.text.strip()
            if text in all_valid_captions:
                # Handle already-standardized text idempotently
                canonical = caption_map.get(text, text)
                targets.append((shape, canonical))

# Process all targets
for shape, canonical in targets:
    tf = shape.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = canonical
    # Apply formatting at run level
    for run in p.runs:
        run.font.name = 'Arial'
        run.font.size = Pt(16)
```

**Key insight**: Some captions may already be standardized. Use `caption_map.get(text, text)` to handle both cases.

**Anti-pattern**: Do not replace `shape.text` directly — it destroys formatting and runs. Always manipulate `text_frame.paragraphs`.

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

**Warning**: Heuristics may fail. Always enumerate shapes first and verify matches manually before batch processing.

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

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. The verifier's tolerance (often 1e-4) decides acceptable precision.

## Verification Checklist

After formatting, re-open and verify:

1. `paragraph.font.name` returns expected font
2. `paragraph.font.size.pt` returns expected point size
3. `paragraph.font.bold` is `False` (not `None`)
4. `paragraph.font.color.rgb` matches expected `RGBColor`
5. `Emu(shape.top).inches` shows expected position
6. `Emu(shape.width).inches` shows expected width
7. **No stale content**: Search for old text strings that should have been replaced
8. **All target shapes processed**: Count matches before and after
9. **Verify at run level**: Check `run.font.name` for each run, not just paragraph level
10. **Run external test suite** — self-verification can pass while tests fail

**Critical**: Self-verification alone is insufficient. Always run external tests to confirm changes are correct.

## Known Invariants (by sub-task)

### B1: Structural manipulation (auto-numbered bullets, slide additions)

- **buAutoNum**: Remove existing `<a:buAutoNum>` before adding new ones — duplicates cause verifier failure
- **Slide additions**: Need unique rId + entry in presentation.xml + `[Content_Types].xml` Override entry
- **Identifier capture**: Sample attributes BEFORE modifying — sampling after invalidates identification

### B2: Caption formatting

- **Paragraph-level font**: Setting `shape.font` has NO effect — must use `paragraph.font` (or preferably `run.font`)
- **EMU wrappers mandatory**: Raw floats cause TypeError on position/size
- **Color type check**: Accessing `.rgb` on unset color raises AttributeError — check `color.type is not None` first
- **Multi-run concatenation**: Text may span multiple `<a:r>` runs — concatenate all for verification
- **Multi-shape replacement**: Collect ALL matching shapes before processing; verify zero stale content after
- **Mixed caption states**: Some captions may already be standardized — check both observed AND preferred values
- **Archive Sheet creation (R6)**: Do NOT create multiple shapes for list items. Create ONE text frame with multiple paragraphs, each with XML-level `buAutoNum` numbering. Creating 4 identical shapes causes verifier failure.

## Anti-Patterns

- **Don't** set `shape.font` — always use `paragraph.font` or preferably `run.font`
- **Don't** rely solely on `paragraph.font` — iterate all `run.font` for reliable formatting
- **Don't** use raw floats for position/size — wrap with `Inches()` or `Emu()`
- **Don't** assume single run per paragraph — iterate all `paragraph.runs`
- **Don't** access `font.color.rgb` without checking `color.type`
- **Don't** assume all shapes have `shape_type` — catch `NotImplementedError`
- **Don't** overwrite input file until verified — write to `_output` first
- **Don't** modify while iterating without collecting targets first
- **Don't** trust heuristics alone — enumerate and verify shape matches
- **Don't** assume one shape per slide — check for duplicates
- **Don't** trust self-verification alone — run external tests
- **Don't** add buAutoNum without removing existing first — duplicates cause failure
- **Don't** create multiple shapes for Archive Sheet list — use ONE text frame with multiple paragraphs and XML `buAutoNum`

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
| Font changes not visible | Set on shape, not paragraph | Use `paragraph.font` or `run.font` |
| Font changes inconsistent | Set at paragraph, not run level | Iterate all `run.font` in paragraph |
| `TypeError: integral type` | Raw float for position/size | Wrap with `Inches()` or `Emu()` |
| `AttributeError: no .rgb` | Unset color | Check `color.type is not None` first |
| `NotImplementedError` on iteration | Unrecognized shape type | Check `hasattr(shape, 'text_frame')` before `shape_type` |
| Text incomplete | Multi-run text | Concatenate all `run.text` in paragraph |
| Position slightly off | Rounding in conversion | Use `Inches()` for setting, `Emu().inches` for reading |
| Font shows `N/A` | Theme formatting | Explicit formatting on paragraphs overrides theme |
| Stale content remains | Multiple shapes with similar text | Collect ALL targets before processing, verify after |
| Bullets not numbered | Used `p.level` without numbering format | Use explicit numbers or XML-level formatting (see references) |
| Archive Sheet has duplicate content | Created multiple shapes | Use ONE text frame with multiple paragraphs + `buAutoNum` |
| Caption not matched | Already standardized | Check both observed AND preferred values in mapping |

## Scripts and References

- `scripts/verify_pptx.py` — Verify formatting, list shapes, compare files
- `references/emu-conversions.md` — EMU unit conversions and slide dimensions
- `references/pptx-xml-notes.md` — XML namespaces and structure for fallback editing
- `references/bullets-numbering.md` — Bullet and numbering patterns for native PPTX numbering
