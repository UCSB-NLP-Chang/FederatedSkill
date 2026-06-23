---
name: pptx-xml-manipulation
description: Direct XML-level editing of PowerPoint (PPTX) files for precise formatting control, bulk modifications, or when high-level libraries lack needed features. Use when tasks require specific font changes, positioning, color values, slide structure modifications, text formatting verification at XML level, handling split text runs across multiple <a:r> elements, or when python-pptx fails with shape type errors or missing properties.
---

# PPTX XML Manipulation

Directly edit PowerPoint files by manipulating their underlying Open XML structure.

## When to Use

- Precise formatting control (exact colors, positions, sizes, fonts)
- Bulk text or formatting modifications across multiple slides
- Adding/removing slides with specific structure
- High-level libraries (python-pptx) don't expose needed features
- Modifying text that may be split across multiple `<a:r>` runs (common with mixed formatting)
- Verification requires inspecting raw XML
- **python-pptx fails with `NotImplementedError` for unrecognized shape types**
- **python-pptx fails with `AttributeError` on `_NoneColor` when reading colors**
- **Need auto-numbered lists (python-pptx doesn't expose numbering well)**

## Critical Tool Usage Rules

**NEVER use leading/trailing spaces in tool names.** Common failure:
```
# WRONG - space before 'Bash'
{ "function": " Bash", ... }

# CORRECT
{ "function": "Bash", ... }
```

## Core Workflow

### 1. Extract PPTX

```python
import zipfile
zipfile.ZipFile('input.pptx').extractall('/tmp/pptx_work')
```

**Do not use `unzip` command** — it may not be available.

### 2. Handle Split Text Runs (Critical)

Text content is often fragmented across multiple `<a:r>` elements, especially if formatting changes mid-text or if the file was edited. **Always join all text runs:**

```python
# Fragile: assumes single run
single_text = re.search(r'<a:t>([^<]+)</a:t>', shape_xml).group(1)

# Robust: joins all runs
runs = re.findall(r'<a:t[^>]*>([^<]*)</a:t>', shape_xml)
full_text = ''.join(runs).strip()
```

**Pattern for handling `xml:space="preserve"`:**
```python
texts = re.findall(r'<a:t[^>]*>([^<]*)</a:t>', shape_xml)
full_text = ''.join(texts)
```

### 3. Replace Text Across Multiple Runs

When replacing text that may span runs, replace the entire paragraph content:

```python
def replace_paragraph_text(para_xml, new_text):
    """Replace all text in a paragraph, consolidating runs."""
    # Match the entire paragraph content between <a:p> and </a:p>
    # Keep formatting from first run, replace text
    pattern = r'(<a:p[^>]*>.*?<a:r>.*?<a:rPr[^/]*/>)(<a:t>[^<]*</a:t>)'
    # Or more aggressively: replace all runs with a single run
    rpr_match = re.search(r'<a:rPr[^/]*/>', para_xml)
    rpr = rpr_match.group(0) if rpr_match else '<a:rPr lang="en-US"/>'
    
    new_run = f'<a:r>{rpr}<a:t>{new_text}</a:t></a:r>'
    # Replace between <a:p...> and </a:p>, preserving pPr
    result = re.sub(r'(<a:p[^>]*>.*?<a:pPr[^/]*/>)?.*?<a:endParaRPr', 
                    r'\1' + new_run + r'<a:endParaRPr', 
                    para_xml, flags=re.DOTALL)
    return result
```

### 4. Understand the Structure

| Path | Purpose |
|------|---------|
| `ppt/slides/slideN.xml` | Slide content |
| `ppt/presentation.xml` | Slide order (`<p:sldIdLst>`) |
| `ppt/_rels/presentation.xml.rels` | Slide relationships |
| `[Content_Types].xml` | MIME type declarations |
| `ppt/slides/_rels/slideN.xml.rels` | Per-slide relationships |

### 5. Key XML Patterns

**Text box (shape) with formatting:**
```xml
<p:sp>
  <p:nvSpPr><p:cNvPr id="6" name="文本框 5"/></p:nvSpPr>
  <p:spPr>
    <a:xfrm>
      <a:off x="3096000" y="6000000"/>  <!-- position EMUs -->
      <a:ext cx="6000000" cy="400000"/>  <!-- size EMUs -->
    </a:xfrm>
  </p:spPr>
  <p:txBody>
    <a:p>
      <a:pPr algn="ctr"/>  <!-- center alignment -->
      <a:r>
        <a:rPr sz="1500">  <!-- font size in hundredths of pt (15pt) -->
          <a:solidFill><a:srgbClr val="6F6C64"/></a:solidFill>
          <a:latin typeface="Calibri"/>
        </a:rPr>
        <a:t>Caption Text</a:t>
      </a:r>
    </a:p>
  </p:txBody>
</p:sp>
```

**Text run properties (`<a:rPr>`) — common attributes:**
- `sz="1700"` — font size in hundredths of a point (17pt)
- `b="1"` — bold
- `i="1"` — italic
- `lang="en-US"` — language
- `<a:latin typeface="Calibri"/>` — Latin script font
- `<a:solidFill><a:srgbClr val="4A6A54"/></a:solidFill>` — RGB color

**Multi-run text (split across `<a:r>` elements):**
Text may be split across multiple runs with different formatting. When replacing text, you may need to consolidate runs or replace across all runs in a paragraph.

```xml
<!-- Text split across runs -->
<a:r><a:rPr/><a:t>Segment A - </a:t></a:r>
<a:r><a:rPr/><a:t>Pelican Bluff Overlook</a:t></a:r>
```

**Auto-numbered list (add to paragraph properties):**
```xml
<a:p>
  <a:pPr>
    <a:buAutoNum type="arabicPeriod"/>  <!-- 1., 2., 3. -->
  </a:pPr>
  <a:r><a:rPr/><a:t>List item text</a:t></a:r>
</a:p>
```

Bullet types: `arabicPeriod`, `alphaLcParen` (a)), `alphaUcParen` (A)), `romanLcParen` (i)).

