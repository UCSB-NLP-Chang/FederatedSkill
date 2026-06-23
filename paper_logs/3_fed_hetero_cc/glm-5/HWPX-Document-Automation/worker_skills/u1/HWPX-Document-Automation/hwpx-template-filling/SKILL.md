---
name: hwpx-template-filling
description: Fill placeholders or replace text in HWPX template files using JSON/CSV data. Use when given an `.hwpx` file with `{{...}}` placeholders or exact text to update, and a corresponding data source. Handles ZIP extraction, XML text replacement (including split runs), and layout cache cleanup. Also covers common pre-processing patterns, including Korean age calculation, phone normalization, unit stripping, score reformatting, date formatting, severity annotation, and text appending.
---

# HWPX Template Filling

HWPX files are ZIP archives containing XML documents. To fill templates or update text:

## Workflow

1. **Read ALL input files first**: Before any processing, read every provided JSON/CSV/data file. Never hardcode or fabricate values.
2. **Merge multiple data sources**: When multiple data files are provided, merge them into a single replacement dict before filling.
3. **Pre-process data** (if needed): Transform raw values before filling. Common transformations:
   - Korean full-year age (만 나이) from birth date + reference date
   - Phone number normalization to `000-0000-0000` format
   - Unit/counter stripping (e.g., `"32명"` → `"32"`, `"₩450,000"` → `"450000"`)
   - Satisfaction score reformatting (e.g., `"4.5/5.0"` → `"4.5점 (5.0점 만점)"`)
   - Date formatting to `YYYY-MM-DD` or `YYYY.MM.DD`
   - Severity annotation (e.g., `"High"` → `"High(즉시조치)"`)
   - Text appending for free-form fields
   - See `references/korean-data-transformations.md` for reusable patterns.
4. **Inspect structure**: Use Python `zipfile` to list contents. Look for `Contents/section*.xml` or `Contents/content.hpf`.
   ```python
   import zipfile
   with zipfile.ZipFile('template.hwpx', 'r') as z:
       z.extractall('extracted/')
   ```
5. **Extract & Parse**: Read the target XML file(s).
6. **Replace Placeholders or Text**: Substitute `{{key}}` patterns or exact existing strings. Preserve surrounding XML tags.
   - **Split Runs Warning**: HWPX often breaks logical phrases across multiple `<hp:run>` elements (e.g., `</hp:run><hp:run charPrIDRef="0">`). If a target string isn't found in raw XML, it's likely split. Use regex to bridge boundaries: `re.sub(r'Part1\s*</hp:run><hp:run[^>]*>\s*Part2', 'NewText', content)`, or replace fragments individually.
7. **Clean Layout Cache**: Remove `<hp:linesegarray>...</hp:linesegarray>` elements from modified section files. Leaving them causes overlapping text when opened in Hancom Office.
8. **Repackage**: Write the modified XML back into a new ZIP archive with the exact same internal paths and filenames. Preserve `content.hpf` (OPF manifest) unmodified.

## Using the helper script

Run `scripts/fill_hwpx_template.py` for standard `{{key}}` replacement tasks after pre-processing your data:
```bash
python3 scripts/fill_hwpx_template.py <template.hwpx> <data.json> <output.hwpx>
```
For direct text replacement or split-run handling, write a custom inline script following the workflow above.

## Placeholder & Text Context Awareness

**Critical**: Placeholders or target text may not be the entire content of an `<hp:t>` element. They often have prefixes/suffixes or span multiple runs:

```xml
<hp:t>1단계: {{단계1}}</hp:t>
<!-- or split across runs -->
<hp:t>고객사: Northwind </hp:t></hp:run><hp:run><hp:t>Retail</hp:t>
```

**Decision rule**: When doing replacements:
- DO NOT assume the target is contiguous in raw XML. Check for `</hp:run><hp:run` boundaries.
- DO NOT search for `>value</hp:t>` if prefixes exist. Search for the value within the text node or use `value in content`.
- If appending after a value, locate it and insert immediately before `</hp:t>`.

## Verification

1. Verify the output ZIP contains the same files as the input.
2. Verify zero `{{...}}` placeholders remain (if applicable).
3. Verify zero `linesegarray` elements remain in modified section files.
4. Verify `content.hpf` is unchanged.
5. **Verify all data came from source files**: Cross-check filled values against original inputs.

