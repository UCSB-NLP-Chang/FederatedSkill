# CSV-Driven Text Standardization

Patterns for replacing/updating text content based on external mapping files.

## Loading the Mapping

```python
import csv

def load_caption_map(csv_path):
    """Load raw -> canonical mapping from CSV.

    CSV format: raw,canonical
    Handles headers automatically if present.
    Skips empty rows, draft rows, and comment rows.
    """
    mapping = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        # Peek at first row to detect header
        first_row = next(reader, None)
        if first_row and not first_row[0].strip().startswith('#'):
            # Check if it looks like data (not header)
            if len(first_row) >= 2 and not first_row[0].lower() in ('raw', 'source', 'from'):
                mapping[first_row[0].strip()] = first_row[1].strip()

        for row in reader:
            if len(row) >= 2:
                mapping[row[0].strip()] = row[1].strip()
    return mapping
```

## Handling CSV Edge Cases

### Empty and Whitespace-Only Rows

```python
def load_caption_map_robust(csv_path):
    """Load mapping with robust edge case handling."""
    mapping = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        
        for i, row in enumerate(reader):
            # Skip empty rows
            if not row or all(cell.strip() == '' for cell in row):
                continue
            
            # Skip rows with insufficient columns
            if len(row) < 2:
                continue
            
            # Skip comment rows (start with #)
            if row[0].strip().startswith('#'):
                continue
            
            # Skip draft/placeholder rows (empty key or value)
            key = row[0].strip()
            value = row[1].strip()
            if not key or not value:
                continue
            
            # Skip header row (first row with typical header names)
            if i == 0 and key.lower() in ('raw', 'source', 'from', 'original', 'old'):
                continue
            
            mapping[key] = value
    
    return mapping
```

### Filtering Draft Rows by Convention

If your CSV uses a status column or draft markers:

```python
def load_caption_map_with_status(csv_path, status_col=2):
    """Load mapping, skipping rows marked as draft."""
    mapping = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        
        for i, row in enumerate(reader):
            if len(row) < 2:
                continue
            
            key = row[0].strip()
            value = row[1].strip()
            
            # Skip if key or value empty
            if not key or not value:
                continue
            
            # Check status column if present
            if len(row) > status_col:
                status = row[status_col].strip().lower()
                if status in ('draft', 'todo', 'skip', 'ignore'):
                    continue
            
            mapping[key] = value
    
    return mapping
```

## Finding and Replacing Text

### Exact Match Replacement

```python
for t_elem in root.findall('.//a:t', NS):
    original = t_elem.text
    if original in caption_map:
        t_elem.text = caption_map[original]
        print(f"Replaced: '{original}' -> '{caption_map[original]}'")
```

### Containment Match (Flexible)

When text might have surrounding whitespace or punctuation:

```python
def find_matching_key(text, mapping):
    """Find mapping key that matches text exactly or as substring."""
    if not text:
        return None
    text = text.strip()
    if text in mapping:
        return text
    # Check if any key is contained within text
    for key in mapping:
        if key in text:
            return key
    return None

for t_elem in root.findall('.//a:t', NS):
    original = t_elem.text
    key = find_matching_key(original, caption_map)
    if key:
        t_elem.text = original.replace(key, caption_map[key])
```

## Building Unique Lists in First-Appearance Order

For Evidence Log or summary slides:

```python
def extract_unique_captions_in_order(slide_files, z, caption_map, NS):
    """Extract unique standardized captions in first-appearance order."""
    seen = []
    for slide_file in slide_files:
        xml = z.read(slide_file).decode('utf-8')
        root = ET.fromstring(xml)

        for t_elem in root.findall('.//a:t', NS):
            text = t_elem.text
            if not text:
                continue

            # Check if this text matches any key in mapping
            key = find_matching_key(text, caption_map)
            if key:
                standardized = caption_map[key]
                if standardized not in seen:
                    seen.append(standardized)

    return seen
```

## Creating Numbered List from Unique Items

```python
def create_numbered_paragraphs(items, NS):
    """Create XML paragraphs with buAutoNum for each item."""
    paragraphs = []
    for i, item in enumerate(items):
        is_last = (i == len(items) - 1)
        end_para = '<a:endParaRPr lang="en-US"/>' if is_last else ''

        para_xml = f'''<a:p>
  <a:pPr><a:buAutoNum type="arabicPeriod" startAt="1"/></a:pPr>
  <a:r>
    <a:rPr lang="en-US" dirty="0" sz="1800">
      <a:solidFill><a:srgbClr val="000000"/></a:solidFill>
      <a:latin typeface="Arial"/>
      <a:ea typeface="Arial"/>
      <a:cs typeface="Arial"/>
    </a:rPr>
    <a:t>{item}</a:t>
  </a:r>
  {end_para}
</a:p>'''
        paragraphs.append(para_xml)

    return '\n'.join(paragraphs)
```

## Complete Integration Example

```python
# 1. Load mapping
caption_map = load_caption_map('evidence_caption_map.csv')

# 2. Process evidence slides (replace text + format)
for slide_file in slide_files:
    if slide_file == 'ppt/slides/slide7.xml':
        continue  # Handle summary slide separately

    xml = z.read(slide_file).decode('utf-8')
    root = ET.fromstring(xml)

    # Find caption shapes by name pattern or content
    for sp in root.findall('.//p:sp', NS):
        cNvPr = sp.find('p:nvSpPr/p:cNvPr', NS)
        if cNvPr is None:
            continue

        name = cNvPr.get('name', '')
        # Match Chinese "Text Box" or English variants
        if not (name.startswith('文本框') or 'Caption' in name):
            continue

        # Get full text from all runs
        texts = [t.text for t in sp.findall('.//a:t', NS) if t.text]
        full_text = ''.join(texts).strip()

        # Replace using mapping
        key = find_matching_key(full_text, caption_map)
        if key:
            # Update first run's text, clear others
            t_elems = sp.findall('.//a:t', NS)
            if t_elems:
                t_elems[0].text = caption_map[key]
                for t in t_elems[1:]:
                    t.text = ''

# 3. Build summary slide with unique items in order
unique_captions = extract_unique_captions_in_order(slide_files, z, caption_map, NS)
slide7_xml = create_evidence_log_slide(unique_captions)
```

## Validation Checklist

- [ ] All CSV keys accounted for (print warnings for unused mappings)
- [ ] No duplicates in unique list (verify `len(seen) == len(set(seen))`)
- [ ] Order preserved from first appearance
- [ ] Replacement didn't affect non-target shapes (check by ID or position)
- [ ] Chinese/no-English shape names handled correctly
- [ ] Empty rows, draft rows, and comment rows filtered out
- [ ] Validation output is consistent (no contradictory pass/fail messages)