**EMU conversions:**
- 914400 EMUs = 1 inch
- 12700 EMUs ≈ 1 point (1/72 inch)
- Slide size: typically 12192000 × 6858000 EMUs (13.333" × 7.5")

See `references/emu-calculations.md` for detailed conversion tables.

### 6. Safe XML Editing

**Avoid `xml.etree.ElementTree` for namespace-heavy edits** — registering namespaces fails with reserved prefixes. Use regex or string replacement for targeted modifications:

```python
import re

# Read slide
with open('/tmp/pptx_work/ppt/slides/slide2.xml', 'r') as f:
    content = f.read()

# Replace font family in all typeface attributes
content = re.sub(r'<a:latin typeface="[^"]*"', '<a:latin typeface="Calibri"', content)
content = re.sub(r'<a:ea typeface="[^"]*"', '<a:ea typeface="Calibri"', content)
content = re.sub(r'<a:cs typeface="[^"]*"', '<a:cs typeface="Calibri"', content)

# Replace color
content = re.sub(r'<a:srgbClr val="[^"]*"', '<a:srgbClr val="4A6A54"', content)

# Replace font size (hundredths of point)
content = re.sub(r'sz="\d+"', 'sz="1700"', content)

# Remove bold/italic
content = re.sub(r'\sb="1"', '', content)
content = re.sub(r'\si="1"', '', content)

# Add auto-numbering to paragraphs (for list slides)
# Insert buAutoNum into pPr elements that don't have one
content = re.sub(
    r'(<a:pPr[^>]*)(?<!buAutoNum>)(>)',
    r'\1><a:buAutoNum type="arabicPeriod"',
    content
)

# Write back
with open('/tmp/pptx_work/ppt/slides/slide2.xml', 'w') as f:
    f.write(content)
```

### 7. Add a New Slide

1. Create `ppt/slides/slideN.xml` with proper namespaces
2. Create `ppt/slides/_rels/slideN.xml.rels` pointing to layout
3. Add to `ppt/_rels/presentation.xml.rels` with unique `rId` (check existing IDs first)
4. Add to `ppt/presentation.xml` `<p:sldIdLst>` with unique `id` (typically 256+)
5. Add to `[Content_Types].xml` with Override for the new slide path

