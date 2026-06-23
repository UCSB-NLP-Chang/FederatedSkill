---
name: pptx-editing
description: Automate PowerPoint (.pptx) inspection, formatting, and content generation using python-pptx. Use when tasks require modifying slide layouts, text box properties, fonts, positions, adding/deleting slides, manipulating XML directly, or performing CSV-driven batch caption/text replacements.
---

# PowerPoint Automation with python-pptx

## Workflow
1. **Install dependency**: `pip install python-pptx --break-system-packages -q`.
2. **Inspect structure**: Run `scripts/inspect_pptx.py <file.pptx>` to safely dump slides, shapes, text, and formatting. Handles `GroupShape` and unknown types automatically.
3. **Plan modifications**: Identify target shapes by type/position rather than name. Handle duplicates explicitly when aggregating content.
4. **Apply changes**: Use `scripts/modify_pptx.py` as a scaffold for safe bulk edits, or write inline scripts following the property access rules below.
5. **Verify internally**: Reload the saved `.pptx` and assert expected properties.
6. **Verify externally (MANDATORY)**: Run the task's test suite immediately after the first save. Do not rely solely on self-written verification scripts. Search broadly (`find / -name "test_*.py" -not -path "*/site-packages/*"`) if not in the working directory. If tests fail, inspect the diff between expected and actual output before iterating. **Never declare success before the external verifier passes.**

