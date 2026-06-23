# PPTX File Structure Reference

## Overview

PPTX files are OPC (Open Packaging Convention) packages - ZIP archives containing XML files following the Office Open XML (OOXML) standard.

## Directory Structure

```
pptx_file.pptx/
├── [Content_Types].xml      # MIME types for all content
├── _rels/
│   └── .rels                # Root relationships
├── docProps/
│   ├── app.xml              # Application properties
│   └── core.xml              # Core properties (author, dates)
└── ppt/
    ├── presentation.xml      # Main presentation definition
    ├── _rels/
    │   └── presentation.xml.rels  # Slide relationships (rId → file mapping)
    ├── presProps.xml         # Presentation properties
    ├── viewProps.xml         # View properties
    ├── tableStyles.xml       # Table styles
    ├── theme/
    │   └── theme1.xml        # Theme definition
    ├── slideMasters/
    │   └── slideMaster1.xml  # Slide master template
    ├── slideLayouts/         # Slide layout templates
    ├── slides/
    │   ├── slide1.xml
    │   ├── slide2.xml
    │   └── _rels/
    │       ├── slide1.xml.rels
    │       └── slide2.xml.rels
    └── notesSlides/          # Speaker notes
```

## Key Files Explained

### presentation.xml
Contains the slide order via `<p:sldIdLst>`:
```xml
<p:sldIdLst>
  <p:sldId id="256" r:id="rId2"/>
  <p:sldId id="257" r:id="rId3"/>
</p:sldIdLst>
```

### presentation.xml.rels
Maps rIds to actual slide files:
```xml
<Relationship Id="rId2" Type="...slide" Target="slides/slide1.xml"/>
<Relationship Id="rId3" Type="...slide" Target="slides/slide2.xml"/>
```

**Important**: The rId order in presentation.xml determines slide order, NOT the slide file names.

### Slide XML Structure

```xml
<p:sld>
  <p:cSld>
    <p:spTree>              <!-- Shape tree -->
      <p:nvGrpSpPr/>        <!-- Group shape properties -->
      <p:grpSpPr/>          <!-- Group transform -->
      <p:sp>                <!-- Shape (e.g., title, text box) -->
        <p:nvSpPr>          <!-- Non-visual properties -->
          <p:cNvPr id="2" name="Title 1"/>
          <p:cNvSpPr txBox="1"/>  <!-- txBox="1" = text box -->
          <p:nvPr><p:ph type="title"/></p:nvPr>  <!-- Placeholder type -->
        </p:nvSpPr>
        <p:spPr>            <!-- Shape properties -->
          <a:xfrm>          <!-- Transform (position/size) -->
            <a:off x="685800" y="1569720"/>  <!-- Position in EMUs -->
            <a:ext cx="3657600" cy="548640"/> <!-- Size in EMUs -->
          </a:xfrm>
        </p:spPr>
        <p:txBody>          <!-- Text body -->
          <a:p>             <!-- Paragraph -->
            <a:pPr algn="ctr"/>  <!-- Paragraph properties (alignment) -->
            <a:r>           <!-- Text run -->
              <a:rPr sz="1500" b="1" i="0">  <!-- Run properties -->
                <a:solidFill>
                  <a:srgbClr val="6F6C64"/>  <!-- Color -->
                </a:solidFill>
                <a:latin typeface="Arial"/>  <!-- Font -->
              </a:rPr>
              <a:t>Text content</a:t>  <!-- Actual text -->
            </a:r>
          </a:p>
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>
```

## Units

- **EMUs (English Metric Units)**: 1 inch = 914,400 EMUs
- **Points**: Font sizes in hundredths (1500 = 15pt)
- Standard slide: 12,192,000 × 6,858,000 EMUs (13.33" × 7.5")

## Shape Types

1. **Placeholders**: `<p:ph>` in nvPr
   - `type="title"` - Title placeholder
   - `type="ctrTitle"` - Center title
   - `idx="1"` - Content placeholder

2. **Text Boxes**: `<p:cNvSpPr txBox="1"/>`
   - Not placeholders, standalone text containers

3. **Auto Shapes**: `<p:spPr><a:prstGeom prst="rect"/>`

## Namespaces

| Prefix | URI |
|--------|-----|
| p | http://schemas.openxmlformats.org/presentationml/2006/main |
| a | http://schemas.openxmlformats.org/drawingml/2006/main |
| r | http://schemas.openxmlformats.org/officeDocument/2006/relationships |
| p14 | http://schemas.microsoft.com/office/powerpoint/2010/main |

## Adding a New Slide

1. Create `ppt/slides/slideN.xml` with slide content
2. Add relationship in `ppt/_rels/presentation.xml.rels`:
   ```xml
   <Relationship Id="rIdN" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slideN.xml"/>
   ```
3. Add slide ID in `ppt/presentation.xml`:
   ```xml
   <p:sldId id="258" r:id="rIdN"/>
   ```
4. Create `ppt/slides/_rels/slideN.xml.rels` for slide's relationships
5. Update `[Content_Types].xml` if needed
