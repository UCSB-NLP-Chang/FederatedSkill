---
name: pptx-manipulation
description: Programmatically read and modify PowerPoint (PPTX) files by manipulating the underlying XML structure. Use when you need to add/remove slides, modify text/formatting, or make bulk changes. Critical when adding new slides that must be registered in [Content_Types].xml.
---

# PPTX File Manipulation

## Overview
PPTX files are ZIP archives containing XML files. Direct XML manipulation is reliable for bulk changes, adding slides, or formatting operations.

## Key Structure
```
pptx_extracted/
├── [Content_Types].xml      # MIME type mappings for all content
├── _rels/.rels              # Root relationships
└── ppt/
    ├── presentation.xml     # Slide order (sldIdLst), slide size
    ├── _rels/
    │   └── presentation.xml.rels  # Slide relationships (rId mappings)
    ├── slides/
    │   ├── slide1.xml       # Slide content
    │   └── _rels/           # Per-slide relationships (images, layouts)
    ├── slideLayouts/
    └── slideMasters/
```

## Workflow

### 1. Extract the PPTX
```bash
unzip file.pptx -d pptx_extracted
# or: python3 scripts/extract_pptx.py file.pptx
```

### 2. Inspect existing relationships (CRITICAL)
Before adding slides, check which rIds are already used:
```bash
cat pptx_extracted/ppt/_rels/presentation.xml.rels
```
Relationship IDs (rId1, rId2, etc.) must be unique. Common mappings:
- rId1: slideMaster
- rId2-rId7: slides (typically)
- rId8+: presProps, viewProps, theme, tableStyles

### 3. Modify content
**Prefer regex-based string manipulation over ElementTree** for PPTX XML editing. See "XML Manipulation Approaches" below for critical limitations.

- Edit slide XML in `ppt/slides/slideN.xml`
- Text formatting: `<a:rPr>` elements (font, size, color, bold, italic)
- Position/size: `<p:spPr>` with `<a:xfrm>` containing `<a:off x="" y=""/>` and `<a:ext cx="" cy=""/>`
- Colors: `<a:solidFill><a:srgbClr val="6F6C64"/></a:solidFill>`

### 4. Add a new slide
Requires 5 coordinated changes:

a) Create `ppt/slides/slideN.xml` (copy from existing slide as template)

b) Create `ppt/slides/_rels/slideN.xml.rels` (link to slideLayout)

c) Add to `ppt/presentation.xml`:
```xml
<p:sldId id="260" r:id="rId12"/>
```
Use next available numeric id (256+) and unused rId.

d) Add to `ppt/_rels/presentation.xml.rels`:
```xml
<Relationship Id="rId12" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slideN.xml"/>
```

e) **Add to `[Content_Types].xml` (CRITICAL)**:
```xml
<Override PartName="/ppt/slides/slideN.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
```
Failure to register the content type results in Office ignoring the new slide or "problem with content" errors. See `references/adding-slides.md` for the complete workflow.

### 5. Repackage
```bash
cd pptx_extracted && zip -r ../output.pptx . && cd ..
```

### 6. Verify (ALWAYS run before finishing)
```bash
python3 scripts/verify_pptx.py output.pptx
```
Do not skip this step. It catches missing content types, duplicate rIds, and structural issues that cause silent failures.

## XML Manipulation Approaches

### Regex-Based (Recommended for most PPTX edits)
Use regex string manipulation when modifying PPTX XML. This avoids namespace registration issues and preserves the original XML structure.

```python
import re

# Read XML as string
with open(slide_path, 'r', encoding='utf-8') as f:
    xml_content = f.read()

# Modify using regex - be specific to avoid matching wrong elements
# Match textbox by position + content pattern
pattern = r'(<a:off x="2096000" y="6350000".*?<a:t>)([^<]+)(</a:t>)'
xml_content = re.sub(pattern, r'\1New Text\3', xml_content, flags=re.DOTALL)

# Write back
with open(slide_path, 'w', encoding='utf-8') as f:
    f.write(xml_content)
```

### ElementTree Limitation (CRITICAL)
Python's built-in `xml.etree.ElementTree` **cannot register namespace prefixes** 'a', 'p', 'r', or 's' - these are reserved for internal use. Attempting `ET.register_namespace('a', uri)` raises `ValueError: Prefix format reserved for internal use`.

Workarounds:
- Use regex-based string manipulation (simplest)
- Use `lxml.etree` instead of ElementTree (supports any prefix)
- Accept auto-generated prefixes like `ns0:`, `ns1:` in output

### lxml Namespace-Qualified Attributes
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

### Identifying Specific Textboxes
When a slide has multiple textboxes, match on multiple attributes to target the correct one:

1. **Position**: Match `<a:off x="..." y="...">` values
2. **Size**: Match `<a:ext cx="..." cy="...">` values
3. **Content pattern**: Match text content that uniquely identifies the textbox
4. **Textbox name**: Check `p:cNvPr name="..."` attribute

Example - find textbox at specific position:
```python
# Match shape at bottom-center position containing caption text
pattern = r'<a:off x="2096000" y="6350000".*?<a:t>([^<]+)</a:t>'
match = re.search(pattern, xml, re.DOTALL)
```

