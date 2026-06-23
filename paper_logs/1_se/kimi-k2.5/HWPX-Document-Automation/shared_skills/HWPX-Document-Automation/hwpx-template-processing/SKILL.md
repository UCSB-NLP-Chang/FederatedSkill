---
name: hwpx-template-processing
description: Fill templates in HWPX (Hancom Office XML) files by replacing {{placeholder}} markers with data from JSON or other sources. Use when you need to programmatically generate .hwpx documents from templates containing field placeholders, especially for Korean documents requiring data transformations like age calculation, budget formatting, date reformatting, or severity annotation.
---

# HWPX Template Processing

HWPX files are ZIP archives containing XML documents. Templates use `{{field_name}}` placeholders that must be replaced with actual values.

## Quick Start: Use the Helper Script First

**ALWAYS try the helper script before writing custom code.** This is the fastest, most reliable path.

```bash
python scripts/fill_hwpx_template.py input.hwpx data.json output.hwpx
```

The script handles:
- Placeholder replacement across all section XML files
- Layout cache (`<hp:linesegarray>`) removal from modified paragraphs
- Verification that no placeholders remain
- Common transforms (age calculation, phone normalization)

### When the CLI Works
- Template has `{{placeholders}}` matching your JSON keys
- No complex field name mapping needed
- Standard transforms only (dates, phones, ages)

## When to Write Custom Code

Import `fill_hwpx_template()` when you need transforms the CLI doesn't provide:

| Scenario | Solution |
|----------|----------|
| JSON keys don't match placeholders | Use `field_mapping` parameter |
| CSV data source | Load CSV, convert to dict, then call function |
| Complex conditional logic | Custom transformer functions |
| Multi-source data merging | Merge dicts first, then call function |

### Custom Transformer Examples

```python
from scripts.fill_hwpx_template import fill_hwpx_template

field_mapping = {
    'customer': '고객사',      # JSON key → placeholder name
    'owner': '담당자',
}

transformers = {
    'window_start': lambda v, d: v.replace('-', '.'),
    'risk_level': lambda v, d: f"{v} (즉시조치)" if v == "High" else v,
}

result = fill_hwpx_template(
    'input.hwpx', 
    data, 
    'output.hwpx',
    field_mapping=field_mapping,
    transformers=transformers
)

assert result['placeholders_remaining'] == 0
```

## Critical Implementation Rules

### 1. Remove Layout Cache After Replacement

Always strip `<hp:linesegarray>` from modified paragraphs to prevent character overlap:

```python
xml_content = re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', xml_content, flags=re.DOTALL)
```

### 2. Use Regex Replacement, Not XML Parsing

- **Correct**: String regex on raw XML content
- **Wrong**: DOM parsers (lose formatting, namespace prefixes)

### 3. Preserve Static Content

Only modify paragraphs where text content actually changes. Copy unmodified entries from source ZIP. Preserve empty paragraphs (`<hp:t />`) used for spacing.

## Anti-Patterns (Never Do These)

| Don't | Why | Instead |
|-------|-----|---------|
| Write one-off script first | Duplicates tested code, introduces bugs | Use `fill_hwpx_template.py` |
| Use CLI `unzip` | Often unavailable in containers | Use `zipfile` module |
| Parse with DOM/trees | Destroys formatting | Regex on raw strings |
| Skip layout cache removal | Causes overlap/misalignment | Always strip `<hp:linesegarray>` |
| Calculate durations with month subtraction | Wrong for partial months | Parse full dates, use relativedelta |

## Verification

After generating the output, verify placeholders were replaced:

```python
import zipfile
import re

with zipfile.ZipFile('output.hwpx', 'r') as z:
    for name in z.namelist():
        if name.endswith('.xml'):
            content = z.read(name).decode('utf-8')
            remaining = re.findall(r'\{\{[^}]+\}\}', content)
            if remaining:
                print(f"Unreplaced in {name}: {remaining}")
```

## References

- `references/hwpx-structure.md` — File format, namespaces, placeholder patterns
- `scripts/fill_hwpx_template.py` — Production-ready helper with verification
