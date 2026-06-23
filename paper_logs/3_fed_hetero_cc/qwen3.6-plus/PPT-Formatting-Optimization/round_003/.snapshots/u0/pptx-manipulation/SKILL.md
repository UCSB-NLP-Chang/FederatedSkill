---
name: pptx-manipulation
description: Programmatically read and modify PowerPoint (.pptx) files via python-pptx or direct XML manipulation. Use for formatting, positioning, slide generation, text replacement, or structural changes with verification at the attribute level.
---

# PowerPoint Manipulation

## Environment Setup
- Always use a virtual environment: `python3 -m venv .venv && .venv/bin/pip install python-pptx lxml`.
- Do not use `pip install` system-wide (PEP 668 restrictions will fail).

## Safe Inspection Workflow
1. Load presentation: `prs = Presentation(path)`
2. Iterate slides and shapes. Wrap property access in try/except or check for `None`.
3. **Critical**: `run.font.color.rgb` raises `AttributeError` if no color is set. Always check `run.font.color.type` or use `try/except`.
4. Use `scripts/inspect_pptx.py` to safely dump structure, text, and formatting without crashing on missing properties.

## Formatting & Layout
- Use `pptx.util.Inches`, `Pt`, `Emu` for all dimensions.
- To center text in a text frame: `tf.paragraphs[0].alignment = PP_ALIGN.CENTER`
- To change font: set `run.font.name`, `run.font.size`, `run.font.color.rgb`, `run.font.bold`.
- Reposition shapes by modifying `shape.left`, `shape.top`, `shape.width`, `shape.height`.

## Auto-Numbered Bullets (XML Injection)
`python-pptx` does not natively support auto-numbering. Inject XML into paragraph properties:
```python
from lxml import etree
from pptx.oxml.ns import qn

def add_auto_number(paragraph, num_type="arabicPeriod"):
    pPr = paragraph._p.get_or_add_pPr()
    buAutoNum = etree.SubElement(pPr, qn('a:buAutoNum'))
    buAutoNum.set('type', num_type)
```
See `references/auto-numbered-bullets.md` for complete examples and type values.

## Adding Slides (Critical Path)
When adding new slides, **5 coordinated changes are required**. Missing any step corrupts the file or causes the slide to be ignored. See `references/adding-slides.md` for the full workflow.

**Mandatory addition to `[Content_Types].xml`:**
```xml
<Override PartName="/ppt/slides/slide7.xml"
          ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
```
Failure to register the content type results in:
- Office applications ignoring the new slide
- "PowerPoint found a problem with content" errors
- Verifier failures even when XML appears correct

## XML Manipulation Warning
Python's built-in `xml.etree.ElementTree` **cannot register namespace prefixes** 'a', 'p', 'r', or 's' — these are reserved for internal use. Attempting `ET.register_namespace('a', uri)` raises `ValueError`.

Workarounds:
- Use `lxml.etree` instead of ElementTree (supports any prefix)
- Use regex-based string manipulation for simple edits
- Accept auto-generated prefixes like `ns0:`, `ns1:` in output

## lxml Namespace-Qualified Attributes
When setting attributes with namespace prefixes (e.g., `r:id`, `a:blip`) in lxml, **do not use the raw string** — lxml will raise `ValueError: Invalid attribute name`.

**Correct pattern:**
```python
from lxml import etree
from pptx.oxml.ns import qn

# WRONG: raises ValueError
# element.set('r:id', 'rId12')

# CORRECT: use qn() to get the fully-qualified name
element.set(qn('r:id'), 'rId12')
```

This applies to all prefixed attributes: `r:id`, `a:blip`, `p:sp`, etc. The `qn()` helper from `pptx.oxml.ns` returns the Clark notation `{namespace}localname` that lxml expects.

## python-pptx Dimension Persistence Bug
`python-pptx` sometimes **fails to persist shape dimension changes** (`shape.width`, `shape.height`, `shape.left`, `shape.top`) to the saved file. The XML shows `w="0"` or missing `<a:ext>` elements even after assignment.

