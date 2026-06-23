---
name: hwpx-editing
description: Edit HWPX (Hancom Office Word) files by extracting, modifying XML content, and repackaging. Use when tasks involve reading or modifying .hwpx files, replacing placeholders, or generating Korean document templates.
---

# HWPX Document Editing

HWPX is Hancom Office's XML-based word processing format. It uses the Open Container Format (OCF) — essentially a ZIP archive with structured XML content.

## File Structure

```
archive.hwpx/
├── Contents/
│   ├── content.hpf          # Package manifest (OPF format)
│   ├── section0.xml         # Main document content (HWPML)
│   └── section1.xml         # Additional sections if present
└── META-INF/
    └── container.xml        # Container metadata
```

Key namespaces:
- `hp:` = Hancom HWPML 2010 (`http://www.hancom.co.kr/hwpml/2010/HWPML`)
- `opf:` = Open Packaging Format (`http://www.idpf.org/2007/opf`)

## Workflow

### 1. Extract the Archive
```bash
unzip -q input.hwpx -d /tmp/hwpx_work/
```

If `unzip` is unavailable, use Python:
```python
import zipfile
with zipfile.ZipFile('input.hwpx', 'r') as z:
    z.extractall('/tmp/hwpx_work/')
```

### 2. Locate Content Files
Read `Contents/content.hpf` to find the manifest, then read the referenced section XML files (typically `section0.xml`).

### 3. Identify Placeholders
Placeholders typically appear in `<hp:t>` text elements:
```xml
<hp:p id="1" paraPrIDRef="0">
  <hp:run charPrIDRef="0">
    <hp:t>회사명: {{회사명}}</hp:t>
  </hp:run>
  <hp:linesegarray>...</hp:linesegarray>  <!-- layout cache -->
</hp:p>
```

### 4. Replace Content
Replace `{{placeholder}}` patterns with actual values.

**Critical:** Remove ALL `<hp:linesegarray>` elements from any modified section file. The layout cache becomes invalid when text changes; Hancom Office recalculates it on open. Removing all elements is simpler and more reliable than tracking which paragraphs were modified.

### 5. Repackage
```bash
cd /tmp/hwpx_work && zip -r ../output.hwpx .
```

Or with Python:
```python
import zipfile, os
with zipfile.ZipFile('output.hwpx', 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('/tmp/hwpx_work'):
        for f in files:
            path = os.path.join(root, f)
            zf.write(path, os.path.relpath(path, '/tmp/hwpx_work'))
```

### 6. Verify
- Ensure no `{{...}}` placeholders remain
- Confirm file opens correctly in Hancom Office

## Quick Replacement (Recommended)

For automated placeholder replacement, use:
```bash
python3 scripts/hwpx_replace.py /path/to/input.hwpx /path/to/data.json /path/to/output.hwpx
```

The JSON should map placeholder names (without braces) to values:
```json
{"회사명": "ABC Corp", "담당자": "Kim"}
```

Placeholders in the document should use `{{name}}` format.

## Common Patterns

| Pattern | Location | Action |
|---------|----------|--------|
| `{{field_name}}` | Inside `<hp:t>` | Replace with value |
| `<hp:linesegarray>` | Layout cache in section XML | Remove ALL from modified section files |
| Static text | `<hp:t>` without braces | Preserve unchanged |

## Anti-Patterns to Avoid

- **Don't** modify text without removing ALL `<hp:linesegarray>` elements from that section file — causes layout corruption (overlapping text)
- **Don't** assume placeholder format; inspect actual file first (could be `{{field}}`, `${field}`, `«field»`, etc.)
- **Don't** use regex on binary ZIP; always extract first
- **Don't** preserve original compression metadata blindly; fresh ZIP is safer

## Verification (Portable)

If system tools are unavailable, verify with Python:
```python
import zipfile, re

# Check archive integrity
with zipfile.ZipFile('output.hwpx', 'r') as z:
    print('Files:', z.namelist())
    # Check for remaining placeholders
    for name in z.namelist():
        if name.endswith('.xml'):
            content = z.read(name).decode('utf-8')
            if re.search(r'\{\{[^}]+\}\}', content):
                print(f'WARNING: Placeholders remain in {name}')
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| File won't open in Hancom Office | Corrupt XML or invalid layout cache | Validate XML, remove ALL `<hp:linesegarray>` from modified section files |
| Text appears but layout is wrong | Stale `<hp:linesegarray>` cache | Remove ALL `<hp:linesegarray>` elements from modified section files: `re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', content, flags=re.DOTALL)` |
| Layout cache not fully removed | Script tracked modified paragraphs (brittle) | Always remove ALL `<hp:linesegarray>` elements from modified section files, not just modified paragraphs |
| Placeholders still visible | Replacement regex too narrow | Use broader pattern like `\{\{[^}]+\}\}` |
| `unzip` or `file` not found | Minimal environment | Use Python zipfile module as fallback |
| Korean text garbled | Encoding mismatch | Ensure UTF-8 for all XML read/write operations |

## Script Reference

See `scripts/hwpx_replace.py` for the reference implementation covering:
- ZIP extraction/repackaging
- Placeholder regex replacement
- Automatic `linesegarray` removal
- Verification of remaining placeholders
