# PPTX XML Schema Reference

## Slide Structure

```xml
<p:sld xmlns:p="..." xmlns:a="...">
  <p:cSld>
    <p:spTree>
      <p:sp>  <!-- Shape -->
        <p:nvSpPr>...</p:nvSpPr>  <!-- Non-visual properties -->
        <p:spPr>                   <!-- Shape properties -->
          <a:xfrm>                 <!-- Transform/position -->
            <a:off x="0" y="0"/>   <!-- Offset (position) -->
            <a:ext cx="0" cy="0"/> <!-- Extents (size) -->
          </a:xfrm>
        </p:spPr>
        <p:txBody>                 <!-- Text body -->
          <a:bodyPr/>              <!-- Body properties -->
          <a:lstStyle/>            <!-- List styles -->
          <a:p>                    <!-- Paragraph -->
            <a:pPr algn="ctr"/>    <!-- Paragraph props (alignment) -->
            <a:r>                  <!-- Run -->
              <a:rPr lang="en-US" sz="1100" b="1">  <!-- Run props -->
                <a:solidFill>
                  <a:srgbClr val="000000"/>
                </a:solidFill>
                <a:latin typeface="Arial"/>
              </a:rPr>
              <a:t>Text here</a:t>
            </a:r>
          </a:p>
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>
```

## Common Attributes

### Text Formatting (a:rPr)
| Attribute | Meaning | Example |
|-----------|---------|---------|
| `sz` | Size in hundredths of pt | `1500` = 15pt |
| `b` | Bold | `1` = on, `0` = off |
| `i` | Italic | `1` = on, `0` = off |
| `u` | Underline | `sng` = single |
| `strike` | Strikethrough | `sngStrike` |

### Alignment (a:pPr @algn)
| Value | Meaning |
|-------|---------|
| `l` | Left |
| `r` | Right |
| `ctr` | Center |
| `just` | Justified |
| `dist` | Distributed |

### Bullet Types (a:buAutoNum @type)
| Value | Format |
|-------|--------|
| `arabicPeriod` | 1., 2., 3. |
| `arabicParenR` | 1), 2), 3) |
| `alphaLcParenR` | a), b), c) |
| `alphaUcParenR` | A), B), C) |
| `romanLcParenR` | i), ii), iii) |

### Auto-Numbering startAt Attribute (CRITICAL)
`<a:buAutoNum>` accepts an optional `startAt` attribute:
- **First paragraph**: `<a:buAutoNum type="arabicPeriod" startAt="1"/>` — starts numbering at 1
- **Subsequent paragraphs**: `<a:buAutoNum type="arabicPeriod"/>` — omit `startAt` to continue the sequence
- **Pitfall**: Putting `startAt="1"` on every paragraph restarts each item to "1." instead of sequencing 1, 2, 3…
- If all paragraphs omit `startAt`, PowerPoint auto-sequences from 1 by default

### Paragraph Indentation for Bullets
```xml
<a:pPr marL="342900" indent="-342900">
  <a:buFont typeface="Arial"/>
  <a:buAutoNum type="arabicPeriod"/>
</a:pPr>
```
- `marL` = left margin (342900 EMUs ≈ 0.375 in, typical bullet indent)
- `indent` = negative of marL for hanging indent (aligns text after number)
- `buFont` = font for the bullet character/number

## EMU Reference

| Measurement | EMUs |
|-------------|------|
| 1 inch | 914400 |
| 1 cm | 360000 |
| 1 mm | 36000 |
| 1 pt | 12700 |

## Slide Dimensions (16:9)
- Width: 12192000 EMUs (13.333 inches)
- Height: 6858000 EMUs (7.5 inches)

## Positioning Reference
- X: 0 = left edge
- Y: 0 = top edge
- Center of 16:9 slide: X=6096000, Y=3429000