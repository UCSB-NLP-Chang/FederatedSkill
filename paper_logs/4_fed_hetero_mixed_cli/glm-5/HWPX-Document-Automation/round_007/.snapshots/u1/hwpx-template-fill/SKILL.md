---
name: hwpx-template-fill
description: Fill HWPX (Hancom Office) templates by replacing {{placeholders}} with values from JSON or a dict, or perform pattern-based text replacement when placeholders are absent. Use for Korean document automation, mail-merge, form generation, or data refresh when the input is a .hwpx file. Handles single or multi-section documents, table cells, and preserves unmodified content.
---

# Fill HWPX Template

HWPX files are ZIP archives containing XML (HWPML format). This skill performs placeholder substitution or pattern-based replacement while preserving document validity.

## Workflow

1. **Extract**: HWPX is a ZIP. Extract to a temporary directory.
2. **Locate**: Main content is in `Contents/section*.xml` files (section0.xml, section1.xml, etc.). Check `content.hpf` manifest if structure differs. Process ALL section files, not just section0.xml.
3. **Preprocess Values**: Transform raw values before replacement. Common needs:
   - **Unit stripping**: "32명" → "32" (remove counting units)
   - **Rating reformatting**: "4.5/5.0" → "4.5점 (5.0점 만점)" (Korean format)
   - **Text enrichment**: Append additional text (e.g., extend 종합의견)
   - **Phone normalization**: "01011112222" → "010-1111-2222"
   - **Date formatting**: Convert to target format (e.g., "2026-06-18" → "2026.06.18")
   - **Korean age**: Calculate from birth date
   - **Array mapping**: Map list items to numbered placeholders (e.g., `immediate_actions[0]` → `{{조치1}}`)
   - **Conditional enrichment**: Add status notes (e.g., "High" → "High (즉시조치)")
   
   See `references/value-preprocessing.md` for reusable code patterns.
4. **Replace**: Choose method based on document structure:
   - **Placeholder replacement**: Find `<hp:t>` text elements matching `{{key}}`, substitute with processed values. Use `scripts/fill_hwpx.py`.
   - **Exact string replacement**: Map old text to new text directly. Use `scripts/update_hwpx_direct.py`.
   - **Pattern-based replacement**: Find text by prefix pattern (e.g., "고객사: " followed by value) and replace. See `references/advanced-replacement.md`.
5. **Clean Layout Cache**: **Critical:** Remove sibling `<hp:linesegarray>` elements from any modified `<hp:p>` paragraphs—including those inside table cells. Failure causes overlapping/garbled characters.
6. **Repackage**: Zip contents back into `.hwpx` preserving directory structure.
7. **Verify**: Scan output to ensure expected changes applied and no unintended modifications.

## Critical Warning

**Always remove `<hp:linesegarray>` elements** from paragraphs where text is modified. This includes:
- Regular paragraphs (`<hp:p>` directly under `<hp:section>`)
- Table cell paragraphs (`<hp:p>` inside `<hp:tc>/<hp:subList>`)

These are pre-calculated layout caches that become invalid when text length changes. Hancom Office trusts these caches during rendering, resulting in unreadable overlapping text if stale caches remain.

## Usage

### Simple 1:1 Placeholder Replacement

```bash
python3 scripts/fill_hwpx.py template.hwpx output.hwpx data.json
```

### Exact String Replacement (No Placeholders)

When updating existing text without placeholders:

```bash
python3 scripts/update_hwpx_direct.py template.hwpx mapping.json output.hwpx
```

Where `mapping.json` is `{"old_text": "new_text", ...}`.

### With Value Preprocessing

When values need transformation (units, ratings, array mapping, status enrichment), preprocess first:

```python
import re
import json

# Load raw data
with open('raw_data.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)

# Preprocess
processed = {}
processed['참석자수'] = re.sub(r'[^0-9]', '', raw['참석자수'])  # "32명" → "32"
processed['만족도'] = raw['만족도'].replace('/', '점 (') + '점 만점)'  # "4.5/5.0" → "4.5점 (5.0점 만점)"
processed['종합의견'] = raw['종합의견'] + ' 후속 심화반 검토 요망.'  # Append text

# Fill
def fill_hwpx_template(template_path, output_path, data):
    # Implementation or import from scripts/fill_hwpx.py logic
    pass

fill_hwpx_template('template.hwpx', 'output.hwpx', processed)
```