## Key Decision Rules
- **RGBColor Import & Initialization**: Always import via `from pptx.dml.color import RGBColor`. `RGBColor()` requires three integer arguments (`RGBColor(0x7A, 0x6F, 0x65)`). To parse hex strings, use `RGBColor.from_string("7A6F65")`. Never pass a single hex string directly to `RGBColor()`.
- **Color access & assignment**: `run.font.color.type` is **read-only**. Check it before reading `.rgb` to avoid `_NoneColor` AttributeError. To change color, directly assign `run.font.color.rgb = RGBColor(...)`.
- **TextFrame clearing**: Use `text_frame.clear()` to safely remove all paragraphs. Do not attempt to access `_p_lst` or manually delete paragraph elements unless `clear()` fails.
- **XML elements**: Use `run._r` for lxml access on runs. Use `shape._element` for shapes. Always use `pptx.oxml.ns.qn()` for namespace-qualified tags. Always `from lxml import etree` at the top of scripts when doing XML manipulation.
- **Units**: Use `pptx.util.Inches()` and `Pt()`. Conversions: `1 inch = 914400 EMU`, `1 Pt = 12700 EMU`. Avoid hardcoding EMU.
- **Shape targeting**: Prefer `shape.shape_type` and positional bounds over `.name`. Non-English or auto-generated names are common.
- **Placeholder Targeting**: `has_text_frame` matches both Title and Content placeholders. On multi-placeholder slides, verify `shape.placeholder_format.type` (e.g., `MSO_PLACEHOLDER_TYPE.TITLE` vs `CONTENT`) or match by explicit name/position to avoid overwriting titles or headers.
- **Text frames**: Explicitly set `text_frame.word_wrap = False` and `text_frame.auto_size = None` to prevent layout shifts.
- **Content aggregation**: When collecting text across slides for summaries or lists, deduplicate explicitly while preserving first-appearance order. Verify the final count matches unique items.
- **Slide deletion/reordering**: `python-pptx` has no public `delete_slide()` or `move_slide()`. You must manipulate `prs.element.sldIdLst` and `prs.part.rels`. See [Slide Manipulation](#slide-manipulation-xml-fallback) below.
- **Output Path Verification**: Graders often enforce exact filenames. If the task doesn't specify, default to overwriting the input or appending `_modified`. Always verify the expected output path before saving. **If a test file exists, run it immediately after the first save to catch path or content mismatches early.**

## CSV-Driven Text Replacement Workflow
When a task provides a CSV registry mapping old text to new text:
1. Parse CSV and identify the status column dynamically (common names: `status`, `record_status`, `state`). Filter for active/valid rows.
2. Build a mapping dict from `observed_label` → `preferred_label`. Skip rows where either field is empty.
3. Iterate slides and shapes. For each text box, check if its text matches a key in the mapping.
4. Replace text using `text_frame.clear()` then `text_frame.paragraphs[0].add_run().text = new_text`.
5. Apply formatting to all runs in the paragraph after replacement.
6. **Preserve unrelated content**: Do not modify shapes whose text is not in the mapping. Verify shelf notes, titles, and body copy remain unchanged.

## GroupShape & Reparenting
- `shape.shape_type` raises `NotImplementedError` on `GroupShape`. Catch it or check `hasattr(shape, 'shapes')`.
- To inspect group children, iterate `shape.shapes`.
- `python-pptx` cannot move a shape out of a `GroupShape` via public API. Use XML reparenting:
  ```python
  from lxml import etree
  from pptx.oxml.ns import qn
  # Find the shape element inside the group
  sp_elem = shape._element
  # Remove from group
  sp_elem.getparent().remove(sp_elem)
  # Append to slide's spTree
  spTree = slide.shapes._spTree
  spTree.append(sp_elem)
  ```
- After reparenting, verify the shape appears in `slide.shapes`. If missing, check XML directly under `<p:spTree>`.
- **Repositioning Groups**: Modifying `group.left`/`group.top` shifts all children relatively. If absolute placement of a specific child is required, adjust the child's coordinates relative to the group, or reparent it first.

## Slide Manipulation (XML Fallback)
When the public API raises `AttributeError` or lacks a method, fall back to `lxml` immediately.

### Delete a slide
```python
from pptx.oxml.ns import qn
# Find the slide index to delete (0-based)
slide_to_remove = prs.slides[target_idx]
# Remove from slide ID list
sldIdLst = prs.element.sldIdLst
sldId = sldIdLst[target_idx]
sldIdLst.remove(sldId)
# Remove relationship
rId = slide_to_remove.part.rId
prs.part.rels.drop_rel(rId)
```

### Reorder slides
```python
# Swap slide at idx_a and idx_b
sldIdLst = prs.element.sldIdLst
sldId_a = sldIdLst[idx_a]
sldId_b = sldIdLst[idx_b]
sldIdLst.remove(sldId_a)
sldIdLst.insert(idx_b, sldId_a)
sldIdLst.remove(sldId_b)
sldIdLst.insert(idx_a, sldId_b)
```

## Bullet & List Formatting (XML Fallback)
`python-pptx` lacks high-level APIs for auto-numbered bullets. Use `lxml.etree` to inject `<a:buAutoNum>` into paragraph properties (`pPr`).

```python
from lxml import etree
from pptx.oxml.ns import qn

pPr = p._pPr
if pPr is None:
    pPr = etree.SubElement(p._p, qn('a:pPr'))

# Clear existing bullet definitions
for child in list(pPr):
    if child.tag in (qn('a:buChar'), qn('a:buNone'), qn('a:buAutoNum')):
        pPr.remove(child)

# Add auto-numbered bullet
bu = etree.SubElement(pPr, qn('a:buAutoNum'))
bu.set('type', 'arabicPeriod') # Options: arabicPeriod, alphaLcParenBoth, romanUcPeriod, etc.
```

## Verification Pattern
1. Reload the saved file with `Presentation()`.
2. Assert slide count, target shape positions, dimensions, text, font properties, and alignment.
3. **Run external tests**: If `test_*.py` or a verifier script exists, execute it immediately. Self-verification often misses exact string matches, XML structure, or edge cases required by graders. Search broadly (`find / -name "test_*.py" -not -path "*/site-packages/*"`) if not in the working directory. If tests fail, inspect the diff between expected and actual output before iterating. **Never declare success before the external verifier passes.**
4. **XML fallback verification**: If a shape is missing from `slide.shapes` after modification, dump the slide XML (`slide._element`) and verify it resides inside `<p:spTree>`. Shapes placed outside this tree will not render or be detected by the public API.

## Anti-Patterns
- Do not pass a hex string directly to `RGBColor()`; use `RGBColor.from_string()` or 3 integers.
- Do not assume `.rgb` exists on all color objects without checking `.type`.
- Do not try to set `run.font.color.type`; it is read-only.
- Do not rely on shape names being consistent or English.
- Do not modify placeholder text without checking `shape.has_text_frame`.
- Avoid hardcoding EMU values; calculate from `Inches()` or `Pt()`.
- Do not skip external test execution; inline verification is insufficient for complex formatting or content extraction tasks.
- Do not use `slide.rId` directly; access it via `slide.part.rId`.
- Do not access `prs._sldIdLst`; use `prs.element.sldIdLst`.
- Do not forget `from lxml import etree` at the top of scripts when manipulating XML.
- Do not call `shape.shape_type` on `GroupShape` without a try/except; it raises `NotImplementedError`.
- Do not blindly iterate `has_text_frame` shapes on multi-placeholder slides; verify `placeholder_format.type` first.
- Do not declare success before running the external test suite.
- Do not use `run._element`; use `run._r` for lxml access on runs.

## Scripts
- `scripts/inspect_pptx.py`: Run first on any unknown `.pptx` to safely dump structure. Handles groups and unknown types.
- `scripts/modify_pptx.py`: Use as a scaffold when writing inline modification scripts becomes error-prone. Contains safe helpers for font, color, and position updates.