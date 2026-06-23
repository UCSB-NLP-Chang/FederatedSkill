# PPTX XML Structure Reference

## ZIP Layout

```
.pptx (ZIP)
├── [Content_Types].xml          # Content type declarations
├── _rels/
├── ppt/
│   ├── presentation.xml         # Slide order & rId references
│   ├── _rels/
│   │   └── presentation.xml.rels # rId -> slide/media mappings
│   ├── slides/
│   │   ├── slide1.xml
│   │   ├── slide2.xml
│   │   └── _rels/
│   │       ├── slide1.xml.rels
│   │       └── slide2.xml.rels
│   ├── slideLayouts/
│   ├── slideMasters/
│   └── theme/
```

## Slide XML Structure

```xml
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld>
    <p:spTree>
      <p:sp>  <!-- Shape -->
        <p:nvSpPr>
          <p:cNvPr id="2" name="Title"/>
          <p:cNvSpPr txBox="1"/>  <!-- Text box flag -->
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm>
            <a:off x="457200" y="274638"/>  <!-- Position in EMUs -->
            <a:ext cx="11223600" cy="1493520"/>  <!-- Size in EMUs -->
          </a:xfrm>
        </p:spPr>
        <p:txBody>  <!-- Text content -->
          <a:p>
            <a:pPr algn="ctr"/>  <!-- Alignment -->
            <a:r>
              <a:rPr lang="en-US" sz="1500" b="1">
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
| sz | a:rPr | 1500 = 15pt | Hundredths of a point |
| b | a:rPr | 0/1 | Bold on/off |
| i | a:rPr | 0/1 | Italic on/off |
| u | a:rPr | none/sng/dbl | Underline |
| typeface | a:latin | Arial | Font name |
| val | a:srgbClr | 6F6C64 | RGB hex without # |
| algn | a:pPr | l/r/ctr/just | Text alignment |

## EMU Conversions

```
1 inch = 914,400 EMUs
1 cm = 360,000 EMUs
1 point = 12,700 EMUs
Standard 16:9 slide: 12,192,000 x 6,858,000 EMUs
```

## Position Reference

Bottom-center positioning example:
- x = (slide_width - box_width) / 2
- y = slide_height - box_height - margin

Example: 10,000,000 EMU wide box at bottom with 200,000 EMU margin:
- x = (12,192,000 - 10,000,000) / 2 = 1,096,000
- y = 6,858,000 - 400,000 - 200,000 = 6,258,000

## Auto-Numbered Bullets

```xml
<a:p>
  <a:pPr>
    <a:buFont typeface="Arial"/>
    <a:buAutoNum type="arabicPeriod" startAt="1"/>
  </a:pPr>
  <a:r>
    <a:t>Bullet text</a:t>
  </a:r>
</a:p>
```

Bullet types: `arabicPeriod`, `arabicParenR`, `romanLcParenBoth`, `alphaLcPeriod`
