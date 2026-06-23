---
name: hwpx-template-fill
description: Fill HWPX (Hancom Office) templates by replacing {{placeholders}} with values from JSON or a dict. Use for Korean document automation, mail-merge, or form generation when the input is a .hwpx file containing {{variable}} markers.
---

# Fill HWPX Template

HWPX files are ZIP archives containing XML (HWPML format). This skill performs placeholder substitution while preserving document validity.

## Workflow

1. **Extract**: HWPX is a ZIP. Extract to a temporary directory.
2. **Locate**: Main content is in `Contents/section0.xml` (refer to `content.hpf` manifest if structure differs).
3. **Replace**: Find `<hp:t>` text elements matching `{{key}}`, substitute with values.
4. **Clean Layout Cache**: **Critical:** Remove sibling `<hp:linesegarray>` elements from any modified `<hp:p>` paragraphs. Failure to do this causes overlapping/garbled characters in Hancom Office.
5. **Repackage**: Zip contents back into `.hwpx` preserving paths.
6. **Verify**: Scan output to ensure no `{{...}}` placeholders remain.

## Critical Warning

**Always remove `<hp:linesegarray>` elements** from paragraphs where text is modified. These are pre-calculated layout caches that become invalid when text length changes. Hancom Office trusts these caches during rendering, resulting in unreadable overlapping text if stale caches remain.

## Usage

Run the helper script:

```bash
python3 scripts/fill_hwpx.py template.hwpx output.hwpx data.json
```

Where `data.json` maps keys to values (e.g., `{"회사명": "Example Inc"}` replaces `{{회사명}}`).

## Verification Checklist

- No `{{` substrings remain in `Contents/section0.xml`
- File remains a valid ZIP with entries `Contents/content.hpf` and `Contents/section0.xml`
- `<hp:linesegarray>` elements removed only from modified paragraphs (preserve in untouched paragraphs)

## Anti-patterns

- **Do not** use `unzip`/`zip` CLI commands; environments often lack them. Use Python's `zipfile` module.
- **Do not** perform blind string replacement on the entire XML; use namespace-aware parsing to avoid breaking tags.
- **Do not** strip all `linesegarray` elements globally; only remove from paragraphs where text actually changed.

## Troubleshooting

**Overlapping characters after edit**: You failed to remove `<hp:linesegarray>` from modified paragraphs. Re-process and ensure the element is removed immediately after text replacement.

**Placeholder not replaced**: Verify the placeholder in XML exactly matches the JSON key including case. Check that the placeholder is inside `<hp:t>` and not split across multiple elements.

**File corruption**: Ensure XML namespace declarations are preserved when writing. Use `ET.register_namespace()` with `http://www.hancom.co.kr/hwpml/2010/HWPML`.
