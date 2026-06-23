# PPTX XML Notes & Namespace Mappings

## Common Namespaces

- Presentation: `p` = `http://schemas.openxmlformats.org/presentationml/2006/main`
- Drawing: `a` = `http://schemas.openxmlformats.org/drawingml/2006/main`
- Relationships: `r` = `http://schemas.openxmlformats.org/officeDocument/2006/relationships`

## Text Structure

```xml
<p:txBody>
  <a:bodyPr/>
  <a:lstStyle/>
  <a:p>
    <a:pPr algn="ctr"/>
    <a:r>
      <a:rPr lang="en-US" latin="Arial" sz="203200" b="0">
        <a:solidFill><a:srgbClr val="49607A"/></a:solidFill>
      </a:rPr>
      <a:t xml:space="preserve">Text Part 1</a:t>
    </a:r>
    <a:r>
      <a:rPr lang="en-US" latin="Arial" sz="203200" b="0">
        <a:solidFill><a:srgbClr val="49607A"/></a:solidFill>
      </a:rPr>
      <a:t>Text Part 2</a:t>
    </a:r>
    <a:endParaRPr lang="en-US"/>
  </a:p>
</p:txBody>
```

## EMU Conversions

| Unit | EMU Value |
|------|----------|
| 1 inch | 914400 |
| 1 cm | 360000 |
| 1 mm | 36000 |
| 1 point | 12700 |

- 16pt = 203200 EMU
- 12pt = 152400 EMU
- 10pt = 127000 EMU

## Shape Tags

| Tag | Meaning |
|-----|---------|
| `p:sp` | Standard shape |
| `p:grpSp` | Group shape |
| `p:pic` | Picture |
| `p:cxnSp` | Connector |

## Font Attribute Reference

Within `<a:rPr>` (run properties):

- `latin="Arial"` — Font family for Latin text
- `sz="203200"` — Font size in EMUs (16pt = 203200)
- `b="0"` or `b="1"` — Bold off/on
- `i="0"` or `i="1"` — Italic off/on

Color is set within `<a:solidFill>`:
```xml
<a:solidFill><a:srgbClr val="49607A"/></a:solidFill>
```
