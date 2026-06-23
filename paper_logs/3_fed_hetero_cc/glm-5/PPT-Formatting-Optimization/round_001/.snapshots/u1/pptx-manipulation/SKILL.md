---
name: pptx-manipulation
description: Programmatically read and modify PowerPoint (PPTX) files by manipulating the underlying XML structure. Use when you need to add/remove slides, modify text/formatting, or make bulk changes that are difficult through GUI automation. Trigger scenarios include caption formatting, slide generation, and relationship ID management.
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
- Edit slide XML in `ppt/slides/slideN.xml`
- Text formatting: `<a:rPr>` elements (font, size, color, bold, italic)
- Position/size: `<p:spPr>` with `<a:xfrm>` containing `<a:off x="" y=""/>` and `<a:ext cx="" cy=""/>`
- Colors: `<a:solidFill><a:srgbClr val="6F6C64"/></a:solidFill>`

### 4. Add a new slide
Requires 4 coordinated changes:

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

### 5. Repackage
```bash
cd pptx_extracted && zip -r ../output.pptx . && cd ..
```

## Validation Steps
1. Verify rIds are unique in presentation.xml.rels
2. Verify slide order in presentation.xml sldIdLst matches expectations
3. Open output file in PowerPoint or LibreOffice to confirm validity
4. Check text formatting by inspecting XML: font size is in hundredths of a point (1500 = 15pt)
5. **Verify at attribute level**: Use `python3 scripts/verify_pptx.py output.pptx` to check specific attributes (font, size, color, position) rather than just file-level existence.

See `references/pptx-xml-schema.md` for quick lookup of XML element attributes and EMU conversion values.

## Common Pitfalls
- **rId conflicts**: Never assume rId8 is free. Always check existing relationships first.
- **Corrupted ZIP**: Use `zip -r` from inside the extracted directory, not from parent.
- **Missing relationships**: Each slide needs both entry in presentation.xml AND relationship in presentation.xml.rels.
- **Font size units**: EMUs (English Metric Units) for position/size; font size is in hundredths of a point. See `references/pptx-xml-schema.md` for EMU conversion table (914400 EMUs = 1 inch).

## Anti-patterns
- Do not use python-pptx for complex formatting changes - it has limited support for text run properties.
- Do not skip the relationship check - using a duplicate rId corrupts the file.
- Do not forget [Content_Types].xml when adding new content types (rarely needed for basic slides).