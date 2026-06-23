---
name: hwpx-editing
description: Edit HWPX (Hancom Office Word) files by extracting, modifying XML content, and repackaging. Use when tasks involve reading or modifying .hwpx files, replacing placeholders, generating Korean document templates, or calculating derived values like phase durations that must be appended to replaced text.
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

### 1. Extract the Archive

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

**Placeholder Context Awareness:** Placeholders may not be the entire content of an `<hp:t>` element. They often have prefixes or suffixes:
```xml
<hp:t>1단계: {{단계1}}</hp:t>  <!-- placeholder has prefix "1단계: " -->
```

When doing post-replacement modifications (appending text, searching for replaced values):
- DO NOT search for `>value</hp:t>` — this fails when prefixes/suffixes exist
- DO search for the value within the text content, then find surrounding context
- If appending after value, search for value and insert before `</hp:t>`

### 5. Post-Processing: Derived Values

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

### 6. Repackage

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

### 7. Verify
- Ensure no `{{...}}` placeholders remain
- Confirm file opens correctly in Hancom Office

## Common Patterns for Korean Documents

| Pattern | Location | Action |
|---------|----------|--------|
| `{{field_name}}` | Inside `<hp:t>` | Replace with value |
| `<hp:linesegarray>` | Layout cache in section XML | Remove ALL from modified section files |
| Static text | `<hp:t>` without braces | Preserve unchanged |
| Phase with date range | `<hp:t>` containing dates | Replace placeholder, then append `(N개월)` duration |

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

## Anti-Patterns to Avoid

- **Don't** modify text without removing ALL `<hp:linesegarray>` elements from that section file — causes layout corruption (overlapping text)
- **Don't** assume placeholder format; inspect actual file first (could be `{{field}}`, `${field}`, `«field»`, etc.)
- **Don't** use regex on binary ZIP; always extract first
- **Don't** preserve original compression metadata blindly; fresh ZIP is safer
- **Don't** track modified paragraphs to selectively remove linesegarray — remove ALL instead
- **Don't** rely on `zip` command being available; use Python zipfile as primary approach
- **Don't** assume `{{key}}` is the only content in its `<hp:t>` element when doing post-replacement edits — placeholder may have prefix/suffix

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

## Script Reference

See `scripts/hwpx_replace.py` for the reference implementation covering:
- ZIP extraction/repackaging
- Placeholder regex replacement (handles multiple occurrences)
- Automatic `linesegarray` removal from all modified section files
- Verification of remaining placeholders
