# PPTX XML Notes & Namespace Mappings

## Common Namespaces

| Prefix | URI |
|--------|-----|
| `p` | `http://schemas.openxmlformats.org/presentationml/2006/main` |
| `a` | `http://schemas.openxmlformats.org/drawingml/2006/main` |
| `r` | `http://schemas.openxmlformats.org/officeDocument/2006/relationships` |

## Text Structure (Multi-run Example)

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

## Shape Tags

| Tag | Type |
|-----|------|
| `p:sp` | Standard shape |
| `p:grpSp` | Group shape |
| `p:pic` | Picture |
| `p:cxnSp` | Connector |

## Font Attributes (in `<a:rPr>`)

| Attribute | Value Format | Example |
|-----------|--------------|---------|
| `latin` | Font name string | `latin="Arial"` |
| `sz` | Size in hundredths of a point | `sz="1600"` = 16pt |
| `b` | Bold: "0" or "1" | `b="1"` |
| `i` | Italic: "0" or "1" | `i="1"` |

## Color in XML

```xml
<a:solidFill>
  <a:srgbClr val="49607A"/>
</a:solidFill>
```

- `val` is hex RGB without `#` prefix
- `49607A` = RGB(73, 96, 122)