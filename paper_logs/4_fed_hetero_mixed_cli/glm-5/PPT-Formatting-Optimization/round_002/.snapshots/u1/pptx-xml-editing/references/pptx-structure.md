# PPTX Structure Reference

## ZIP Layout

```
.pptx (ZIP)
├── [Content_Types].xml
├── _rels/
├── ppt/
│   ├── presentation.xml          # Slide order & rId references
│   ├── _rels/presentation.xml.rels # rId -> slide/media mappings
│   ├── slides/
│   │   ├── slide1.xml
│   │   └── _rels/slide1.xml.rels
│   ├── slideMasters/
│   └── theme/
```

## Slide XML Structure

```xml
<p:sld xmlns:p="..." xmlns:a="..." xmlns:r="...">
  <p:cSld>
    <p:spTree>
      <p:sp>  <!-- Shape -->
        <p:nvSpPr>
          <p:cNvPr id="N" name="..."/>
          <p:cNvSpPr txBox="1"/>  <!-- Text box flag -->
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm>
            <a:off x="X" y="Y"/>  <!-- Position in EMUs -->
            <a:ext cx="W" cy="H"/>  <!-- Size in EMUs -->
          </a:xfrm>
        </p:spPr>
        <p:txBody>  <!-- Text content -->
          <a:p>
            <a:pPr algn="ctr"/>  <!-- Alignment: l/r/ctr/just -->
            <a:r>
              <a:rPr lang="en-US" sz="1500" b="0">
                <a:solidFill>
                  <a:srgbClr val="6F6C64"/>
                </a:solidFill>
                <a:latin typeface="Arial"/>
              </a:rPr>
              <a:t>Text content here</a:t>
            </a:r>
          </a:p>
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>
```

## Text Styling Attributes

| Attribute | Element | Values | Notes |
|-----------|---------|--------|-------|
| sz | a:rPr | 1500 = 15pt | In hundredths of a point |
| b | a:rPr | 0/1 | Bold on/off |
| i | a:rPr | 0/1 | Italic on/off |
| u | a:rPr | none/sng/dbl | Underline |
| typeface | a:latin | Font name | Latin fonts |
| val | a:srgbClr | 6-char hex | RGB color without # |
| algn | a:pPr | l/r/ctr/just | Text alignment |

## EMU Conversions

- 1 inch = 914,400 EMUs
- 1 cm = 360,000 EMUs
- 1 point = 12,700 EMUs
- Standard slide: 12,192,000 x 6,858,000 EMUs (13.33" x 7.5")

## Arial Font Width Estimates (at 15pt, in EMUs)

Use these for `cx` (width) calculations to ensure single-line text fit:

- Narrow (`i, l, I, j, ., ;, :, !, '`): ~50,000
- Medium (`f, t, s, r, -, (, ), [, ]`): ~70,000
- Average (`a, c, e, g, m, n, o, p, q, u, v, x, z`): ~85,000
- Wide (`A-Z, 0-9`): ~100,000
- Extra Wide (`M, Q, O, &, %, $, #, @, ~, +, =, <, >`): ~120,000
- Space: ~40,000

Add padding: `total_width + 2 * 91440` (for left/right insets).

## Position Reference

For bottom-center positioning:
- x = (slide_width - box_width) / 2
- y = slide_height - box_height - margin

Example: 10,000,000 wide box at bottom with 100,000 margin:
- x = (12192000 - 10000000) / 2 = 1096000
- y = 6858000 - 400000 - 200000 = 6258000

## Relationship Handling

When adding a new slide (`slide7.xml`):

1. Add `<p:sldId id="263" r:id="rId257"/>` to `ppt/presentation.xml`
2. Add relationship to `ppt/_rels/presentation.xml.rels`:
   ```xml
   <Relationship Id="rId257" 
                 Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" 
                 Target="slides/slide7.xml"/>
   ```
3. Add Override to `[Content_Types].xml`:
   ```xml
   <Override PartName="/ppt/slides/slide7.xml"
             ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
   ```
4. Ensure `rId` is unique across the rels file

## Common Text Box Positioning

### Bottom Center Caption Box

For a caption box at the bottom center of a 16:9 slide:
- Width: 8,000,000 EMUs (~8.75 inches)
- Height: 400,000-600,000 EMUs depending on text size
- X position: (12,192,000 - 8,000,000) / 2 = 2,096,000 EMUs
- Y position: 6,858,000 - height - margin (e.g., 5,852,160 for 400,000 height + 600,000 margin)
