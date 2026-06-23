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

## Known invariants (by sub-task)
### PPTX slide addition
- New slides MUST be registered in `[Content_Types].xml` with an `<Override>` entry. (R1 u2: verifier flagged missing content type — slide ignored.)
- rId values must be unique — always check existing relationships before adding. (R0/R1 common failure.)
- PartName in `[Content_Types].xml` must have leading `/` — `/ppt/slides/slide4.xml`, not `ppt/slides/slide4.xml`.

### PPTX text formatting
- Font size in `a:rPr/@sz` is hundredths of a point (1500 = 15pt), not points.
- `run.font.color.rgb` crashes when `color.type` is unset — always guard with try/except.

## References
- `references/auto-numbered-bullets.md` — Auto-numbering XML injection patterns and type values
- `references/pptx-xml-schema.md` — EMU conversion table, XML structure, attribute reference
- `references/adding-slides.md` — 5-step workflow for adding slides with rId and content type management
