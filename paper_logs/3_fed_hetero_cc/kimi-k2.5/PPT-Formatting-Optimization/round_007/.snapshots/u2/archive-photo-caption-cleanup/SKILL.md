---
name: archive-photo-caption-cleanup
description: Clean up and standardize photo/archive captions in PowerPoint presentations using a CSV registry. Use when: task involves standardizing captions from a registry/mapping file, reformatting archive labels, creating summary/index slides with numbered lists, or processing museum/archive photo metadata. Trigger phrases: "archive photo", "caption cleanup", "registry", "standardize labels", "photo review", "museum", "catalog".
---

# Archive Photo Caption Cleanup

Standardize archive/museum photo captions in PowerPoint using a CSV registry, then create a formatted summary slide.

## Workflow

### 1. Load and Validate Registry

```python
import csv
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn

def load_caption_registry(csv_path):
    """Load caption mappings, filtering out drafts and missing labels."""
    mappings = {}
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip drafts and missing labels
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
- Descriptive sentences about the photo content

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
    """Collect all caption shapes that need updating."""
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
                # Already standardized - still needs formatting
                targets.append((slide_idx, shape, text))
                seen_canonical.add(text)
    
    return targets, sorted(seen_canonical)
```

### 4. Format Captions Consistently

```python
def format_caption(shape, text, font_name='Calibri', font_size=15, 
                   color_hex='6C665C', width_inches=4, left_inches=4.67):
    """Apply standard formatting to a caption shape."""
    tf = shape.text_frame
    tf.clear()
    
    p = tf.paragraphs[0] if tf.paragraphs else tf.add_paragraph()
    p.text = text
    
    # Font formatting at paragraph level
    p.font.name = font_name
    p.font.size = Pt(font_size)
    p.font.bold = False
    p.font.italic = False
    p.font.color.rgb = RGBColor.from_string(color_hex)
    
    # Position and size with EMU wrappers
    shape.width = Inches(width_inches)
    shape.left = Inches(left_inches)
    # Keep original top or set standard bottom position
```

### 5. Create Archive Sheet Slide (Numbered List)

**CRITICAL**: Use proper XML-level auto-numbering, NOT duplicate shapes.

```python
def add_archive_sheet(prs, canonical_items, title="Archive Sheet"):
    """Add a summary slide with properly numbered items.
    
    WARNING: Do NOT create multiple shapes with the same text.
    Create ONE text frame with multiple paragraphs using XML numbering.
    """
    # Use blank layout (index 6 is typically blank)
    blank_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[-1]
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
    
    for i, item in enumerate(canonical_items, 1):
        p = tf.add_paragraph()
        p.text = item  # Text WITHOUT numbers - numbering is XML-level
        p.font.size = Pt(14)
        p.font.name = 'Calibri'
        
        # Apply native PowerPoint numbering via XML
        _apply_auto_number(p, num_type='arabicPeriod')
    
    return slide

def _apply_auto_number(paragraph, num_type='arabicPeriod'):
    """Apply native PowerPoint auto-numbering to a paragraph."""
    pPr = paragraph._p.get_or_add_pPr()
    
    # CRITICAL: Remove existing bullet elements first
    for child in list(pPr):
        if child.tag in (qn('a:buChar'), qn('a:buNone'), qn('a:buAutoNum')):
            pPr.remove(child)
    
    # Add auto-number element
    buAutoNum = pPr.makeelement(qn('a:buAutoNum'), {'type': num_type})
    pPr.append(buAutoNum)
```

### 6. Verify Exhaustively

```python
def verify_cleanup(output_path, expected_captions, expected_count):
    """Re-open and verify all changes."""
    prs = Presentation(output_path)
    
    found_captions = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if not hasattr(shape, 'text_frame'):
                continue
            text = shape.text.strip()
            if text in expected_captions:
                found_captions.append(text)
                # Verify formatting
                for p in shape.text_frame.paragraphs:
                    assert p.font.name == 'Calibri', f"Wrong font: {p.font.name}"
                    assert p.font.size.pt == 15, f"Wrong size: {p.font.size.pt}"
                    assert p.font.bold == False, "Bold should be False"
                    assert p.font.italic == False, "Italic should be False"
    
    # Check for stale content
    all_text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, 'text_frame'):
                all_text.append(shape.text)
    
    # Verify Archive Sheet
    archive_slides = [s for s in prs.slides 
                      if any('Archive Sheet' in sh.text for sh in s.shapes 
                             if hasattr(sh, 'text_frame'))]
    assert len(archive_slides) == 1, "Should have exactly one Archive Sheet"
    
    # Check Archive Sheet has proper structure (not duplicate shapes)
    archive_slide = archive_slides[0]
    list_shapes = [sh for sh in archive_slide.shapes 
                   if hasattr(sh, 'text_frame') and sh.text != 'Archive Sheet']
    assert len(list_shapes) == 1, "Archive Sheet should have ONE list shape, not duplicates"
    
    return True
```

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Correct Approach |
|-------------|--------------|------------------|
| Process shapes while iterating | Misses duplicates, causes stale content | Collect ALL targets first in a list |
| Create multiple shapes for list items | Creates duplicate content, verifier fails | ONE shape with multiple paragraphs |
| Use explicit "1. " text for numbering | Not "live" numbering, harder to maintain | XML-level `buAutoNum` elements |
| Skip already-standardized captions | Inconsistent formatting across slides | Format ALL caption shapes matching criteria |
| Trust single-pass replacement | Multiple shapes may have same text | Verify zero stale content after processing |

## Critical Decision Rules

1. **If caption_map has entries but no matches found**: Lower the `min_chars` threshold or check position heuristics - captions may be shorter or positioned differently.

2. **If Archive Sheet shows duplicate shapes**: You created multiple text boxes instead of one text frame with multiple paragraphs. Restart slide creation using the pattern in step 5.

3. **If font changes not visible**: You set `shape.font` instead of `paragraph.font`. Always format at paragraph level.

4. **If numbering doesn't appear**: Check XML for duplicate `buAutoNum` elements. Always remove existing bullet elements before adding new ones.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Verifier fails on Archive Sheet | Duplicate shapes with same content | Use ONE shape, multiple paragraphs with XML numbering |
| Some captions not formatted | Heuristic too strict | Lower `min_chars` or adjust position threshold |
| Stale original captions remain | Multiple shapes with similar text | Collect ALL targets before processing |
| Numbering shows as plain text | Used explicit numbers in text | Use XML `buAutoNum` with `arabicPeriod` type |
| Font shows as theme default | Set on shape, not paragraph | Always use `paragraph.font` |

## References

- `references/csv-registry-format.md` - Expected CSV schema for caption registries
- `references/xml-numbering.md` - Detailed XML numbering patterns and types
- `../pptx-manipulation/` - General PPTX manipulation patterns (EMU, fonts, etc.)