# EMU Conversion Reference

English Metric Units (EMUs) are the internal unit used by PowerPoint.

## Conversion Table

| Unit | EMU Value |
|------|----------|
| 1 inch | 914400 |
| 1 cm | 360000 |
| 1 mm | 36000 |
| 1 point | 12700 |

## Using pptx.util Helpers

```python
from pptx.util import Inches, Pt, Emu, Cm, Mm

# Convert to EMUs automatically
Inches(1.5)   # 1371600 EMUs
Pt(12)        # 152400 EMUs
Cm(2.5)       # 900000 EMUs
Mm(25)        # 900000 EMUs
```

## Slide Dimensions (Standard 16:9)

| Property | EMUs | Inches |
|----------|------|--------|
| Width | 12192000 | 13.33 |
| Height | 6858000 | 7.5 |

Access programmatically:
```python
slide_width = prs.slide_width   # EMUs
slide_height = prs.slide_height  # EMUs
```

## Common Position Values

| Position | EMUs | Inches |
|----------|------|--------|
| Left margin | 457200 | 0.5 |
| Right margin (13.33" - 0.5") | 12146300 | ~13.3 |
| Top margin | 457200 | 0.5 |
| Lower half start | 4572000 | 5.0 |

## TypeError Prevention

**Always wrap numeric values:**

```python
# CORRECT
shape.left = Inches(2.0)
shape.top = Inches(6.5)

# WRONG - raises TypeError
shape.left = 2.0   # TypeError: value must be integral type
```
