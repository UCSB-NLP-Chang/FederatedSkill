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

**Critical:** Remove `<hp:linesegarray>` elements from any modified `<hp:p>` paragraphs. These contain cached layout calculations that become invalid when text changes, causing rendering issues in Hancom Office.

### 5. Repackage
```bash
cd /tmp/hwpx_work && zip -r ../output.hwpx .
```

### 6. Verify
- Ensure no `{{...}}` placeholders remain
- Confirm file opens correctly in Hancom Office

## Common Patterns

| Pattern | Location | Action |
|---------|----------|--------|
| `{{field_name}}` | Inside `<hp:t>` | Replace with value |
| `<hp:linesegarray>` | Sibling of `<hp:run>` in `<hp:p>` | Remove if parent modified |
| Static text | `<hp:t>` without braces | Preserve unchanged |

## Anti-Patterns to Avoid

- **Don't** modify text without removing `<hp:linesegarray>` from the same paragraph — causes layout corruption
- **Don't** assume placeholder format; inspect actual file first (could be `{{field}}`, `${field}`, etc.)
- **Don't** use regex on binary ZIP; always extract first
- **Don't** preserve original compression metadata blindly; fresh ZIP is safer

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| File won't open in Hancom Office | Corrupt XML or invalid layout cache | Validate XML, remove `<hp:linesegarray>` from modified paragraphs |
| Text appears but layout is wrong | Stale `<hp:linesegarray>` cache | Remove all `<hp:linesegarray>` elements from modified `<hp:p>` nodes |
| Placeholders still visible | Replacement regex too narrow | Use broader pattern like `\{\{[^}]+\}\}` |

## Script Helper

For automated placeholder replacement, use:
```bash
python3 scripts/hwpx_replace.py /path/to/input.hwpx /path/to/data.json /path/to/output.hwpx
```

See `scripts/hwpx_replace.py` for the reference implementation.
