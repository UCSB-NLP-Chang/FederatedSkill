---
name: hwpx-editing
description: Edit HWPX (Hancom Office Word) files by extracting, modifying XML content, and repackaging. Use when tasks involve reading or modifying .hwpx files, replacing placeholders, generating Korean document templates, calculating derived values like phase durations, or applying value transformations (stripping units, reformatting scores, date formatting, appending text). Also use for Korean safety audit briefs, training feedback forms, project proposals, and clinic intake summaries.
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

## Quick Start

For automated placeholder replacement, use:
```bash
python3 scripts/hwpx_replace.py /path/to/input.hwpx /path/to/data.json /path/to/output.hwpx
```

The JSON should map placeholder names (without braces) to values:
```json
{"회사명": "ABC Corp", "담당자": "Kim"}
```

Placeholders in the document should use `{{name}}` format. The script handles multiple occurrences automatically.

## Manual Workflow

### 1. Read ALL Input Files First
**Before any processing, read every provided JSON/data file.** Never hardcode or fabricate values. If a file is mentioned in the task (e.g., `audit_overview.json`, `corrective_actions.json`), read it before processing.

When multiple JSON files are provided, merge them into a single replacement dict before filling:
```python
import json
data = {}
for path in ['audit_overview.json', 'corrective_actions.json', 'audit_items.json']:
    data.update(json.load(open(path)))
```

### 2. Extract the Archive

**Always use Python zipfile (portable, always available):**
```python
import zipfile, tempfile, os
work_dir = tempfile.mkdtemp()
with zipfile.ZipFile('input.hwpx', 'r') as z:
    z.extractall(work_dir)
```

Only use `unzip` if you have verified it exists:
```bash
which unzip && unzip -q input.hwpx -d /tmp/hwpx_work/
```

### 3. Locate Content Files
Read `Contents/content.hpf` to find the manifest, then read the referenced section XML files (typically `section0.xml`).

### 4. Identify Placeholders
Placeholders typically appear in `<hp:t>` text elements:
```xml
<hp:p id="1" paraPrIDRef="0">
  <hp:run charPrIDRef="0">
    <hp:t>회사명: {{회사명}}</hp:t>
  </hp:run>
  <hp:linesegarray>...</hp:linesegarray>  <!-- layout cache -->
</hp:p>
```

### 5. Replace Content
Replace `{{placeholder}}` patterns with actual values.

**Critical:** Remove ALL `<hp:linesegarray>` elements from any modified section file. The layout cache becomes invalid when text changes; Hancom Office recalculates it on open. Removing all elements is simpler and more reliable than tracking which paragraphs were modified.

**Placeholder Context Awareness:** Placeholders may not be the entire content of an `<hp:t>` element. They often have prefixes or suffixes:
```xml
<hp:t>1단계: {{단계1}}</hp:t>  <!-- placeholder has prefix "1단계: " -->
```

When doing post-replacement modifications (appending text, searching for replaced values):
- DO NOT search for `>value</hp:t>` — this fails when prefixes/suffixes exist
- DO search for the value within the text content, then find surrounding context
- If appending after value, search for value and insert before `</hp:t>`

### 6. Value Transformation Patterns

Common transformations for Korean document workflows:

**Strip unit suffixes (numeric fields):**
```python
import re

def strip_unit(value: str, unit: str = '명') -> str:
    """Remove unit suffix like '32명' -> '32'."""
    return re.sub(rf'{unit}$', '', value.strip())

# Examples:
# "32명" -> "32"
# "150건" -> "150" (with unit='건')
```

**Reformat ratio scores:**
```python
def reformat_score(value: str, pattern: str = r'([\d.]+)/([\d.]+)') -> str:
    """Convert '4.5/5.0' to '4.5점 (5.0점 만점)'."""
    match = re.match(pattern, value.strip())
    if match:
        actual, maximum = match.groups()
        return f"{actual}점 ({maximum}점 만점)"
    return value

# Example: "4.5/5.0" -> "4.5점 (5.0점 만점)"
```

**Append text to existing values:**
```python
def append_text(original: str, addition: str) -> str:
    """Append additional text with proper spacing."""
    return f"{original} {addition}" if not original.endswith(' ') else f"{original}{addition}"

# Example: "기초 개념 설명이..." + "후속 심화반 검토 요망."
```

**Apply transformations before replacement:**
```python
raw_data = json.load(open('data.json'))
transformed = {
    '참석자수': strip_unit(raw_data['참석자수'], '명'),
    '만족도': reformat_score(raw_data['만족도']),
    '종합의견': append_text(raw_data['종합의견'], '후속 심화반 검토 요망.'),
    # ... other fields pass through unchanged
}
```

