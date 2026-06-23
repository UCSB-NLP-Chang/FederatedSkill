# HWPX File Structure

HWPX (Hancom WP ML XML) is Hancom Office's open document format.

## Archive Structure
```
document.hwpx
├── Contents/
│   ├── content.hpf      # Document metadata and settings
│   ├── section0.xml     # Main content (first section)
│   ├── section1.xml     # Additional sections if present
│   └── ...
├── DocInfo/
│   └── ...              # Document properties
└── [Content_Types].xml  # Content type definitions
```

## XML Structure

### Namespace
```xml
xmlns:hp="http://www.hancom.co.kr/hwpml/2010/HWPML"
```

### Paragraph Structure
```xml
<hp:p id="1" paraPrIDRef="0">
  <hp:run charPrIDRef="0">
    <hp:t>Text content here</hp:t>
  </hp:run>
  <hp:linesegarray>
    <hp:lineseg textpos="0" vertpos="0" vertsize="1000" horzsize="5000"/>
  </hp:linesegarray>
</hp:p>
```

### Key Elements
- `<hp:p>` - Paragraph container
- `<hp:run>` - Text run with formatting
- `<hp:t>` - Actual text content
- `<hp:linesegarray>` - Layout cache (computed line segments)

## Layout Cache Behavior

The `<hp:linesegarray>` element stores pre-computed layout information. When text content changes:
1. The cached positions become invalid
2. Must remove the entire `<hp:linesegarray>` element
3. Hancom Office will recalculate on next open

Failure to remove stale layout cache causes:
- Incorrect text positioning
- Overlapping text
- Missing content

## Common Placeholder Patterns

Korean templates typically use:
- `{{필드명}}` - Double braces with Korean field name
- Example: `{{회사명}}`, `{{담당자}}`, `{{전화번호}}`

## Encoding

Always use UTF-8 encoding when reading/writing HWPX XML files.