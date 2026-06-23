---
name: hwpx-template-fill
description: Fill HWPX (Hancom Office) templates by replacing {{placeholders}} with values from JSON or a dict. Use for Korean document automation, mail-merge, or form generation when the input is a .hwpx file containing {{variable}} markers.
---

# Fill HWPX Template

HWPX files are ZIP archives containing XML (HWPML format). This skill performs placeholder substitution while preserving document validity.

## Workflow

1. **Extract**: HWPX is a ZIP. Extract to a temporary directory.
2. **Locate**: Main content is in `Contents/section0.xml` (refer to `content.hpf` manifest if structure differs).
3. **Preprocess Values**: Before replacement, transform raw values as needed:
   - **Korean age**: Calculate from birth date and reference date
   - **Phone normalization**: Format as `010-0000-0000`
   - **Date formatting**: Convert to target format
   - **Text enrichment**: Add units or calculated fields
4. **Replace**: Find `<hp:t>` text elements matching `{{key}}`, substitute with processed values.
5. **Clean Layout Cache**: **Critical:** Remove sibling `<hp:linesegarray>` elements from any modified `<hp:p>` paragraphs. Failure to do this causes overlapping/garbled characters in Hancom Office.
6. **Repackage**: Zip contents back into `.hwpx` preserving paths and original `ZipInfo` metadata.
7. **Verify**: Scan output to ensure no `{{...}}` placeholders remain.

## Critical Warning

**Always remove `<hp:linesegarray>` elements** from paragraphs where text is modified. These are pre-calculated layout caches that become invalid when text length changes. Hancom Office trusts these caches during rendering, resulting in unreadable overlapping text if stale caches remain.

## Usage

Run the helper script for direct 1:1 replacement:

```bash
python3 scripts/fill_hwpx.py template.hwpx output.hwpx data.json
```

Where `data.json` maps keys to values (e.g., `{"회사명": "Example Inc"}` replaces `{{회사명}}`).

For preprocessing (age calculation, phone normalization), transform values BEFORE calling the script:

```python
# Example: preprocess values before calling fill_hwpx_template
raw_values = {"생년월일": "1990-01-15", "연락처": "01011112222"}
processed_values = {
    "생년월일": raw_values["생년월일"],  # keep original
    "연락처": normalize_phone(raw_values["연락처"]),  # format as 010-1111-2222
}
fill_hwpx_template(template, output, processed_values)
```

## Verification Checklist

- No `{{` substrings remain in `Contents/section0.xml`
- File remains a valid ZIP with entries `Contents/content.hpf` and `Contents/section0.xml`
- `<hp:linesegarray>` elements removed only from modified paragraphs (preserve in untouched paragraphs)

## Verification Notes

- `linesegarray` elements **will remain** on static/unmodified paragraphs. This is expected and correct.
- Only verify that paragraphs containing replaced values do *not* contain `linesegarray`.
- A simple regex check for remaining `{{...}}` is usually sufficient for placeholder validation.

## Known invariants (by sub-task)

### B1: HWPX Template Placeholder Fill
- `<hp:linesegarray>` elements must be removed from any modified `<hp:p>` paragraphs. Failure causes overlapping/garbled characters.
- Values may require preprocessing (age calculation, phone normalization) before placeholder replacement. (R2)

## Anti-patterns

- **Do not** use `unzip`/`zip` CLI commands; environments often lack them. Use Python's `zipfile` module.
- **Do not** perform blind string replacement on the entire XML; use namespace-aware parsing to avoid breaking tags.
- **Do not** strip all `linesegarray` elements globally; only remove from paragraphs where text actually changed.
- **Do not** add/remove files from the HWPX archive unless explicitly required. Preserve the original `namelist` and `ZipInfo` objects.

## Troubleshooting

**Overlapping characters after edit**: You failed to remove `<hp:linesegarray>` from modified paragraphs. Re-process and ensure the element is removed immediately after text replacement.

**Placeholder not replaced**: Verify the placeholder in XML exactly matches the JSON key including case. Check that the placeholder is inside `<hp:t>` and not split across multiple elements.

**File corruption**: Ensure XML namespace declarations are preserved when writing. Use `ET.register_namespace()` with `http://www.hancom.co.kr/hwpml/2010/HWPML`.

**Incorrect age/phone values**: Values were not preprocessed before replacement. Transform raw values (age calculation, phone normalization) before calling the script.