### 7. Post-Processing: Derived Values

Some templates require calculated values appended to replaced text. Common pattern in Korean project documents:

**Phase duration calculation (개월):**
```python
from datetime import datetime

def month_span(start: str, end: str) -> int:
    """Calculate inclusive month difference from YYYY-MM strings."""
    s = datetime.strptime(start, '%Y-%m')
    e = datetime.strptime(end, '%Y-%m')
    return (e.year - s.year) * 12 + (e.month - s.month) + 1

# After replacing {{단계1}}, append duration
# Input:  "1단계: 요구사항 분석 및 설계 (2026-08 ~ 2026-10)"
# Output: "1단계: 요구사항 분석 및 설계 (2026-08 ~ 2026-10) (3개월)"
```

Apply this as a second pass after placeholder replacement, modifying the `<hp:t>` content directly.

### 8. Repackage

**Use Python (always works):**
```python
import zipfile, os

with zipfile.ZipFile('output.hwpx', 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(work_dir):
        for f in files:
            path = os.path.join(root, f)
            zf.write(path, os.path.relpath(path, work_dir))
```

Only use `zip` command as fallback after verifying availability.

### 9. Verify
- Ensure no `{{...}}` placeholders remain
- Verify zero `linesegarray` elements remain in modified section files
- Confirm file opens correctly in Hancom Office
- **Verify all data came from source files**: Cross-check filled values against original JSON inputs

## Common Patterns for Korean Documents

| Pattern | Location | Action |
|---------|----------|--------|
| `{{field_name}}` | Inside `<hp:t>` | Replace with value |
| `<hp:linesegarray>` | Layout cache in section XML | Remove ALL from modified section files |
| Static text | `<hp:t>` without braces | Preserve unchanged |
| Phase with date range | `<hp:t>` containing dates | Replace placeholder, then append `(N개월)` duration |
| Numeric with unit | Value like `32명`, `150건` | Strip unit suffix before replacement |
| Score ratio | Value like `4.5/5.0` | Reformat to `4.5점 (5.0점 만점)` |
| Append text | Free-form text field | Add supplementary text after original |

### Korean Age Calculation
For documents requiring Korean age (만 나이, full-year age):
```python
from datetime import datetime
birth = datetime.strptime(birth_date, '%Y-%m-%d')
visit = datetime.strptime(visit_date, '%Y-%m-%d')
age = visit.year - birth.year
if (visit.month, visit.day) < (birth.month, birth.day):
    age -= 1
# Format: f"{birth_date} ({age}세)"
```

### Phone Number Normalization
Standard Korean mobile format: `010-0000-0000`
```python
import re
phone = re.sub(r'\D', '', raw_phone)  # digits only
if len(phone) == 11:
    phone = f"{phone[:3]}-{phone[3:7]}-{phone[7:]}"
```

### Budget/Currency Normalization
Korean budget values often contain commas that should be removed while preserving the currency symbol:
```python
import re
def normalize_budget(raw: str) -> str:
    # Input: "₩450,000,000" -> Output: "₩450000000"
    return re.sub(r'(\d),(\d)', r'\1\2', raw)

# For thorough removal (multiple commas):
def normalize_budget_thorough(raw: str) -> str:
    while ',' in raw:
        raw = re.sub(r'(\d),(\d)', r'\1\2', raw)
    return raw
```

### Date Format Conversion
Korean documents often use `YYYY.MM.DD` format instead of ISO `YYYY-MM-DD`:
```python
# Convert ISO date to Korean format
iso_date = "2026-06-18"
korean_date = iso_date.replace('-', '.')  # "2026.06.18"
```

### Risk Tier with Severity Annotation
Safety audit documents often require risk tiers annotated with Korean severity notes:
```python
severity_map = {
    'High': '즉시조치',
    'Medium': '계획보완', 
    'Low': '모니터링'
}
risk_tier = "High"
risk_with_severity = f"{risk_tier}({severity_map[risk_tier]})"  # "High(즉시조치)"
```

## Anti-Patterns to Avoid

