---
name: archive-photo-caption-cleanup
description: Clean up and standardize photo/archive captions in PowerPoint presentations using a CSV registry. Use when task involves standardizing captions from a registry/mapping file, reformatting archive labels, creating summary/index slides with numbered lists, or processing museum/archive photo metadata. Triggers include "archive photo", "caption cleanup", "registry", "standardize labels", "photo review", "museum", "catalog".
---

# Archive Photo Caption Cleanup

Standardize archive/museum photo captions in PowerPoint using a CSV registry, then create or update formatted summary/index slides.

## Core Workflow

### 1. Load and Validate Registry

```python
import csv
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn

def load_caption_registry(csv_path):
    mappings = {}
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('Status', '').lower() == 'draft':
                continue
            raw = row.get('Raw Caption', '').strip()
            canonical = row.get('Standardized Label', '').strip()
            if raw and canonical:
                mappings[raw] = canonical
    return mappings
```

### 2. Identify Caption Shapes

Captions are typically:
- Long text (>40 characters)
- Positioned in lower half of slide (`top > Inches(5)`)
- Descriptive sentences about photo content

```python
def is_likely_caption(shape, min_chars=40, min_top_inches=5):
    if not hasattr(shape, 'text_frame'):
        return False
    text = shape.text.strip()
    if len(text) < min_chars:
        return False
    try:
        return Emu(shape.top).inches >= min_top_inches
    except (AttributeError, NotImplementedError):
        return False
```

### 3. Collect ALL Matching Shapes First

**Critical**: Never process while iterating. Collect targets first to avoid missing duplicates.

```python
def collect_caption_targets(prs, caption_map):
    targets = []  # [(slide_idx, shape, canonical_text), ...]
    seen_canonical = set()
    
    for slide_idx, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if not is_likely_caption(shape):
                continue
            text = shape.text.strip()
            if text in caption_map:
                canonical = caption_map[text]
                targets.append((slide_idx, shape, canonical))
                seen_canonical.add(canonical)
            elif text in caption_map.values():
                targets.append((slide_idx, shape, text))
                seen_canonical.add(text)
    
    return targets, sorted(seen_canonical)
```

### 4. Format Captions Consistently

```python
def format_caption(shape, text, font_name='Calibri', font_size=15, 
                   color_hex='6C665C', width_inches=4, left_inches=4.67):
    tf = shape.text_frame
    tf.clear()
    
    p = tf.paragraphs[0] if tf.paragraphs else tf.add_paragraph()
    p.text = text
    
    p.font.name = font_name
    p.font.size = Pt(font_size)
    p.font.bold = False
    p.font.italic = False
    p.font.color.rgb = RGBColor.from_string(color_hex)
    
    shape.width = Inches(width_inches)
    shape.left = Inches(left_inches)
```

### 5. Create or Update Summary/Index Slides

#### Creating New Archive Sheet (Numbered List)

**CRITICAL**: Use proper XML-level auto-numbering, NOT duplicate shapes.

```python
def add_archive_sheet(prs, canonical_items, title="Archive Sheet"):
    blank_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[-1]
    slide = prs.slides.add_slide(blank_layout)
    
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12), Inches(1))
    title_frame = title_box.text_frame
    title_frame.text = title
    title_frame.paragraphs[0].font.size = Pt(24)
    title_frame.paragraphs[0].font.bold = True
    
    list_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(12), Inches(5))
    tf = list_box.text_frame
    tf.clear()
    
    for i, item in enumerate(canonical_items, 1):
        p = tf.add_paragraph()
        p.text = item
        p.font.size = Pt(14)
        p.font.name = 'Calibri'
        _apply_auto_number(p, num_type='arabicPeriod')
    
    return slide

def _apply_auto_number(paragraph, num_type='arabicPeriod'):
    pPr = paragraph._p.get_or_add_pPr()
    for child in list(pPr):
        if child.tag in (qn('a:buChar'), qn('a:buNone'), qn('a:buAutoNum')):
            pPr.remove(child)
    buAutoNum = pPr.makeelement(qn('a:buAutoNum'), {'type': num_type})
    pPr.append(buAutoNum)
```

#### Updating Existing Index Slide (Replacing Placeholders)

**CRITICAL DIFFERENCE**: When REPLACING existing bullet content (not creating new), ensure you create SEPARATE paragraphs for each item.

```python
def replace_index_bullets(shape, items, font_name='Arial', font_size=14):
    """Replace ALL content of an index shape with separate bullets.
    
    COMMON FAILURE: Setting p.text to multi-line string creates ONE paragraph.
    MUST use add_paragraph() for each item.
    """
    tf = shape.text_frame
    tf.clear()
    
    for item in items:
        p = tf.add_paragraph()
        p.text = item
        p.font.name = font_name
        p.font.size = Pt(font_size)
        p.font.bold = False
        # Apply numbering if needed
        _apply_auto_number(p, num_type='arabicPeriod')
    
    return len(items)  # Return count for verification
```

### 6. Verify Exhaustively

```python
def verify_cleanup(output_path, expected_captions, expected_count):
    prs = Presentation(output_path)
    
    found_captions = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if not hasattr(shape, 'text_frame'):
                continue
            text = shape.text.strip()
            if text in expected_captions:
                found_captions.append(text)
                for p in shape.text_frame.paragraphs:
                    assert p.font.name == 'Calibri', f"Wrong font: {p.font.name}"
    
    archive_slides = [s for s in prs.slides 
                      if any('Archive Sheet' in sh.text for sh in s.shapes 
                             if hasattr(sh, 'text_frame'))]
    
    if archive_slides:
        archive_slide = archive_slides[0]
        list_shapes = [sh for sh in archive_slide.shapes 
                       if hasattr(sh, 'text_frame') and sh.text != 'Archive Sheet']
        assert len(list_shapes) == 1, "Should have ONE list shape"
    
    return True
```

## Critical Distinction: Creating vs Updating Index Slides

| Scenario | Approach | Common Failure |
|----------|----------|----------------|
| Create NEW Archive Sheet | `add_paragraph()` + XML numbering | Creating multiple shapes instead of one text frame |
| Update EXISTING index slide | Clear + `add_paragraph()` per item | Setting single paragraph text to multi-line string |

**When updating existing bullets**: Never do `p.text = "item1\nitem2\nitem3"` — this creates ONE paragraph. Always loop and call `add_paragraph()` for each item.

## Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
|-------------|--------------|------------------|
| Process shapes while iterating | Misses duplicates | Collect ALL targets first in a list |
| Create multiple shapes for list items | Duplicate content | ONE shape with multiple paragraphs |
| Set paragraph text with `\n` separators | Creates single paragraph with newlines | Use `add_paragraph()` for each item |
| Update index by clearing and setting single text | Loses bullet structure | Clear then add paragraphs in loop |

## Verification Checklist

After any index/summary slide operation:

1. **Count paragraphs**: `len(shape.text_frame.paragraphs)` should equal item count
2. **Check concatenated text**: `".join(p.text for p in paragraphs)` should not contain `\n`
3. **Verify numbering**: Each paragraph has `buAutoNum` element in XML
4. **No stale content**: Search for placeholder text that should have been replaced

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| All items on one line | Used `\n` in single paragraph text | Use `add_paragraph()` for each item |
| Wrong number of bullets | Paragraph count mismatch | Verify `len(paragraphs) == len(items)` |
| Numbering as plain text | Used explicit numbers instead of XML | Use `buAutoNum` XML element |

## References

See `../pptx-manipulation/` for general PPTX patterns (EMU, fonts, safe iteration).
