# CSV-Driven Text Standardization

## Load Mapping (with edge case handling)

```python
import csv

def load_caption_map(csv_path):
    mapping = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if len(row) < 2: continue
            key, val = row[0].strip(), row[1].strip()
            # Skip: empty, comment (#), draft rows, header row
            if not key or not val: continue
            if key.startswith('#'): continue
            if i == 0 and key.lower() in ('raw', 'source', 'from', 'original'): continue
            mapping[key] = val
    return mapping
```

## Find & Replace Text

```python
def find_matching_key(text, mapping):
    if text in mapping: return text
    for key in mapping:
        if key in text: return key  # substring match
    return None

for t_elem in root.findall('.//a:t', NS):
    key = find_matching_key(t_elem.text, mapping)
    if key: t_elem.text = t_elem.text.replace(key, mapping[key])
```

## Caption Shape Identification

Match by name pattern (`文本框 N`) or text content search:
```python
for sp in root.findall('.//p:sp', NS):
    name = sp.find('p:nvSpPr/p:cNvPr', NS).get('name', '')
    if name.startswith('文本框'):  # Chinese "Text Box"
        texts = [t.text for t in sp.findall('.//a:t', NS) if t.text]
        # process shape...
```

## buAutoNum Pattern

Each `<a:p>` with `startAt="1"`:
```xml
<a:p>
  <a:pPr><a:buAutoNum type="arabicPeriod" startAt="1"/></a:pPr>
  <a:r><a:rPr lang="en-US"/><a:t>Item</a:t></a:r>
</a:p>
```

## Bottom-Center Position

```python
x = (SLIDE_WIDTH - box_width) // 2  # 12192000 EMUs wide
y = SLIDE_HEIGHT - box_height - margin  # 6858000 EMUs tall
```

## Validation

- All CSV keys accounted for
- No duplicates in extracted list
- Order preserved from first appearance