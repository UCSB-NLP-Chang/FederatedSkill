---
name: hwpx-editing
description: Edit HWPX (Hancom Office Word) files by extracting, modifying XML content, and repackaging. Use when tasks involve reading or modifying .hwpx files, replacing placeholders, generating Korean document templates, calculating derived values like phase durations, or applying value transformations (stripping units, reformatting scores, date formatting, appending text). Also use for Korean safety audit briefs, training feedback forms, project proposals, clinic intake summaries, and renewal playbooks. Two workflows exist: placeholder-based ({{field}} patterns) and direct value replacement (literal old→new mappings).
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

## Choose Your Workflow

| Scenario | Workflow | Tool |
|----------|----------|------|
| Document has `{{placeholder}}` patterns | Placeholder-based | `scripts/hwpx_replace.py` |
| Document has literal values to replace | Direct value replacement | Manual XML editing |
| Need calculated/derived values | Transform then use appropriate workflow | Python preprocessing |

## Workflow A: Placeholder-Based (Recommended)

For documents with `{{field_name}}` placeholders:

```bash
python3 scripts/hwpx_replace.py input.hwpx data.json output.hwpx
```

JSON maps placeholder names (without braces) to values:
```json
{"회사명": "ABC Corp", "담당자": "Kim"}
```

The script handles extraction, replacement, linesegarray removal (all from modified sections), and repackaging.

## Workflow B: Direct Value Replacement

For documents without placeholders (literal old values embedded):

1. **Extract**: Use Python zipfile to unpack
2. **Locate**: Search XML for old values across all section files
3. **Replace**: Substitute old→new values directly
4. **Clean**: Remove `<hp:linesegarray>` only from modified paragraphs
5. **Verify**: Confirm old values gone, static content preserved
6. **Repackage**: ZIP with Python zipfile

See `references/direct-value-replacement.md` for detailed patterns.

## Value Transformation Patterns

Apply these BEFORE building replacement dict or making direct replacements:

**Strip unit suffixes:**
```python
import re
def strip_unit(value: str, unit: str = '명') -> str:
    return re.sub(rf'{unit}$', '', value.strip())
# "32명" → "32"
```

**Reformat ratio scores:**
```python
def reformat_score(value: str) -> str:
    match = re.match(r'([\d.]+)/([\d.]+)', value.strip())
    if match:
        actual, maximum = match.groups()
        return f"{actual}점 ({maximum}점 만점)"
    return value
# "4.5/5.0" → "4.5점 (5.0점 만점)"
```

**Date format conversion:**
```python
# YYYY-MM-DD → YYYY.MM.DD (Korean official format)
korean_date = iso_date.replace('-', '.')
```

**Korean age (만 나이):**
```python
from datetime import datetime
birth = datetime.strptime(birth_date, '%Y-%m-%d')
visit = datetime.strptime(visit_date, '%Y-%m-%d')
age = visit.year - birth.year
if (visit.month, visit.day) < (birth.month, birth.day):
    age -= 1
# Format: f"{birth_date} ({age}세)"
```

**Phase duration calculation:**
```python
def month_span(start: str, end: str) -> int:
    """Calculate inclusive month difference from YYYY-MM strings."""
    s = datetime.strptime(start, '%Y-%m')
    e = datetime.strptime(end, '%Y-%m')
    return (e.year - s.year) * 12 + (e.month - s.month) + 1
# Append "(N개월)" to phase descriptions
```

## Critical Rules

### Linesegarray Handling
- **Placeholder workflow**: Remove ALL `<hp:linesegarray>` elements from modified section files (script does this automatically)
- **Direct replacement**: Remove ONLY from paragraphs you modify (preserves unmodified layout)

The layout cache becomes invalid when text changes; Hancom Office recalculates it on open.

### Data Provenance
- **Never fabricate values** — Always read from provided source files
- Cross-check filled values against original JSON inputs
- If multiple JSON files provided, merge them before processing

### Multi-Section Documents
Always check for `section0.xml`, `section1.xml`, etc.:
```python
sections = list(Path(work_dir / 'Contents').glob('section*.xml'))
```

### Table Content
Tables use nested structure: `<hp:tbl>` → `<hp:tr>` → `<hp:tc>` → `<hp:subList>` → `<hp:p>` → `<hp:run>` → `<hp:t>`. The text is still in `<hp:t>` elements.

## Verification (Portable)

```python
import zipfile, re

with zipfile.ZipFile('output.hwpx', 'r') as z:
    for name in z.namelist():
        if name.endswith('.xml'):
            content = z.read(name).decode('utf-8')
            # Check for remaining placeholders
            if re.search(r'\{\{[^}]+\}\}', content):
                print(f'WARNING: Placeholders remain in {name}')
            # Check old values not removed (direct replacement)
            if 'OldCompanyName' in content:
                print(f'WARNING: Old value remains in {name}')
```

## Anti-Patterns

| Don't | Why | Instead |
|-------|-----|---------|
| Use placeholder script for direct value replacement | Script expects `{{key}}` format | Use manual XML editing for literal values |
| Remove linesegarray from entire file (direct replacement) | Unnecessary layout recalculation | Remove only from modified paragraphs |
| Apply transformations after XML replacement | Brittle string matching | Transform in Python before replacement |
| Search `>value</hp:t>` when appending text | Fails if prefix/suffix exists | Search for value within text node |
| Hardcode data values | Verification failure | Always read from provided files |
| Assume single section file | Misses content in section1+ | Glob all section*.xml files |

## Task-Specific Patterns

### Safety Audit Brief
- Date: `2026-06-18` → `2026.06.18`
- Risk tier: `High` → `High(즉시조치)` via `{'High':'즉시조치','Medium':'계획보완','Low':'모니터링'}`
- Actions: Map array to `{{조치1}}`, `{{조치2}}`, etc.
- Check `audit_items` for table cell placeholders

### Training Feedback
- Strip units: `32명` → `32`
- Reformat scores: `4.5/5.0` → `4.5점 (5.0점 만점)`
- Append text to `종합의견` if required

### Project Proposal
- Calculate phase durations: `(N개월)` from date ranges
- Normalize budget: remove commas, keep `₩`

### Clinic Intake
- Korean age from birth+visit dates
- Phone normalize: `01000000000` → `010-0000-0000`

### Renewal Playbook
- Direct value replacement (no placeholders)
- Preserve appendix/static sections
- Update table cells in `<hp:tc>` elements

## References

- `scripts/hwpx_replace.py` — Placeholder-based replacement automation
- `references/direct-value-replacement.md` — Literal value replacement patterns
- `references/safety-audit-patterns.md` — Safety audit specific mappings

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| File won't open | Corrupt XML or invalid layout cache | Validate XML, check linesegarray removal |
| Text overlaps | Stale linesegarray in modified paragraph | Remove linesegarray from changed paragraphs |
| Old values remain | Incomplete replacement | Verify all sections searched, grep for remnants |
| Static content changed | Over-broad replacement | Use precise context strings, verify preservation |
| Korean text garbled | Encoding mismatch | Use UTF-8 for all XML operations |
| Table cells not updating | Wrong element targeted | Navigate to inner `<hp:t>` inside `<hp:tc>` |
