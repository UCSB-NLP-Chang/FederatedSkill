# Advanced HWPX Replacement Patterns

Patterns for HWPX updates when documents lack `{{placeholder}}` markers or require special handling.

## Pattern-Based Text Replacement

When documents use static text instead of placeholders, find and replace by pattern.

### Prefix-Based Replacement

Find text by prefix and replace the value portion:

```python
import xml.etree.ElementTree as ET

def replace_by_prefix(root, prefix, new_value, ns={'hp': 'http://www.hancom.co.kr/hwpml/2010/HWPML'}):
    """Replace text that starts with a known prefix.
    
    Example: "고객사: Northwind Retail" → "고객사: Asteron Commerce"
    """
    modified_paras = set()
    for t in root.iter('{http://www.hancom.co.kr/hwpml/2010/HWPML}t'):
        if t.text and prefix in t.text:
            # Replace the portion after the prefix
            idx = t.text.find(prefix)
            t.text = t.text[:idx + len(prefix)] + new_value
            # Track parent paragraph for linesegarray removal
            p = t.getparent()  # <hp:run>
            while p is not None and not p.tag.endswith('p'):
                p = p.getparent()
            if p is not None:
                modified_paras.add(p.get('id'))
    return modified_paras
```

### Date Range Replacement

Replace date ranges with new values:

```python
import re

def replace_date_range(root, new_start, new_end, ns={'hp': 'http://www.hancom.co.kr/hwpml/2010/HWPML'}):
    """Replace date range patterns like '2025-04-01 ~ 2025-04-15'.
    
    Example: "2025-04-01 ~ 2025-04-15" → "2026-08-12 ~ 2026-08-26"
    """
    date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}\s*~\s*\d{4}-\d{2}-\d{2}')
    modified_paras = set()
    
    for t in root.iter('{http://www.hancom.co.kr/hwpml/2010/HWPML}t'):
        if t.text and date_pattern.search(t.text):
            t.text = date_pattern.sub(f'{new_start} ~ {new_end}', t.text)
            # Track for linesegarray removal
            p = t.getparent()
            while p is not None and not p.tag.endswith('p'):
                p = p.getparent()
            if p is not None:
                modified_paras.add(p.get('id'))
    
    return modified_paras
```

## Table Cell Handling

Tables contain nested `<hp:p>` elements inside `<hp:tc>` cells. These require the same `linesegarray` handling.

### Table Structure

```xml
<hp:tbl id="200">
  <hp:tr>
    <hp:tc borderFillIDRef="1">
      <hp:subList textDirection="HORIZONTAL" vertAlign="CENTER">
        <hp:p id="30" paraPrIDRef="0">
          <hp:run charPrIDRef="0"><hp:t>가격 밴드</hp:t></hp:run>
        </hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="0" rowAddr="0"/>
    </hp:tc>
    <hp:tc borderFillIDRef="1">
      <hp:subList textDirection="HORIZONTAL" vertAlign="CENTER">
        <hp:p id="31" paraPrIDRef="0">
          <hp:run charPrIDRef="0"><hp:t>Standard-18M</hp:t></hp:run>
          <hp:linesegarray>...</hp:linesegarray>  <!-- Remove if text changes -->
        </hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="1" rowAddr="0"/>
    </hp:tc>
  </hp:tr>
</hp:tbl>
```

### Updating Table Cells

```python
def update_table_cell(root, cell_id, new_text, ns={'hp': 'http://www.hancom.co.kr/hwpml/2010/HWPML'}):
    """Update text in a table cell paragraph by ID.
    
    Args:
        root: XML root element
        cell_id: The id attribute of the <hp:p> element inside the table cell
        new_text: New text content
    """
    for p in root.iter('{http://www.hancom.co.kr/hwpml/2010/HWPML}p'):
        if p.get('id') == cell_id:
            for t in p.iter('{http://www.hancom.co.kr/hwpml/2010/HWPML}t'):
                t.text = new_text
                break
            # Remove linesegarray from this paragraph
            remove_linesegarray(p)
            return True
    return False

def remove_linesegarray(paragraph):
    """Remove hp:linesegarray from a paragraph element."""
    ns = {'hp': 'http://www.hancom.co.kr/hwpml/2010/HWPML'}
    for lineseg in paragraph.findall('.//hp:linesegarray', ns):
        paragraph.remove(lineseg)
```

## CSV Data Integration

Import list data from CSV files and map to document fields.

### Reading CSV with Sequence Ordering

```python
import csv

def load_ordered_items(csv_path, key_column='sequence'):
    """Load items from CSV ordered by sequence column.
    
    Args:
        csv_path: Path to CSV file
        key_column: Column name for ordering (default: 'sequence')
    
    Returns:
        List of tuples: [(sequence, item_text), ...]
    """
    items = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            seq = int(row.get(key_column, 0))
            text = row.get('item', row.get('text', row.get('description', '')))
            items.append((seq, text))
    
    return sorted(items, key=lambda x: x[0])

# Usage
follow_ups = load_ordered_items('follow_ups.csv')
# [(1, '보안 검토 완료 일정을 고객과 다시 확인'), 
#  (2, '결재 라인에 최신 가격 밴드를 반영'),
#  (3, '갱신 주간에 에스컬레이션 연락처를 온콜로 고정')]
```

### Mapping CSV Items to Numbered Paragraphs

