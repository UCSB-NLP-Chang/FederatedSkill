---
name: pptx-caption-standardization
description: Standardize and format captions in PowerPoint presentations with precise positioning, font consistency, and single-line width fitting. Use when tasks require multiple caption updates with consistent formatting, bottom-center positioning, specific font/size/color requirements, or ensuring captions fit on single lines without wrapping.
---

# PPTX Caption Standardization

Systematic caption formatting for multi-slide PowerPoint presentations.

## When to Use

- Multiple slides need consistent caption formatting
- Captions must be repositioned (e.g., bottom-center)
- Font, size, color standardization required across captions
- Captions must fit on single lines (auto-width calculation)
- Duplicate caption shapes exist and must be deduplicated
- Evidence logs or numbered lists need generation from caption data

## Core Workflow

### 1. Analyze Structure

Extract and identify caption shapes by name pattern:

```python
import zipfile, re, os

zipfile.ZipFile('input.pptx').extractall('/tmp/pptx_work')

def find_captions(slide_file):
    with open(slide_file) as f:
        content = f.read()
    # Match shapes with Chinese "文本框" (text box) pattern
    shapes = re.findall(r'<p:sp>.*?</p:sp>', content, re.DOTALL)
    captions = []
    for shape in shapes:
        if '文本框' in shape or 'caption' in shape.lower():
            texts = re.findall(r'<a:t>([^<]+)</a:t>', shape)
            if texts:
                captions.append({'xml': shape, 'texts': texts})
    return captions
```

### 2. Calculate Text Width (EMU-based Heuristics)

For single-line captions, estimate width per character:

| Font/Size | EMUs per char | Formula |
|-----------|---------------|---------|
| 14pt Arial | ~80,000-100,000 | `len(text) * 90000` |
| 16pt Arial | ~90,000-110,000 | `len(text) * 100000` |
| 12pt Calibri | ~70,000-85,000 | `len(text) * 80000` |

Safe estimate for mixed content: `len(text) * 100000` EMUs minimum.

```python
def estimate_width(text, font_size_pt=14, safety_factor=1.2):
    """Estimate EMU width for single-line text."""
    base_emus_per_char = {12: 80000, 14: 90000, 16: 100000, 18: 110000}
    base = base_emus_per_char.get(font_size_pt, 90000)
    return int(len(text) * base * safety_factor)
```

### 3. Standardize Position (Bottom-Center)

Standard slide: 12192000 × 6858000 EMUs

```python
def bottom_center_position(text_width, margin_bottom=Inches(0.75)):
    slide_width = 12192000
    slide_height = 6858000
    
    x = (slide_width - text_width) // 2
    y = slide_height - margin_bottom - height  # height ~360000 for single line
    return int(x), int(y)
```

### 4. Apply Formatting via Regex

Update or create caption XML with consistent formatting:

```python
def format_caption_xml(shape_xml, new_text, font='Arial', size_pt=14, 
                       color='6B7280', bold=False, italic=False):
    """Apply standard formatting to caption shape XML."""
    # Update text content
    xml = re.sub(r'<a:t>[^<]*</a:t>', f'<a:t>{new_text}</a:t>', shape_xml)
    
    # Update or create rPr element with full formatting
    size_hundredths = size_pt * 100
    bold_attr = ' b="1"' if bold else ''
    italic_attr = ' i="1"' if italic else ''
    
    rpr_pattern = r'<a:rPr[^/]*/>'
    new_rpr = (f'<a:rPr lang="en-US" sz="{size_hundredths}"{bold_attr}{italic_attr}>'
               f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
               f'<a:latin typeface="{font}"/><a:ea typeface="{font}"/><a:cs typeface="{font}"/></a:rPr>')
    
    if re.search(rpr_pattern, xml):
        xml = re.sub(rpr_pattern, new_rpr, xml)
    else:
        # Insert after <a:r> opening
        xml = re.sub(r'(<a:r>)(<a:t>)', r'\1' + new_rpr + r'\2', xml)
    
    # Center align paragraph
    xml = re.sub(r'<a:pPr[^>]*/>', '<a:pPr algn="ctr"/>', xml)
    if '<a:pPr' not in xml:
        xml = re.sub(r'(<a:p>)(<a:r>)', r'\1<a:pPr algn="ctr"/>\2', xml)
    
    return xml
```

### 5. Handle Duplicate Caption Shapes

Critical: Some slides have OLD and NEW caption shapes. Preserve content placeholders, remove only duplicate captions.

```python
def deduplicate_captions(slide_content, caption_patterns):
    """
    Remove old caption shapes, keep new formatted ones.
    caption_patterns: list of regex patterns identifying captions to KEEP
    """
    # Find all shapes
    shapes = re.findall(r'<p:sp>.*?</p:sp>', slide_content, re.DOTALL)
    
    shapes_to_keep = []
    for shape in shapes:
        is_placeholder = '<p:ph ' in shape  # Content placeholders have <p:ph>
        texts = re.findall(r'<a:t>([^<]+)</a:t>', shape)
        text = ' '.join(texts)
        
        # Keep placeholders always
        if is_placeholder:
            shapes_to_keep.append(shape)
            continue
            
        # Check if this is a caption we want to keep
        keep = any(re.search(p, text, re.I) for p in caption_patterns)
        if keep or not any(c in text.lower() for c in ['camera', 'badge', 'elevator', 'stairwell']):
            shapes_to_keep.append(shape)
        # else: skip (remove old caption)
    
    # Rebuild spTree with kept shapes only
    return rebuild_spTree(slide_content, shapes_to_keep)
```

