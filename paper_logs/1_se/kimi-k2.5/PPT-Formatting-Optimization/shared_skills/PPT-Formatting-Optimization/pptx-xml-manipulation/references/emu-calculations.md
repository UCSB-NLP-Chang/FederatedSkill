# EMU Calculations Reference

EMU (English Metric Unit) is the coordinate system used in Open XML.

## Conversions

| From | To EMU | Formula |
|------|--------|---------|
| Inches | EMU | × 914400 |
| Points (pt) | EMU | × 12700 |
| Centimeters | EMU | × 360000 |
| Millimeters | EMU | × 36000 |

## Common Values

| Description | EMU |
|-------------|-----|
| 1 inch | 914400 |
| 1 point (1/72") | 12700 |
| Standard slide width (13.333") | 12192000 |
| Standard slide height (7.5") | 6858000 |
| 1 cm | 360000 |
| Left margin (0.75") | 685800 |
| Bottom position for captions (6.5") | 6000000 |

## Font Size

Font size in Open XML is in **hundredths of a point**:

| Desired Size | XML Value |
|--------------|-----------|
| 10pt | 1000 |
| 12pt | 1200 |
| 15pt | 1500 |
| 18pt | 1800 |
| 24pt | 2400 |
| 36pt | 3600 |

## Positioning Reference

Standard slide: 12192000 × 6858000 EMU

```
(0,0)                    (12192000,0)
   ┌────────────────────────────┐
   │                            │
   │         CENTER             │
   │     (6096000, 3429000)     │
   │                            │
   │                            │
   └────────────────────────────┘
(0,6858000)            (12192000,6858000)
```

Bottom-centered text box example:
- x = (slide_width - box_width) / 2 = (12192000 - 6000000) / 2 = 3096000
- y = 6000000 (about 6.5 inches from top)
