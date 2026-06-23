# HWPX File Structure

## Overview

HWPX (Hancom Office XML Package) is a ZIP-based office document format. It replaces the older binary HWP format with XML-based content.

## ZIP Contents

Typical structure:
```
Contents/
├── content.hpf      # Document metadata/properties (OPF package manifest)
├── section0.xml     # Main document content (may have section1.xml, etc.)
└── ...
```

## XML Namespace

HWPX uses the namespace: `http://www.hancom.co.kr/hwpml/2010/HWPML`

Prefix is typically `hp:`:
- `<hp:section>` - Document section
- `<hp:p>` - Paragraph with optional `id` and `paraPrIDRef` attributes
- `<hp:run>` - Text run with formatting via `charPrIDRef`
- `<hp:t>` - Actual text content (may contain `{{placeholder}}` markers)

## Placeholder Pattern

Templates use double-curly braces:
```xml
<hp:t>회사명: {{회사명}}</hp:t>
```

Multiple occurrences of same placeholder are replaced independently.

## Layout Cache (`<linesegarray>`)

HWPX pre-calculates character positions for rendering:

```xml
<hp:p id="1">
  <hp:run><hp:t>회사명: {{회사명}}</hp:t></hp:run>
  <hp:linesegarray>
    <hp:lineseg textpos="0" vertpos="0" vertsize="1000" horzsize="5000"/>
  </hp:linesegarray>
</hp:p>
```

**Critical**: When text length changes (placeholders replaced with actual values), cached positions become invalid, causing overlapping or misaligned characters. Always remove `<hp:linesegarray>` elements from modified paragraphs.

## Character Encoding

- XML files: UTF-8 (with or without BOM)
- ZIP entries: May use UTF-8 filenames

## Compression

Use standard DEFLATE compression when repackaging. Preserve original `ZipInfo` objects when copying unmodified entries to preserve timestamps and permissions.

## Static Content Preservation

Some paragraphs should not be modified:
- Signature placeholders: `수기 서명 칸은 비워 두세요.`
- Document headers/footers with fixed text
- Instructional text

Only strip `<hp:linesegarray>` from paragraphs where text content actually changed.