## Anti-patterns

- **Do not fabricate or hardcode data values**. Always read from provided source files.
- **Do not apply transformations unless explicitly required**.
- Do not rely on `unzip`/`zip` CLI tools; they are often missing. Use Python `zipfile`.
- Do not modify `content.hpf` unless adding new files to the manifest.
- Do not skip `hp:linesegarray` removal on modified section files.
- Do not treat `.hwpx` as a plain text file.
- Do not pass raw birth dates, unformatted phone numbers, or values with Korean units directly if the template expects computed/clean values.
- Do not assume text is contiguous in raw XML; HWPX frequently splits phrases across `<hp:run>` boundaries.
- Do not apply transformations after XML replacement — transform values in Python before building the replacement dict.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly. The verifier's tolerance decides acceptable precision.

## Known invariants (by sub-task)

### hwpx-template-fill
- Output XML must NOT contain `linesegarray` elements in modified section files.
- `{{...}}` placeholder format is standard; Korean field names like `{{회사명}}` are common.

### hwpx-training-feedback
- Numeric fields like `참석자수` often have unit suffixes (`32명`) that must be stripped.
- Score fields like `만족도` use ratio format (`4.5/5.0`) that should be reformatted to Korean style.
- Free-form text fields like `종합의견` may need additional text appended.

### hwpx-project-proposal
- Phase descriptions may need duration appended: calculate month span from date ranges and add `(N개월)` suffix.
- Budget values may need normalization (remove commas, keep currency symbol).

### hwpx-clinic-intake-summary
- Korean age (만 나이) requires birth date + visit date calculation.
- Phone numbers must be normalized to `010-0000-0000` format.

### hwpx-safety-audit-brief
- **CRITICAL**: Process ALL data sections from input JSON. Audit items tables often need individual cell mapping.
- Date format must be converted: `2026-06-18` → `2026.06.18`
- Risk tier requires severity annotation: `High` → `High(즉시조치)`
- Corrective actions map to numbered placeholders: `{{조치1}}`, `{{조치2}}`, `{{조치3}}`
- See `references/safety-audit-patterns.md` for detailed workflow.

### hwpx-renewal-playbook-update
- May involve non-placeholder text replacement (replacing existing static values).
- Use regex bridging for split-run boundaries: `re.sub(r'Part1\s*</hp:run><hp:run[^>]*>\s*Part2', 'NewText', content)`.
- See `references/direct-value-replacement.md` for detailed patterns.

### hwpx-inventory-warehouse-report
- Placeholder-based workflow typical.
- Common fields: 보고일, 작성자, 부서, 창고명, 창고위치, 총품목수, 총재고금액.
- Item lists may use numbered placeholders: 품목1, 품목2, 품목3 (or array→numbered placeholder mapping).
- Special notes fields: 특이사항, 차기계획.
- Currency format: preserve `₩` and commas in values.

## Troubleshooting

- **`unzip: command not found`**: Use Python zipfile module instead.
- **Layout cache not fully removed**: Remove ALL `<hp:linesegarray>` from modified sections: `re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', content, flags=re.DOTALL)`.
- **Target string not found in XML**: Likely split across `<hp:run>` boundaries. Inspect raw XML for `</hp:run><hp:run` tags interrupting the phrase. Use regex to bridge boundaries or replace fragments separately.
- **Post-replacement append fails**: If searching for `>value</hp:t>` returns False, the placeholder likely has a prefix/suffix. Adjust search pattern.
- **Unit suffixes appear in output**: Forgot to strip units. Apply transformation before building replacement dict.
- **Verifier fails despite "successful" fill**: Check that all data came from source files, and that no unjustified transformations were applied.

## Fallback

If the HWPX contains complex fields or form controls instead of plain text, inspect the XML for `<hp:field>` or `<hp:ctrl>` elements and adjust the replacement strategy accordingly.

## References

- `references/hwpx-structure.md` — detailed HWPX archive structure and XML namespace info
- `references/korean-data-transformations.md` — reusable patterns for Korean age calculation, phone normalization, unit stripping, score reformatting, date formatting, and text appending
- `references/safety-audit-patterns.md` — specific patterns for Korean warehouse safety audit HWPX documents
- `references/direct-value-replacement.md` — patterns for replacing literal values without placeholder markup
- `references/verification.md` — portable verification using Python zipfile fallback