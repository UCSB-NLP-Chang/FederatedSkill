---
name: pptx-manipulation
description: Programmatically read and modify PowerPoint (.pptx) files via XML or python-pptx. Use for formatting, positioning, slide generation, text replacement, or structural changes with verification at the attribute level.
---

# PowerPoint XML Manipulation

Edit .pptx files by treating them as ZIP archives containing XML documents. This approach provides precise control over formatting, positioning, and structure that high-level libraries often obscure.

## Quick Start

1. **Extract**: Treat .pptx as ZIP, extract to working directory
2. **Locate**: Find target content in `ppt/slides/slide{N}.xml`
3. **Modify**: Edit XML elements (text, formatting, positioning)
4. **Repack**: ZIP contents with `.pptx` extension
5. **Verify**: Parse XML to confirm changes at attribute level

## Key Technical Details

### Measurement Units
- **EMUs** (English Metric Units): 914400 EMUs = 1 inch
- Common slide dimensions: 12192000 × 6858000 EMUs (16:9)
- Caption positioning example: X=1572000, Y=6000000, Width=6000000

### Critical XML Paths
| Element | Path | Purpose |
|---------|------|---------|
| Slide content | `ppt/slides/slide{N}.xml` | Individual slide markup |
| Slide order | `ppt/presentation.xml` | Slide IDs and sequence |
| Text formatting | `//a:rPr` | Font, size, color, bold |
| Position | `//a:xfrm/a:off` | X/Y coordinates (x, y attrs) |
| Dimensions | `//a:xfrm/a:ext` | Width/height (cx, cy attrs) |
| Paragraph props | `//a:pPr` | Alignment, bullets |

### XML Namespaces
```python
NSMAP = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
}
```

## Common Operations

### Modify Text Formatting
Target: `a:rPr` element (run properties)
```xml
<a:rPr lang="en-US" sz="1500" b="0">
  <a:solidFill><a:srgbClr val="6F6C64"/></a:solidFill>
  <a:latin typeface="Arial"/>
</a:rPr>
```
- Font size: `sz` attribute in hundredths of a point (1500 = 15pt)
- Bold: `b="1"` or `b="0"`
- Color: `a:srgbClr/@val` as 6-digit hex (no #)
- Font family: `a:latin/@typeface`

### Adjust Position and Size
Target: `a:xfrm` (transform) containing `a:off` and `a:ext`
```xml
<a:xfrm>
  <a:off x="1572000" y="6000000"/>
  <a:ext cx="6000000" cy="400000"/>
</a:xfrm>
```
- X/Y: `a:off` attributes in EMUs
- Width/Height: `a:ext` attributes (cx=width, cy=height)

### Set Text Alignment
Target: `a:pPr` (paragraph properties)
```xml
<a:pPr algn="ctr"/>  <!-- center -->
<!-- algn values: l (left), r (right), ctr (center), just (justify) -->
```

### Auto-Numbered Bullets
Target: `a:pPr` with bullet style
```xml
<a:pPr>
  <a:buAutoNum type="arabicParenR"/>
</a:pPr>
```
- `arabicParenR`: 1), 2), 3)
- `alphaLcParenR`: a), b), c)

## Verification Strategy

Always verify at the XML attribute level, not just file existence.

1. **Slide count**: Check `ppt/slides/slide{N}.xml` files and IDs in `presentation.xml`
2. **Text content**: Extract `//a:t` text nodes
3. **Formatting**: Verify `a:rPr/@sz`, `a:rPr/@b`, `a:solidFill/a:srgbClr/@val`
4. **Position**: Check `a:xfrm/a:off/@x`, `a:xfrm/a:off/@y`
5. **Dimensions**: Check `a:xfrm/a:ext/@cx`, `a:xfrm/a:ext/@cy`

See `scripts/verify_pptx.py` for reusable verification helpers.

## Anti-Patterns

- **Don't** rely solely on high-level libraries (python-pptx) for precise positioning or complex formatting—they often lack granularity
- **Don't** modify slides without checking `presentation.xml` slide IDs—orphaned slides may break the deck
- **Don't** assume text is in the first `a:r` element—captions may span multiple runs
- **Don't** forget XML namespaces—use qualified names or register NSMAP
- **Don't** trust visual inspection alone—verify the actual XML attributes

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| Changes not visible | XML not saved or wrong slide | Verify file path and slide number in XML |
| Position values seem wrong | Mixing EMUs and points | Convert: inches × 914400 = EMUs |
| Font not applied | Missing `a:ea` or `a:cs` typeface | Set all three: latin, ea, cs |
| Slide order wrong | Slide IDs in presentation.xml | Update `p:sldId` elements in presentation.xml |
| Zip corruption | Wrong compression method | Use `zipfile.ZIP_DEFLATED` |

## Fallbacks

If direct XML manipulation fails:
1. Use `python-pptx` for simple structural changes (adding slides, basic text)
2. Convert to Google Slides via API for collaborative editing tasks
3. Export to PDF and use PDF manipulation tools if presentation format is flexible

## References

- `references/pptx-xml-schema.md` - Detailed element reference
- `references/adding-slides.md` - 4-step workflow for adding slides with rId management
- `scripts/verify_pptx.py` - Verification script for common attributes
- `scripts/extract_pptx.py` - Safe extraction and repacking utilities