```python
def update_numbered_items(root, items, start_para_id, ns={'hp': 'http://www.hancom.co.kr/hwpml/2010/HWPML'}):
    """Replace numbered list items in document.
    
    Args:
        root: XML root element
        items: List of (sequence, text) tuples
        start_para_id: ID of first paragraph to update
    """
    for seq, text in items:
        para_id = start_para_id + seq - 1  # Assuming consecutive IDs
        for p in root.iter('{http://www.hancom.co.kr/hwpml/2010/HWPML}p'):
            if p.get('id') == str(para_id):
                for t in p.iter('{http://www.hancom.co.kr/hwpml/2010/HWPML}t'):
                    t.text = f'{seq}. {text}'
                    break
                remove_linesegarray(p)
                break
```

## Preserving Unmodified Content

When updating specific fields, ensure other content remains unchanged.

### Selective Update Pattern

```python
def update_document(template_path, output_path, updates):
    """Update specific fields while preserving other content.
    
    Args:
        template_path: Path to input HWPX
        output_path: Path for output HWPX
        updates: Dict mapping field names to new values
    """
    import zipfile
    import io
    
    # Extract
    with zipfile.ZipFile(template_path, 'r') as zin:
        files = {name: zin.read(name) for name in zin.namelist()}
    
    modified_paras = set()
    
    # Process each section
    for name in files:
        if name.startswith('Contents/section') and name.endswith('.xml'):
            root = ET.fromstring(files[name])
            
            # Apply updates by pattern
            if 'customer' in updates:
                modified_paras.update(
                    replace_by_prefix(root, '고객사: ', updates['customer'])
                )
            if 'owner' in updates:
                modified_paras.update(
                    replace_by_prefix(root, '현 담당자: ', updates['owner'])
                )
            # ... more updates
            
            # Remove linesegarray from modified paragraphs
            for p in root.iter('{http://www.hancom.co.kr/hwpml/2010/HWPML}p'):
                if p.get('id') in modified_paras:
                    remove_linesegarray(p)
            
            files[name] = ET.tostring(root, encoding='unicode')
    
    # Repackage
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, content in files.items():
            zout.writestr(name, content)
```

## Complete Example: Renewal Playbook Update

```python
import xml.etree.ElementTree as ET
import zipfile
import csv
import io
from datetime import datetime

def update_renewal_playbook(hwpx_path, json_data, csv_path, output_path):
    """Update a renewal playbook HWPX with new customer data.
    
    Args:
        hwpx_path: Path to template HWPX
        json_data: Dict with customer, owner, dates, etc.
        csv_path: Path to CSV with follow-up items
        output_path: Path for output HWPX
    """
    ns = {'hp': 'http://www.hancom.co.kr/hwpml/2010/HWPML'}
    
    # Load follow-ups from CSV
    follow_ups = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            follow_ups.append((int(row['sequence']), row['item']))
    follow_ups.sort(key=lambda x: x[0])
    
    # Extract HWPX
    with zipfile.ZipFile(hwpx_path, 'r') as zin:
        files = {name: zin.read(name) for name in zin.namelist()}
    
    modified_paras = set()
    
    # Process sections
    for name in files:
        if not (name.startswith('Contents/section') and name.endswith('.xml')):
            continue
        
        root = ET.fromstring(files[name])
        
        # Update fields by pattern
        for t in root.iter('{http://www.hancom.co.kr/hwpml/2010/HWPML}t'):
            text = t.text or ''
            
            # Customer name
            if '고객사:' in text or '고객사: ' in text:
                t.text = f"고객사: {json_data['customer']}"
                modified_paras.add(get_parent_para_id(t))
            
            # Owner
            elif '현 담당자:' in text:
                t.text = f"현 담당자: {json_data['owner_name']}"
                modified_paras.add(get_parent_para_id(t))
            
            # Date range
            elif re.search(r'\d{4}-\d{2}-\d{2}\s*~\s*\d{4}-\d{2}-\d{2}', text):
                t.text = re.sub(
                    r'\d{4}-\d{2}-\d{2}\s*~\s*\d{4}-\d{2}-\d{2}',
                    f"{json_data['window_start']} ~ {json_data['window_end']}",
                    text
                )
                modified_paras.add(get_parent_para_id(t))
        
        # Update table cells (price band, escalation email)
        for p in root.iter('{http://www.hancom.co.kr/hwpml/2010/HWPML}p'):
            para_id = p.get('id')
            for t in p.iter('{http://www.hancom.co.kr/hwpml/2010/HWPML}t'):
                text = t.text or ''
                if text == 'Standard-18M':  # Old price band
                    t.text = json_data['band']
                    modified_paras.add(para_id)
                elif '@' in text and 'example' in text:  # Email pattern
                    t.text = json_data['escalation_email']
                    modified_paras.add(para_id)
        
        # Update follow-up items
        for seq, item in follow_ups:
            para_id = str(40 + seq)  # Assuming IDs 41, 42, 43...
            for p in root.iter('{http://www.hancom.co.kr/hwpml/2010/HWPML}p'):
                if p.get('id') == para_id:
                    for t in p.iter('{http://www.hancom.co.kr/hwpml/2010/HWPML}t'):
                        t.text = f'{seq}. {item}'
                    modified_paras.add(para_id)
        
        # Remove linesegarray from modified paragraphs
        for p in root.iter('{http://www.hancom.co.kr/hwpml/2010/HWPML}p'):
            if p.get('id') in modified_paras:
                for ls in p.findall('.//hp:linesegarray', ns):
                    p.remove(ls)
        
        files[name] = ET.tostring(root, encoding='unicode')
    
    # Repackage
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, content in files.items():
            zout.writestr(name, content.encode('utf-8'))

def get_parent_para_id(element):
    """Get the id of the parent <hp:p> element."""
    parent = element.getparent() if hasattr(element, 'getparent') else None
    while parent is not None:
        if parent.tag.endswith('p'):
            return parent.get('id')
        parent = parent.getparent() if hasattr(parent, 'getparent') else None
    return None
```