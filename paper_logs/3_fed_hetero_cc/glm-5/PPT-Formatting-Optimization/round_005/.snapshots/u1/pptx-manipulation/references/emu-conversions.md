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
Emu(914400)   # 914400 EMUs (1 inch)
```

## Reading Existing Values

```python
from pptx.util import Emu

# Convert EMU to inches for display
left_inches = Emu(shape.left).inches
top_inches = Emu(shape.top).inches
width_inches = Emu(shape.width).inches
```

## Slide Dimensions (Standard 16:9)

| Property | EMUs | Inches |
|----------|------|--------|
| Width | 12192000 | 13.33 |
| Height | 6858000 | 7.5 |

```python
slide_width = prs.slide_width   # EMUs
slide_height = prs.slide_height  # EMUs
```

## Common Point Sizes to EMU

| Points | EMU |
|--------|-----|
| 8pt | 101600 |
| 10pt | 127000 |
| 12pt | 152400 |
| 14pt | 177800 |
| 16pt | 203200 |
| 18pt | 228600 |
| 24pt | 304800 |
| 36pt | 457200 |
| 48pt | 609600 |