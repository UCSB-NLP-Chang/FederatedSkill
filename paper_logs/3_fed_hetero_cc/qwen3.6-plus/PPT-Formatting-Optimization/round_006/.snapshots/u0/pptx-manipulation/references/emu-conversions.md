# EMU Conversion Reference

English Metric Units (EMUs) are PowerPoint's internal unit.

## Unit Conversions

| Unit | EMU Value |
|------|----------|
| 1 inch | 914400 |
| 1 point | 12700 |
| 1 cm | 360000 |

## Common Sizes

| Size | EMU Value |
|------|----------|
| 16pt | 203200 |
| 12pt | 152400 |
| 10pt | 127000 |

## Using pptx.util Helpers

```python
from pptx.util import Inches, Pt, Emu

Inches(1.5)   # 1371600 EMUs
Pt(16)        # 203200 EMUs
```

## Slide Dimensions (Standard 16:9)

- Width: 12192000 EMUs (13.33 inches)
- Height: 6858000 EMUs (7.5 inches)

```python
slide_width = prs.slide_width
slide_height = prs.slide_height
```

## Reading vs Writing

- **Writing**: Use `Inches()` or `Pt()` constructors
- **Reading**: Convert with `Emu(value).inches`