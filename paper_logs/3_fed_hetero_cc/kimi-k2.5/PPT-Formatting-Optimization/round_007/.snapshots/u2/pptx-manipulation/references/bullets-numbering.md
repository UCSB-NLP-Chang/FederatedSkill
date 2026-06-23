# Bullets and Numbering in python-pptx

## The Challenge

PowerPoint's bullet and numbering system is complex:
- `python-pptx` provides limited high-level API for numbering
- True auto-numbering requires XML-level manipulation
- Simplest reliable approach: explicit numbering in text

## Option 1: Explicit Numbering (Recommended)

Most reliable for programmatic control:

```python
from pptx.util import Pt

def set_numbered_list(text_frame, items, font_name='Arial', font_size=Pt(14)):
    """Replace all content with explicitly numbered items."""
    tf = text_frame
    tf.clear()
    
    for i, item in enumerate(items, 1):
        p = tf.add_paragraph()
        p.text = f"{i}. {item}"
        p.font.name = font_name
        p.font.size = font_size
        # No bullet character - numbers are in text
```

**Pros**: Predictable, easy to verify, works with all PowerPoint versions
**Cons**: Numbers are text, not "live" numbering (won't auto-update if reordered)

## Option 2: Bullet Levels (Limited)

For simple bullets without numbers:

```python
from pptx.util import Pt

def set_bulleted_list(text_frame, items):
    tf = text_frame
    tf.clear()
    
    for i, item in enumerate(items):
        p = tf.add_paragraph()
        p.text = item
        p.level = 0  # First level bullet
        p.font.size = Pt(14)
```

**Note**: This creates bullets (o), not numbers. The `level` controls indentation only.

## Option 3: Native Numbering via XML

For true PowerPoint auto-numbering (1, 2, 3 that updates automatically):

```python
from pptx.oxml.ns import qn
from pptx.oxml import parse_xml

def apply_numbering(paragraph):
    """Apply native numbering to a paragraph via XML."""
    pPr = paragraph._p.get_or_add_pPr()
    
    # CRITICAL: Remove existing bullet elements FIRST
    for child in list(pPr):
        if child.tag in (qn('a:buChar'), qn('a:buNone'), qn('a:buAutoNum')):
            pPr.remove(child)
    
    # Check if numbering element exists
    numPr = pPr.find(qn('a:numPr'))
    if numPr is None:
        numPr = parse_xml(
            r'<a:numPr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            r'<a:buAutoNum type="arabicPeriod"/>'
            r'</a:numPr>'
        )
        pPr.append(numPr)
```

**Common `buAutoNum` types**:
- `arabicPeriod` - 1. 2. 3.
- `arabicParenR` - 1) 2) 3)
- `alphaLcPeriod` - a. b. c.
- `alphaUcPeriod` - A. B. C.
- `romanLcPeriod` - i. ii. iii.
- `romanUcPeriod` - I. II. III.

## Verification

Always verify the result by re-opening:

```python
from pptx import Presentation

prs = Presentation('output.pptx')
for slide in prs.slides:
    for shape in slide.shapes:
        if hasattr(shape, 'text_frame'):
            for p in shape.text_frame.paragraphs:
                print(f"Text: {p.text}")
                # Check for numbering in XML
                pPr = p._p.pPr
                if pPr is not None and pPr.numPr is not None:
                    print("  Has native numbering")
```

## Recommendation

Use **Option 1 (explicit numbering)** unless:
- User specifically requests live/auto-updating numbering
- You need multi-level outlines with automatic renumbering

Explicit numbering is simpler, more predictable, and easier to debug.
