# PPTX Structure Reference

## ZIP Layout

```
.pptx (ZIP)
├── [Content_Types].xml
├── ppt/
│   ├── presentation.xml          # Slide order
│   ├── _rels/presentation.xml.rels # rId mappings
│   └── slides/slide1.xml
```

## EMU Conversions

- 1 inch = 914,400 EMUs
- 1 cm = 360,000 EMUs
- 1 point = 12,700 EMUs
- Standard slide: 12,192,000 x 6,858,000 EMUs

## Slide XML Structure

```xml
<p:sld xmlns:p="..." xmlns:a="..." xmlns:r="...">
  <p:cSld><p:spTree>
    <p:sp>
      <p:nvSpPr><p:cNvPr id="N" name="..."/></p:nvSpPr>
      <p:spPr><a:xfrm><a:off x="X" y="Y"/><a:ext cx="W" cy="H"/></a:xfrm></p:spPr>
      <p:txBody><a:p><a:r><a:rPr sz="1500"/><a:t>Text</a:t></a:r></a:p></p:txBody>
    </p:sp>
  </p:spTree></p:cSld>
</p:sld>
```

## String Template for New Slide

```python
SLIDE_TEMPLATE = '''<sld xmlns="http://schemas.openxmlformats.org/presentationml/2006/main"
  xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <cSld><spTree>
    <nvGrpSpPr><cNvPr id="1" name=""/><cNvGrpSpPr/></nvGrpSpPr>
    <grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></a:xfrm></grpSpPr>
    <sp>
      <nvSpPr><cNvPr id="2" name="Title 1"/></nvSpPr>
      <txBody><a:p><a:r><a:t>{title}</a:t></a:r></a:p></txBody>
    </sp>
  </spTree></cSld>
</sld>'''
```

## buAutoNum Types

| Type | Output |
|------|--------|
| arabicPeriod | 1. 2. 3. |
| alphaLcParenR | a) b) c) |
| romanLcParenBoth | (i) (ii) |

## Relationship Updates (New Slide)

1. Add to `ppt/_rels/presentation.xml.rels`:
   ```xml
   <Relationship Id="rId{X}" Type="...slide" Target="slides/slideN.xml"/>
   ```
2. Add to `ppt/presentation.xml`:
   ```xml
   <p:sldId id="{NUM}" r:id="rId{X}"/>
   ```
3. Add to `[Content_Types].xml`:
   ```xml
   <Override PartName="/ppt/slides/slideN.xml" ContentType="...slide+xml"/>
   ```

## Placeholder Shape Names

- `Title 1`, `Content Placeholder 2`, `Text Placeholder 3`
- `Date Placeholder 4`, `Footer Placeholder 5`, `Slide Number Placeholder 6`
- Remove these when cloning slides