For more preprocessing patterns (Korean age, phone normalization, array mapping, conditional enrichment), see `references/value-preprocessing.md`.

### Pattern-Based Replacement

When documents lack `{{placeholder}}` markers, use ElementTree to find and replace text by pattern:

```python
import xml.etree.ElementTree as ET

# Find text by prefix and replace the value portion
for t in root.iter('{http://www.hancom.co.kr/hwpml/2010/HWPML}t'):
    if t.text and t.text.startswith('고객사: '):
        t.text = f'고객사: {new_customer_name}'
        # Mark parent <hp:p> for linesegarray removal
```

For detailed patterns including table cell updates, date ranges, and CSV integration, see `references/advanced-replacement.md`.

## Verification Checklist

- Expected text changes applied in all relevant `Contents/section*.xml` files
- No `{{...}}` placeholders remain (if using placeholder mode)
- File remains a valid ZIP with entries `Contents/content.hpf` and `Contents/section*.xml`
- `<hp:linesegarray>` elements removed only from modified paragraphs (preserve in untouched paragraphs)
- Unmodified content preserved (verify by comparing unchanged sections)

## Known invariants (by sub-task)

### B1: HWPX Template Placeholder Fill + Preprocessing + Multi-Section + Direct Replacement
- `<hp:linesegarray>` elements must be removed from any modified `<hp:p>` paragraphs, including those inside table cells. Failure causes overlapping/garbled characters.
- Regex for linesegarray removal must match both self-closing `<hp:linesegarray />` and full `<hp:linesegarray>...</hp:linesegarray>` without overlapping; incorrect patterns leave orphaned `</hp:linesegarray>` closing tags.
- Multi-section documents: Process ALL `section*.xml` files, not just `section0.xml`.
- Values may require preprocessing before replacement (units, ratings, text enrichment, array mapping).
- Table cells contain nested `<hp:p>` elements inside `<hp:tc>/<hp:subList>` that follow the same rules as regular paragraphs.
- Handle `<hp:run>` splitting: HWPX often splits text across multiple `<hp:run>` tags. Do not run `str.replace()` on raw XML if it might cross tag boundaries.

## Anti-patterns

- **Do not** use `unzip`/`zip` CLI commands; environments often lack them. Use Python's `zipfile` module.
- **Do not** perform blind string replacement on the entire XML; use namespace-aware parsing to avoid breaking tags.
- **Do not** strip all `linesegarray` elements globally; only remove from paragraphs where text actually changed.
- **Do not** assume only `section0.xml` exists; always check for and process all `section*.xml` files.
- **Do not** add/remove files from the HWPX archive unless explicitly required.
- **Do not** assume `{{placeholder}}` syntax exists; check document structure first and use pattern-based replacement if needed.
- **Do not read from the ZIP file after its `with` block closes.** Always load all XML strings into a dictionary before closing the read context.

## Troubleshooting

**Overlapping characters after edit**: You failed to remove `<hp:linesegarray>` from modified paragraphs. Re-process and ensure the element is removed immediately after text replacement. Check table cell paragraphs too.

**Placeholder not replaced**: Verify the placeholder in XML exactly matches the JSON key including case. Check that the placeholder is inside `<hp:t>` and not split across multiple elements. If using multi-section documents, verify the placeholder wasn't in a section you missed (e.g., section1.xml).

**File corruption**: Ensure XML namespace declarations are preserved when writing. Use `ET.register_namespace()` with `http://www.hancom.co.kr/hwpml/2010/HWPML`.

**Incorrect values (units, ratings)**: Values were not preprocessed before replacement. Transform raw values (strip units, reformat ratings, append text) before calling the fill function. See `references/value-preprocessing.md` for patterns.

**Table cell text not updating**: Table cells contain `<hp:p>` elements inside `<hp:tc>/<hp:subList>`. Use ElementTree iteration to find these nested paragraphs, not just top-level `<hp:p>` elements.