### 6. Update Position and Size

```python
def update_position(shape_xml, x, y, width, height=360000):
    """Update xfrm position and size."""
    # Replace or insert xfrm
    xfrm_pattern = r'<a:xfrm>.*?</a:xfrm>'
    new_xfrm = f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{width}" cy="{height}"/></a:xfrm>'
    
    if re.search(xfrm_pattern, shape_xml, re.DOTALL):
        return re.sub(xfrm_pattern, new_xfrm, shape_xml, flags=re.DOTALL)
    else:
        # Insert before prstGeom
        return re.sub(r'(<a:prstGeom)', new_xfrm + r'\1', shape_xml)
```

## Verification Checklist

After each slide modification, verify:

| Check | Method |
|-------|--------|
| Caption text correct | `grep '<a:t>EXPECTED</a:t>' slide.xml` |
| Font applied | `grep 'typeface="Arial"'` |
| Size correct | `grep 'sz="1400"'` (14pt = 1400) |
| Color correct | `grep 'val="6B7280"'` |
| Bold off | `grep -v 'b="1"'` or verify not present |
| Position bottom | `grep 'y="6000000"'` or similar |
| Single shape per caption | Count `<p:sp>.*caption-ish.*</p:sp>` patterns |
| Content preserved | Verify placeholders still have text |

### Quick Verification Script

```python
def verify_slide(slide_file, expected_caption, expected_font='Arial', 
                 expected_size=1400, expected_color='6B7280'):
    with open(slide_file) as f:
        content = f.read()
    
    issues = []
    
    # Check caption text
    if expected_caption not in content:
        issues.append(f"Caption '{expected_caption}' not found")
    
    # Find caption shape and check formatting
    shapes = re.findall(r'<p:sp>.*?</p:sp>', content, re.DOTALL)
    caption_shapes = [s for s in shapes if expected_caption in s]
    
    if len(caption_shapes) != 1:
        issues.append(f"Found {len(caption_shapes)} caption shapes, expected 1")
    
    if caption_shapes:
        cap = caption_shapes[0]
        if f'typeface="{expected_font}"' not in cap:
            issues.append(f"Font not {expected_font}")
        if f'sz="{expected_size}"' not in cap:
            issues.append(f"Size not {expected_size}")
        if f'val="{expected_color}"' not in cap:
            issues.append(f"Color not {expected_color}")
        if 'b="1"' in cap:
            issues.append("Bold should be off")
    
    return issues
```

## Anti-Patterns

- **Don't** use `python-pptx` for precise caption positioning — it lacks pixel-perfect control
- **Don't** assume text width — always calculate based on content length
- **Don't** modify all shapes named "文本框" — filter by content to avoid breaking UI elements
- **Don't** trust visual verification alone — always grep the XML
- **Don't** remove shapes by index — use text/content matching to identify duplicates
- **Don't** set width too narrow — captions will wrap; use `len(text) * 100000` minimum
- **Don't** forget to update ALL font family attributes: `<a:latin>`, `<a:ea>`, `<a:cs>`

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Caption wraps to two lines | Width too narrow | Increase cx by 20% or use `len(text) * 110000` |
| Old caption still visible | Duplicate shape not removed | Check for multiple shapes with similar text |
| Content placeholder lost | Accidentally removed | Always check `<p:ph` before removing shapes |
| Font not applied | Only updated `<a:latin>` | Must update `ea` and `cs` typefaces too |
| Size verification fails | sz attribute in wrong place | Ensure sz is in `<a:rPr>` not `<a:pPr>` |
| Position off-center | Integer division truncation | Use `//` for center calculation, verify x is int |

## Evidence Log Generation

Generate numbered lists from processed captions:

```python
def generate_evidence_log(ordered_captions, slide_file):
    """
    Replace slide content with auto-numbered list.
    ordered_captions: list of caption strings in display order
    """
    # Build numbered paragraphs XML
    paras = []
    for i, caption in enumerate(ordered_captions, 1):
        para = (f'<a:p><a:pPr><a:buAutoNum type="arabicPeriod"/></a:pPr>'
                f'<a:r><a:rPr lang="en-US"/><a:t>{caption}</a:t></a:r></a:p>')
        paras.append(para)
    
    # Replace existing paragraphs in content placeholder
    # Preserve placeholder structure, replace inner content
    return paras
```

## References

- EMU calculations: `../pptx-xml-manipulation/references/emu-calculations.md`
- Validation script: `scripts/verify_captions.py` — run after modifications
