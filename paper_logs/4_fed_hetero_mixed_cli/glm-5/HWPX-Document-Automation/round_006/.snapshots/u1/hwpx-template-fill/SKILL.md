---
name: hwpx-template-fill
description: Fill HWPX (Hancom Office) templates by replacing {{placeholders}} with values from JSON or a dict. Use for Korean document automation, mail-merge, or form generation when the input is a .hwpx file containing {{variable}} markers. Handles single or multi-section documents. Preprocess values to strip units, reformat ratings, map arrays to numbered fields, enrich status values, or adjust date formats before filling.
---

# Fill HWPX Template

HWPX files are ZIP archives containing XML (HWPML format). This skill performs placeholder substitution while preserving document validity.

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
4. **Replace**: Find `<hp:t>` text elements matching `{{key}}`, substitute with processed values.
5. **Clean Layout Cache**: **Critical:** Remove sibling `<hp:linesegarray>` elements from any modified `<hp:p>` paragraphs. Failure causes overlapping/garbled characters.
6. **Repackage**: Zip contents back into `.hwpx` preserving directory structure.
7. **Verify**: Scan output to ensure no `{{...}}` placeholders remain in ANY section file.

## Critical Warning

**Always remove `<hp:linesegarray>` elements** from paragraphs where text is modified. These are pre-calculated layout caches that become invalid when text length changes. Hancom Office trusts these caches during rendering, resulting in unreadable overlapping text if stale caches remain.

## Usage

### Simple 1:1 Replacement
Run the helper script when no preprocessing is needed:

```bash
python3 scripts/fill_hwpx.py template.hwpx output.hwpx data.json
```

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

## Verification Checklist

- No `{{` substrings remain in any `Contents/section*.xml` file
- File remains a valid ZIP with entries `Contents/content.hpf` and `Contents/section*.xml`
- `<hp:linesegarray>` elements removed only from modified paragraphs (preserve in untouched paragraphs)

## Known invariants

- `<hp:linesegarray>` must be removed from any modified `<hp:p>` paragraphs. Failure causes overlapping/garbled characters.
- Multi-section documents: Process ALL `section*.xml` files, not just `section0.xml`.
- Values may require preprocessing before replacement (units, ratings, text enrichment, array mapping).

## Anti-patterns

- **Do not** use `unzip`/`zip` CLI commands; environments often lack them. Use Python's `zipfile` module.
- **Do not** perform blind string replacement on the entire XML; use namespace-aware parsing to avoid breaking tags.
- **Do not** strip all `linesegarray` elements globally; only remove from paragraphs where text actually changed.
- **Do not** assume only `section0.xml` exists; always check for and process all `section*.xml` files.
- **Do not** add/remove files from the HWPX archive unless explicitly required.

## Troubleshooting

**Overlapping characters after edit**: You failed to remove `<hp:linesegarray>` from modified paragraphs. Re-process and ensure the element is removed immediately after text replacement.

**Placeholder not replaced**: Verify the placeholder in XML exactly matches the JSON key including case. Check that the placeholder is inside `<hp:t>` and not split across multiple elements. If using multi-section documents, verify the placeholder wasn't in a section you missed (e.g., section1.xml).

**File corruption**: Ensure XML namespace declarations are preserved when writing. Use `ET.register_namespace()` with `http://www.hancom.co.kr/hwpml/2010/HWPML`.

**Incorrect values (units, ratings)**: Values were not preprocessed before replacement. Transform raw values (strip units, reformat ratings, append text) before calling the fill function. See `references/value-preprocessing.md` for patterns.