## Auto-Numbered Bullet Lists (CRITICAL)
When creating auto-numbered lists in PPTX XML, the `startAt` attribute on `<a:buAutoNum>` controls numbering restart behavior:

**Wrong** — every paragraph restarts at 1:
```xml
<a:pPr><a:buAutoNum type="arabicPeriod" startAt="1"/></a:pPr>  <!-- item shows as "1." -->
<a:pPr><a:buAutoNum type="arabicPeriod" startAt="1"/></a:pPr>  <!-- item also shows as "1." -->
```

**Correct** — only the first paragraph specifies `startAt`; subsequent paragraphs omit it to continue the sequence:
```xml
<a:pPr><a:buAutoNum type="arabicPeriod" startAt="1"/></a:pPr>  <!-- "1." -->
<a:pPr><a:buAutoNum type="arabicPeriod"/></a:pPr>              <!-- "2." -->
<a:pPr><a:buAutoNum type="arabicPeriod"/></a:pPr>              <!-- "3." -->
```

Or omit `startAt` entirely on all paragraphs — PowerPoint auto-sequences from 1 by default.

See `references/pptx-xml-schema.md` for the full list of `buAutoNum` type values.

## Validation Steps
1. Verify rIds are unique in presentation.xml.rels
2. Verify slide order in presentation.xml sldIdLst matches expectations
3. **Verify [Content_Types].xml has entries for all slides** — use `python3 scripts/verify_pptx.py output.pptx` to check
4. Check text formatting by inspecting XML: font size is in hundredths of a point (1500 = 15pt)
5. **Verify at attribute level**: Use `python3 scripts/verify_pptx.py output.pptx` to check specific attributes (font, size, color, position).
6. **Verify auto-numbered lists**: If you created numbered bullets, confirm sequential numbering (1, 2, 3…) not repeated (1, 1, 1…).

See `references/pptx-xml-schema.md` for quick lookup of XML element attributes and EMU conversion values.

## Common Pitfalls
- **rId conflicts**: Never assume rId8 is free. Always check existing relationships first.
- **Corrupted ZIP**: Use `zip -r` from inside the extracted directory, not from parent.
- **Missing relationships**: Each slide needs both entry in presentation.xml AND relationship in presentation.xml.rels.
- **Font size units**: EMUs (English Metric Units) for position/size; font size is in hundredths of a point. See `references/pptx-xml-schema.md` for EMU conversion table (914400 EMUs = 1 inch).
- **Missing [Content_Types].xml entry**: Every new slide MUST be registered in [Content_Types].xml or it will be invisible to Office applications.
- **Wrong textbox modified**: When multiple textboxes exist, regex may match the first occurrence. Use position/size constraints to target the correct element.
- **Namespace prefix error**: ElementTree cannot use 'a', 'p', 'r' prefixes. Use regex or lxml.
- **Auto-numbering restart**: Putting `startAt="1"` on every `<a:buAutoNum>` makes every item numbered "1.". Only the first paragraph should have `startAt`; omit it on subsequent paragraphs to continue the sequence.
- **python-pptx dimension persistence**: Shape dimension changes (`shape.width`, `shape.height`) may not survive save. If this happens, fall back to direct XML manipulation of `<a:xfrm>` elements.
- **lxml raw string attributes**: Using `'r:id'` directly in `element.set()` raises ValueError with lxml. Use `qn('r:id')`.

## Anti-patterns
- Do not use python-pptx for complex formatting changes - it has limited support for text run properties.
- Do not skip the relationship check - using a duplicate rId corrupts the file.
- Do not forget [Content_Types].xml when adding new slides or parts.
- Do not use ElementTree.register_namespace() with 'a', 'p', 'r' prefixes - will raise ValueError.
- Do not assume the first matching text element is the correct target - verify by position/content.
- Do not put `startAt` on every `<a:buAutoNum>` in a numbered list - only the first paragraph needs it.
- Do not skip running `scripts/verify_pptx.py` after repackaging - it catches silent structural errors.
- Do not use raw strings like `'r:id'` in `element.set()` with lxml — use `qn('r:id')`.
- Do not trust python-pptx dimension assignments without XML verification — fall back to lxml if dimensions show as 0.

## Known invariants (by sub-task)

### B1-pptx-formatting (all sub-tasks)
- New slides MUST be registered in `[Content_Types].xml` with an `<Override>` element. Missing this causes the slide to be invisible/ignored by Office and verifier failures. (R1 u2)
- Python stdlib ElementTree cannot register namespace prefixes 'a', 'p', 'r'. Use regex-based string manipulation or lxml instead. (R1 u1)
- When multiple text elements exist on a slide, always match by position + content to target the correct textbox. First match may be wrong. (R1 u1)
- Auto-numbered bullet lists: only the first `<a:buAutoNum>` should specify `startAt`; omit it on subsequent paragraphs or every item restarts at 1. (R2 u1)
- lxml namespace-qualified attributes (r:id, a:blip, etc.) must use `qn()` helper, not raw string. (R2 u0)

## References
- `references/pptx-xml-schema.md` - Quick lookup of XML element attributes and EMU conversion values
- `references/adding-slides.md` - 5-step workflow for adding slides with rId and content type management
- `scripts/verify_pptx.py` - Verification script including content type checks
- `scripts/extract_pptx.py` - Safe extraction, repacking, and content type registration utilities