- **Don't fabricate or hardcode data values** — Always read from provided source files. If a file is mentioned in the task, read it before processing. Cross-check filled values against original inputs during verification.
- **Don't apply transformations unless explicitly required** — If the template expects `YYYY-MM-DD`, do not change to `YYYY.MM.DD`. If a field value is `"High"`, do not append text like `"High(즉시조치)"` unless the task or template explicitly requires it.
- **Don't** modify text without removing ALL `<hp:linesegarray>` elements from that section file — causes layout corruption (overlapping text)
- **Don't** assume placeholder format; inspect actual file first (could be `{{field}}`, `${field}`, `«field»`, etc.)
- **Don't** use regex on binary ZIP; always extract first
- **Don't** preserve original compression metadata blindly; fresh ZIP is safer
- **Don't** track modified paragraphs to selectively remove linesegarray — remove ALL instead
- **Don't** rely on `zip` command being available; use Python zipfile as primary approach
- **Don't** assume `{{key}}` is the only content in its `<hp:t>` element when doing post-replacement edits — placeholder may have prefix/suffix
- **Don't** apply transformations after XML replacement — transform values in Python before building replacement dict
- **Don't** only process obvious placeholders — inspect ALL JSON data sections; tables and lists often need mapping to numbered placeholders like `{{조치1}}`, `{{조치2}}`, etc.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### hwpx-template-fill
- Output XML must NOT contain `linesegarray` elements in modified section files — remove ALL after editing.
- `{{...}}` placeholder format is standard; Korean field names like `{{회사명}}` are common.

### hwpx-clinic-intake-summary
- Korean age (만 나이) requires birth date + visit date calculation; do not pass raw birth date to age placeholders.
- Phone numbers must be normalized to `010-0000-0000` format.

### hwpx-project-proposal
- Phase descriptions may need duration appended: calculate month span from date ranges and add `(N개월)` suffix.
- Budget values may need normalization (remove commas, keep currency symbol).

### hwpx-training-feedback
- Numeric fields like `참석자수` often have unit suffixes (`32명`) that must be stripped.
- Score fields like `만족도` use ratio format (`4.5/5.0`) that should be reformatted to Korean style.
- Free-form text fields like `종합의견` may need additional text appended.

### hwpx-safety-audit-brief
- **CRITICAL**: Process ALL data sections from input JSON, not just `summary` and `immediate_actions`. Audit items tables often need individual cell mapping.
- Date format must be converted: `2026-06-18` → `2026.06.18`
- Risk tier requires severity annotation: `High` → `High(즉시조치)` using mapping `{'High':'즉시조치','Medium':'계획보완','Low':'모니터링'}`
- Corrective actions map to numbered placeholders: `{{조치1}}`, `{{조치2}}`, `{{조치3}}` from array indices
- Verify all placeholders including `{{보고대상}}` and any table cell placeholders are filled

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
            if '<hp:linesegarray>' in content:
                print(f'WARNING: Layout cache remains in {name}')
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| File won't open in Hancom Office | Corrupt XML or invalid layout cache | Validate XML, remove ALL `<hp:linesegarray>` from modified section files |
| Text appears but layout is wrong | Stale `<hp:linesegarray>` cache | Remove ALL `<hp:linesegarray>` elements from modified section files: `re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', content, flags=re.DOTALL)` |
| Layout cache not fully removed | Script tracked modified paragraphs (brittle) | Always remove ALL `<hp:linesegarray>` elements from modified section files, not just modified paragraphs |
| Placeholders still visible | Replacement regex too narrow | Use broader pattern like `\{\{[^}]+\}\}` |
| `unzip` or `zip` not found | Minimal environment | Use Python zipfile module as primary approach |
| Korean text garbled | Encoding mismatch | Ensure UTF-8 for all XML read/write operations |
| Phase durations missing | Calculated values not appended | Add second pass to append `(N개월)` after placeholder replacement |
| Post-replacement append fails | Searching `>value</hp:t>` when placeholder has prefix/suffix | Inspect XML to find actual text structure; search for value within text node, not wrapped form |
| Unit suffixes appear in output | Forgot to strip '명', '건', etc. | Apply `strip_unit()` transformation before building replacement dict |
| Score format inconsistent | Raw ratio passed through | Apply `reformat_score()` transformation for ratio values |
| Verifier fails on safety audit | Missing table data or unmapped fields | Check for `audit_items` or similar nested data requiring numbered placeholder mapping; verify `{{보고대상}}` and all action placeholders |
| Date format mismatch | Template expects `YYYY.MM.DD` but received `YYYY-MM-DD` | Apply `iso_date.replace('-', '.')` transformation; Korean official documents often use dot-separated dates |
| Data provenance failure | Hardcoded or fabricated values | Cross-check each filled value against original JSON inputs; never fabricate data |

## Script Reference

See `scripts/hwpx_replace.py` for the reference implementation covering:
- ZIP extraction/repackaging
- Placeholder regex replacement (handles multiple occurrences)
- Automatic `linesegarray` removal from all modified section files
- Verification of remaining placeholders

For value transformations, apply them in Python before calling the script or adapt the script to include transformation hooks.