### 8. Repackage

```python
import zipfile
import os

with zipfile.ZipFile('output.pptx', 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('/tmp/pptx_work'):
        for f in files:
            path = os.path.join(root, f)
            arcname = os.path.relpath(path, '/tmp/pptx_work')
            zf.write(path, arcname)
```

## Validation

Run `scripts/validate_pptx.py` to verify:
- All required XML files present
- Relationship consistency
- Content type declarations

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| PowerPoint can't open file | Missing `[Content_Types].xml` entry | Add Override for new slide |
| Slides out of order | Wrong `id` in `presentation.xml` | Use sequential IDs |
| Broken relationships | Duplicate `rId` values | Check `presentation.xml.rels` for conflicts |
| Formatting not applied | Wrong namespace prefix | Use `a:` for DrawingML, `p:` for PresentationML |
| `ET.register_namespace` fails | Reserved prefix format | Use regex/string replacement instead |
| Tool call fails with "No such tool" | **Extra spaces in function name** | Use exact tool names: `Read`, `Bash`, `Write` (no leading/trailing spaces) |
| Bash output truncated | Long output in `cat` | Use `grep` or targeted extraction instead |
| Multi-run text not fully replaced | Text split across `<a:r>` elements | Use regex to match entire paragraph or consolidate runs |
| Caption text concatenated with other content | Replaced wrong paragraph | Target only caption shapes by name pattern (`文本框`) |

## Anti-Patterns

- **Don't** use `xml.etree.ElementTree.register_namespace` with PPTX — it fails on reserved prefixes
- **Don't** use string templating for XML without escaping
- **Don't** assume slide IDs match file names (slide3.xml could have id="262")
- **Don't** modify only slide XML without updating relationships
- **Don't** rely on `unzip` system command — use Python's zipfile
- **Don't** trust `cat` for large XML files — use targeted `grep` or `python3 -c` extraction
- **Don't** include spaces in tool names — ` Bash` fails, `Bash` works
- **Don't** assume text is in a single `<a:t>` element — always join runs
- **Don't** modify title/content placeholders when targeting captions — check `<p:ph` to identify placeholders

## Fallback: python-pptx

For simpler tasks, try `python-pptx` first. See `references/python-pptx-patterns.md` for common API patterns and pitfalls.

Basic usage:
```python
from pptx import Presentation
prs = Presentation('input.pptx')
# ... modifications ...
prs.save('output.pptx')
```

**Switch to direct XML manipulation when:**
- `NotImplementedError: Shape instance of unrecognized shape type`
- `AttributeError: no .rgb property on color type '_NoneColor'`
- Need auto-numbered lists (python-pptx doesn't expose numbering well)
- Need precise positioning that python-pptx rounds
- Working with shapes that python-pptx can't identify
- Text is split across multiple runs with complex formatting

## python-pptx Pitfalls (Quick Reference)

If using python-pptx, watch for these specific errors from the trace:

| Error | Cause | Solution |
|-------|-------|----------|
| `ImportError: cannot import name 'RgbColor'` | Wrong capitalization | Use `RGBColor` (all caps) |
| `AttributeError: no .rgb property on color type '_NoneColor'` | Color unset/inherited | Check `font.color.type` before accessing `.rgb` |
| `TypeError: value must be an integral type, got <class 'float'>` | EMU values must be int | Cast to `int()`: `shape.left = int(Inches(1.5))` |
| `NotImplementedError: Shape instance of unrecognized shape type` | Unknown shape type | Use direct XML or skip shape |
| `AttributeError: '_Paragraph' object has no attribute 'getparent'` | Wrong lxml access | Use `p._p.getparent()` not `p.getparent()` |
| Installation fails with "externally-managed-environment" | PEP 668 restriction | Use `--break-system-packages` or venv |

Safe color reading pattern:
```python
def get_rgb_safe(font_color):
    if font_color is None or font_color.type is None:
        return None
    try:
        return font_color.rgb
    except AttributeError:
        return None
```

Safe EMU positioning (must be integer):
```python
from pptx.util import Inches
shape.left = int(Inches(1.52))  # Cast to int!
shape.width = int(Inches(10))
```