**Detection**: After saving, extract and check XML. If `<a:off>` or `<a:ext>` are missing or zero, python-pptx did not persist the change.

**Fallback**: Modify the XML directly using lxml:
```python
from lxml import etree
from pptx.oxml.ns import qn

# Find the shape's spPr element
spPr = shape._element.find(qn('p:spPr'))
xfrm = spPr.find(qn('a:xfrm'))

# Set position
off = xfrm.find(qn('a:off'))
if off is None:
    off = etree.SubElement(xfrm, qn('a:off'))
off.set('x', str(left_emu))
off.set('y', str(top_emu))

# Set size
ext = xfrm.find(qn('a:ext'))
if ext is None:
    ext = etree.SubElement(xfrm, qn('a:ext'))
ext.set('cx', str(width_emu))
ext.set('cy', str(height_emu))
```

**Decision rule**: If you need precise positioning or sizing and python-pptx assignment doesn't work after save, switch to direct XML manipulation of `<a:xfrm>` elements immediately rather than debugging python-pptx internals.

## Verification
Always verify at the XML attribute level, not just file existence or "does it open."

1. **Content types**: Verify all slides registered in `[Content_Types].xml`
2. **Re-open the saved `.pptx`** and inspect shapes/XML to confirm changes.
3. **For formatting changes**, verify specific attributes:
   - Font size: `a:rPr/@sz` (hundredths of a point, e.g., 1500 = 15pt)
   - Bold: `a:rPr/@b` (1 = on, 0 = off)
   - Color: `a:solidFill/a:srgbClr/@val` (6-digit hex, no #)
   - Font family: `a:latin/@typeface`
4. **For positioning**, verify `a:xfrm/a:off/@x` and `a:xfrm/a:off/@y` in EMUs.
5. **For bullets**, verify `<a:buAutoNum>` exists in the slide XML.

Use `scripts/verify_pptx.py` to check formatting and content types at the attribute level.

## Anti-Patterns
- Do not assume all shapes contain text frames. Check `shape.has_text_frame`.
- Do not rely on `shape.name` being unique or human-readable — match by text content, position, or placeholder type instead.
- Avoid hardcoding EMU values; use `Inches()` or `Pt()` for readability.
- Do not verify only at file-level (e.g., "does it open"); verify specific XML attributes.
- Do not add new slides without updating `[Content_Types].xml` — the file will fail validation.
- Do not use `ElementTree.register_namespace()` with 'a', 'p', 'r' prefixes — will raise ValueError.
- Do not use raw strings like `'r:id'` in `element.set()` with lxml — use `qn('r:id')`.
- Do not trust python-pptx dimension assignments without XML verification — fall back to lxml if dimensions show as 0.

## Known invariants (by sub-task)
### PPTX slide addition
- New slides MUST be registered in `[Content_Types].xml` with an `<Override>` entry. (R1 u2: verifier flagged missing content type — slide ignored.)
- rId values must be unique — always check existing relationships before adding. (R0/R1 common failure.)
- PartName in `[Content_Types].xml` must have leading `/` — `/ppt/slides/slide4.xml`, not `ppt/slides/slide4.xml`.

### PPTX text formatting
- Font size in `a:rPr/@sz` is hundredths of a point (1500 = 15pt), not points.
- `run.font.color.rgb` crashes when `color.type` is unset — always guard with try/except.

### Auto-numbered bullets
- Only the first `<a:buAutoNum>` should specify `startAt`; omit it on subsequent paragraphs or every item restarts at "1.". (R2 u1)

## References
- `references/auto-numbered-bullets.md` — Auto-numbering XML injection patterns and type values
- `references/pptx-xml-schema.md` — EMU conversion table, XML structure, attribute reference
- `references/adding-slides.md` — 5-step workflow for adding slides with rId and content type management
