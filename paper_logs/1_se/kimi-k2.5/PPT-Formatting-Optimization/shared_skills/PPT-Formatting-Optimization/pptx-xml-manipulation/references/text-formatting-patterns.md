# Text Formatting Patterns in PPTX XML

Common text formatting modifications and their XML representations.

## Font Family

```xml
<!-- Before -->
<a:latin typeface="Lucida Grande"/>
<a:ea typeface="Lucida Grande"/>
<a:cs typeface="Lucida Grande"/>

<!-- After -->
<a:latin typeface="Calibri"/>
<a:ea typeface="Calibri"/>
<a:cs typeface="Calibri"/>
```

## Font Size

Size is in **hundredths of a point**:

| Desired | XML Value |
|---------|-----------|
| 10pt | 1000 |
| 12pt | 1200 |
| 15pt | 1500 |
| 17pt | 1700 |
| 18pt | 1800 |
| 24pt | 2400 |

```xml
<a:rPr sz="1700"/>
```

## Text Color (RGB)

```xml
<a:solidFill>
  <a:srgbClr val="4A6A54"/>
</a:solidFill>
```

## Bold and Italic

```xml
<!-- Bold -->
<a:rPr b="1"/>

<!-- Italic -->
<a:rPr i="1"/>

<!-- Both -->
<a:rPr b="1" i="1"/>

<!-- Neither (remove attributes) -->
<a:rPr sz="1700"/>
```

## Text Alignment

```xml
<!-- Left -->
<a:pPr algn="l"/>

<!-- Center -->
<a:pPr algn="ctr"/>

<!-- Right -->
<a:pPr algn="r"/>
```

## Position and Size (EMUs)

```xml
<a:xfrm>
  <a:off x="1096000" y="6258000"/>  <!-- top-left corner -->
  <a:ext cx="10000000" cy="400000"/> <!-- width, height -->
</a:xfrm>
```

Common positions for bottom-center caption on standard slide (12192000 × 6858000):
- x = ~1,000,000 to 10,000,000 (centered: (12192000 - width) / 2)
- y = ~6,000,000 to 6,300,000 (near bottom)

## Numbered Lists

```xml
<a:p>
  <a:pPr>
    <a:buAutoNum type="arabicPeriod"/>
  </a:pPr>
  <a:r>
    <a:rPr/>
    <a:t>First item</a:t>
  </a:r>
</a:p>
```

Bullet types: `arabicPeriod` (1.), `alphaLcParen` (a)), `romanLcParen` (i)), etc.
