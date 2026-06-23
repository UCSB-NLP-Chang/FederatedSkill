# Auto-Numbered Bullets in python-pptx

`python-pptx` lacks high-level API support for auto-numbered lists. You must inject `<a:buAutoNum>` into the paragraph properties XML.

## XML Injection Pattern
```python
from lxml import etree
from pptx.oxml.ns import qn

def add_auto_number(paragraph, num_type="arabicPeriod"):
    pPr = paragraph._p.get_or_add_pPr()
    buAutoNum = etree.SubElement(pPr, qn('a:buAutoNum'))
    buAutoNum.set('type', num_type)
```

## Common `type` Values
- `arabicPeriod`: 1., 2., 3.
- `alphaLcParenR`: a), b), c)
- `alphaUcParenR`: A), B), C)
- `romanLcPeriod`: i., ii., iii.
- `arabicPlain`: 1, 2, 3

## Verification
After saving, extract `ppt/slides/slideN.xml` and search for `<a:buAutoNum type="..."/>` to confirm rendering will work in PowerPoint.
