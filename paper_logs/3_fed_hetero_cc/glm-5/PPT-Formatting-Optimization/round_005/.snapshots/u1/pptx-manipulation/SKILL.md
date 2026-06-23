---
name: pptx-manipulation
description: Edit, format, and verify PowerPoint (.pptx) files using python-pptx. Use when tasks require changing slide content, text formatting, shape properties, positioning, or adding slides while preserving existing elements. Covers both structural manipulation (B1) and caption formatting (B2).
---

# PowerPoint Manipulation & Verification

Unified skill for PPTX editing — combines structural manipulation, text formatting, and verification patterns.

## Core Workflow

1. **Load**: `prs = Presentation(path)`
2. **Iterate slides/shapes**: Handle groups via `shape.shapes`, skip shapes without `text_frame`
3. **Identify targets**: Use text content, position, or name — not indices
4. **Apply changes**: Always at paragraph level for fonts; EMU wrappers for position/size
5. **Save**: `prs.save(output_path)` — never overwrite input during iteration
6. **Verify**: Run `scripts/verify_formatting.py` to confirm changes

## Critical Implementation Details

### 1. Position and Size — EMU Wrappers Required

**Never use raw floats**. Always wrap with `Inches()`, `Emu()`, or `Pt()`:

```python
from pptx.util import Inches, Pt, Emu

# CORRECT
shape.left = Inches(0.5)
shape.top = Inches(6.6)
shape.width = Inches(10.0)

# WRONG — TypeError: value must be an integral type
shape.left = 0.5  # FAILS
shape.top = 6.6   # FAILS
```

### 2. Font Formatting — Paragraph Level Only

**Never set font on shape** — it has no effect. Always iterate paragraphs:

```python
from pptx.util import Pt
from pptx.dml.color import RGBColor

for paragraph in shape.text_frame.paragraphs:
    paragraph.font.name = 'Arial'
    paragraph.font.size = Pt(16)
    paragraph.font.bold = False
    paragraph.font.color.rgb = RGBColor(0x49, 0x60, 0x7A)
```

### 3. Safe Color Access

Font color may be unset. Check before accessing `.rgb`:

```python
font = paragraph.font
if font.color.type is not None:
    rgb = font.color.rgb  # Safe
else:
    rgb = None  # Color not set
```

### 4. Multi-run Text

PPTX splits text into `<a:r>` runs. **Never assume single run per paragraph**. Concatenate for verification:

```python
def get_full_text(paragraph):
    return "".join(run.text for run in paragraph.runs)
```

### 5. Safe Shape Iteration — NotImplementedError Guard

Some shapes throw `NotImplementedError` on `shape_type`:

```python
for shape in slide.shapes:
    if not hasattr(shape, 'text_frame'):
        continue
    # Safe to process text
    if hasattr(shape, 'shapes'):  # Group shape
        for nested in shape.shapes:
            if nested.has_text_frame:
                # Process nested shape
```

### 6. Caption Identification Heuristic

When distinguishing content captions from UI badges:

```python
def is_platform_caption(shape):
    if not hasattr(shape, 'text_frame'):
        return False
    text = shape.text.strip()
    return len(text) > 40 and shape.top > Inches(5)
```

| Characteristic | Caption | UI Element |
|---------------|---------|------------|
| Text length | > 40 chars | < 50 chars |
| Position | `top > Inches(5)` (lower) | `top < Inches(2)` (upper) |

## Verification Checklist

After modifications, verify:
1. Re-open file to confirm changes persisted
2. `paragraph.font.name` returns expected font
3. `paragraph.font.size.pt` returns expected point size
4. `paragraph.font.bold` is `False` (not `None`)
5. `Emu(shape.top).inches` shows expected position

Run `scripts/verify_formatting.py` for automated check.

## Known Invariants (by sub-task)

### B1: Structural manipulation (auto-numbered bullets, slide additions)

- **buAutoNum**: Remove existing `<a:buAutoNum>` before adding new ones — duplicates cause verifier failure (R3 u0)
- **Slide additions**: Need unique rId + entry in presentation.xml + `[Content_Types].xml` Override entry
- **Identifier capture**: Sample attributes BEFORE modifying — sampling after invalidates identification (R3 u2)
- **False-positive verification**: verify_pptx.py font size bug showed '1600pt' instead of '16pt' — fixed in R3. Always re-open file to verify.

### B2: Caption formatting

- **Paragraph-level font**: Setting `shape.font` has NO effect — must use `paragraph.font`
- **EMU wrappers mandatory**: Raw floats cause TypeError on position/size
- **Color type check**: Accessing `.rgb` on unset color raises AttributeError — check `color.type is not None` first
- **Multi-run concatenation**: Text may span multiple `<a:r>` runs — concatenate all for verification

## Anti-Patterns

- **Do NOT** use raw floats for position/size: `shape.left = 0.5` → TypeError
- **Do NOT** set `shape.font` directly — use `paragraph.font`
- **Do NOT** access `.rgb` without checking `color.type`
- **Do NOT** assume single run per paragraph — concatenate all runs
- **Do NOT** use `shape.shape_type` blindly — catch NotImplementedError or check attributes
- **Do NOT** rely on `shape.text` alone for formatting verification — inspect XML runs

## Fallback: Direct XML

If python-pptx fails on complex shapes:

```bash
unzip presentation.pptx -d pptx_extracted/
# Edit pptx_extracted/ppt/slides/slide1.xml
zip -r new_presentation.pptx pptx_extracted/
```

See `references/emu-conversions.md` for EMU values and `references/pptx_xml_notes.md` for namespace mappings.