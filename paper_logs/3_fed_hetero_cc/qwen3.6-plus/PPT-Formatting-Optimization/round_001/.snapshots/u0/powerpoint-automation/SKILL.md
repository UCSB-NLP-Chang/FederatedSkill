---
name: powerpoint-automation
description: Programmatic manipulation of PowerPoint (.pptx) files using python-pptx. Use when tasks require batch formatting, text replacement, slide generation, layout adjustments, or adding auto-numbered lists to presentations.
---

# PowerPoint Automation with python-pptx

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

## Verification
Always verify at the XML attribute level, not just file existence or "does it open."

1. **Re-open the saved `.pptx`** and inspect shapes/XML to confirm changes.
2. **For formatting changes**, verify specific attributes:
   - Font size: `a:rPr/@sz` (hundredths of a point, e.g., 1500 = 15pt)
   - Bold: `a:rPr/@b` (1 = on, 0 = off)
   - Color: `a:solidFill/a:srgbClr/@val` (6-digit hex, no #)
   - Font family: `a:latin/@typeface`
3. **For positioning**, verify `a:xfrm/a:off/@x` and `a:xfrm/a:off/@y` in EMUs.
4. **For bullets**, verify `<a:buAutoNum>` exists in the slide XML.

Use `scripts/verify_pptx.py` to check formatting at the attribute level.

## Anti-Patterns
- Do not assume all shapes contain text frames. Check `shape.has_text_frame`.
- Do not rely on `shape.name` being unique or human-readable.
- Avoid hardcoding EMU values; use `Inches()` or `Pt()` for readability.
- Do not verify only at file-level (e.g., "does it open"); verify specific XML attributes.

## Known invariants (by sub-task)
(Round 0 — no sub-task-specific invariants identified yet. Will update as evidence emerges.)

## References
- `references/auto-numbered-bullets.md` — Auto-numbering XML injection patterns and type values
- `references/pptx-xml-schema.md` — EMU conversion table, XML structure, attribute reference
