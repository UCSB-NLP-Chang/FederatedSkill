# Direct Value Replacement in HWPX

For documents without `{{placeholder}}` patterns, use direct string replacement on extracted XML.

## When to Use This Pattern

- Document contains literal values to update (e.g., "Northwind Retail" → "Asteron Commerce")
- No placeholder markup exists in the source
- Template was created by saving a filled document, not designed for automation
- Task specifies exact old→new value mappings

## Workflow

### 1. Extract and Inspect
```python
import zipfile, tempfile
work_dir = tempfile.mkdtemp()
with zipfile.ZipFile('input.hwpx', 'r') as z:
    z.extractall(work_dir)
```

Read all section XML files to locate target values:
```bash
grep -r "old_value" /tmp/hwpx_work/Contents/
```

### 2. Plan Replacements

Map each old value to its location:
| Old Value | File | Context | New Value |
|-----------|------|---------|-----------|
| Northwind Retail | section0.xml | 고객사: ... | Asteron Commerce |
| 2025-04-01 ~ 2025-04-15 | section1.xml | 갱신 윈도우 확인: ... | 2026-08-12 ~ 2026-08-26 |

### 3. Execute with Linesegarray Removal

For each modified paragraph, remove the entire `<hp:linesegarray>...</hp:linesegarray>` element:

```python
import re

# Read file
with open(xml_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace specific value
content = content.replace('old_value', 'new_value')

# Remove linesegarray from modified paragraph only
# Match the paragraph containing the change
old_para = '<hp:p id="43"...>...old_value...</hp:p>'
new_para = old_para.replace('old_value', 'new_value')
new_para = re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', new_para, flags=re.DOTALL)
content = content.replace(old_para, new_para)
```

**Critical difference from placeholder workflow:**
- Placeholder workflow: Remove ALL linesegarray elements from entire section files (simpler)
- Direct replacement: Remove only from paragraphs you modify (preserves unmodified layout)

### 4. Preserve Static Content

Explicitly verify preserved sections remain unchanged:
```python
assert '이 부록 문단은 그대로 유지해야 합니다.' in content
assert '기존 히스토리: 2025년 1분기 초안' in content
```

### 5. Verify No Duplicates

After replacement, confirm old values are gone:
```python
assert 'Northwind' not in content
assert '2025-04-01' not in content
```

## Common Patterns

### Table Cell Updates
Table content is nested deeper:
```xml
<hp:tc><hp:subList><hp:p><hp:run><hp:t>Priority-24M</hp:t></hp:run></hp:p></hp:subList></hp:tc>
```

Replace the inner `<hp:t>` text, then walk up to remove linesegarray from the containing `<hp:p>`.

### Multi-Section Documents
Documents may split content across `section0.xml`, `section1.xml`, etc. Search all sections:
```python
for section in ['section0.xml', 'section1.xml']:
    path = f'{work_dir}/Contents/{section}'
    if os.path.exists(path):
        # process
```

## Split Run Handling (Critical)

HWPX often breaks logical phrases across multiple `<hp:run>` elements. A phrase like "Northwind Retail" may appear in raw XML as:

```xml
<hp:t>Northwind </hp:t></hp:run><hp:run charPrIDRef="0"><hp:t>Retail</hp:t>
```

**Symptom**: Direct string replacement fails because the target is not contiguous in raw XML.

**Solution**: Use regex to bridge run boundaries:

```python
import re

# Bridge split runs across </hp:run><hp:run> boundaries
# Example: Replace "Northwind Retail" even when split
content = re.sub(
    r'Northwind\s*</hp:run><hp:run[^>]*>\s*Retail',
    'Asteron Commerce',
    content
)

# Generic pattern for split phrases:
# content = re.sub(r'Part1\s*</hp:run><hp:run[^>]*>\s*Part2', 'NewText', content)
```

**Verification**: Always verify rendered text by stripping XML tags, not raw XML:

```python
rendered = re.sub(r'<[^>]+>', '', content)  # Strip all tags
assert 'Asteron Commerce' in rendered
assert 'Northwind' not in rendered
```

## Verification Checklist

- [ ] All specified old values replaced
- [ ] No old values remain in output
- [ ] Static/preserved content unchanged
- [ ] Linesegarray removed from modified paragraphs only
- [ ] File repackages without errors
- [ ] Opens correctly in Hancom Office (test if possible)

## Anti-Patterns

- **Don't** use placeholder script (`hwpx_replace.py`) for direct value replacement - it expects `{{key}}` format
- **Don't** remove linesegarray from entire file when only few paragraphs changed - unnecessary layout recalculation
- **Don't** assume single section file - always check for `section0.xml`, `section1.xml`, etc.
- **Don't** rely on line numbers from grep - XML may be minified; search for context strings