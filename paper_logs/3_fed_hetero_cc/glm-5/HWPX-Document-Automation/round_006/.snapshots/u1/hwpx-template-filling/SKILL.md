---
name: hwpx-template-filling
description: Fill placeholders in HWPX template files using JSON data. Use when given an `.hwpx` file with `{{...}}` placeholders and a corresponding JSON or key-value source. Handles ZIP extraction, XML text replacement, and layout cache cleanup. Also covers common pre-processing patterns, including Korean age calculation, phone normalization, unit stripping, score reformatting, date formatting (YYYY-MM-DD or YYYY.MM.DD), and text appending.
---

# HWPX Template Filling

HWPX files are ZIP archives containing XML documents. To fill templates:

## Workflow

1. **Read ALL input files first**: Before any processing, read every provided JSON/data file. Never hardcode or fabricate values.
2. **Pre-process data** (if needed): Transform raw JSON values before filling. Common transformations:
   - Korean full-year age (만 나이) from birth date + reference date
   - Phone number normalization to `000-0000-0000` format
   - Unit/counter stripping (e.g., `"32명"` → `"32"`, `"₩450,000"` → `"450000"`)
   - Satisfaction score reformatting (e.g., `"4.5/5.0"` → `"4.5점 (5.0점 만점)"`)
   - Date formatting to `YYYY-MM-DD` or `YYYY.MM.DD` (only when explicitly required)
   - Text appending for free-form fields
   - Custom formatting (e.g., date ranges)
   - See `references/korean-data-transformations.md` for reusable patterns.
3. **Merge multiple data sources**: When multiple JSON files are provided, merge them into a single replacement dict before filling.
4. **Inspect structure**: Use Python `zipfile` to list contents. Look for `Contents/section*.xml` or `Contents/content.hpf`.
   ```python
   import zipfile
   with zipfile.ZipFile('template.hwpx', 'r') as z:
       z.extractall('extracted/')
   ```
   Or use `unzip` if available (fallback):
   ```bash
   unzip -o template.hwpx -d extracted/
   ```
5. **Extract & Parse**: Read the target XML file(s).
6. **Replace Placeholders**: Substitute `{{key}}` patterns with pre-processed values. Preserve surrounding text and XML tags.
7. **Clean Layout Cache**: Remove `<hp:linesegarray>...</hp:linesegarray>` elements from modified section files. Leaving them causes overlapping text when opened in Hancom Office.
8. **Repackage**: Write the modified XML back into a new ZIP archive with the exact same internal paths and filenames. Preserve `content.hpf` (OPF manifest) unmodified.

## Using the helper script

Run `scripts/fill_hwpx_template.py` for standard `{{key}}` replacement tasks after pre-processing your data:
```bash
python3 scripts/fill_hwpx_template.py <template.hwpx> <data.json> <output.hwpx>
```

If your data requires transformation (age, phone, dates, units, scores), pre-process the JSON first, then pass the transformed JSON to the script.

## Placeholder Context Awareness

**Critical**: Placeholders may not be the entire content of an `<hp:t>` element. They often have prefixes or suffixes in the same text node:

```xml
<hp:t>1단계: {{단계1}}</hp:t>
```

After replacement, the text becomes `1단계: 요구사항 분석 및 설계 (2026-08 ~ 2026-10)`, not just the value.

**Decision rule**: When doing post-replacement modifications (appending text, adding spans, etc.):
- DO NOT search for `>value</hp:t>` — this fails when prefixes exist.
- DO search for the value within the text node: `re.search(r'>' + re.escape(value) + r'</hp:t>', content)` or use `value in content` to locate it, then find the surrounding context.
- If you need to append after the value, search for the value and insert immediately before `</hp:t>`.

## Verification

1. Verify the output ZIP contains the same files as the input.
2. Verify zero `{{...}}` placeholders remain in the XML.
3. Verify zero `linesegarray` elements remain in modified section files.
4. Verify `content.hpf` is unchanged.
5. **Verify all data came from source files**: Cross-check filled values against original JSON inputs.

## Anti-patterns

- **Do not fabricate or hardcode data values**. Always read from provided source files. If a file is mentioned in the task, read it before processing.
- **Do not apply transformations unless explicitly required**. If the template expects `YYYY-MM-DD`, do not change to `YYYY.MM.DD`. If a field value is `"High"`, do not append text unless the task or template explicitly requires it.
- Do not rely on `unzip`/`zip` CLI tools; they are often missing in constrained environments. Use Python `zipfile`.
- Do not modify `content.hpf` unless adding new files to the manifest.
- Do not skip `hp:linesegarray` removal on modified section files; it breaks rendering.
- Do not treat `.hwpx` as a plain text file.
- Do not pass raw birth dates, unformatted phone numbers, or values with Korean units/counters directly to placeholders if the template expects computed ages, normalized formats, or clean numbers.
- Do not pass raw ratio scores (`4.5/5.0`) to placeholders expecting Korean-style scores (`4.5점 (5.0점 만점)`).
- Do not assume `{{key}}` is the only content in its `<hp:t>` element when doing post-replacement edits.
- Do not apply transformations after XML replacement — transform values in Python before building the replacement dict.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### hwpx-template-fill
- Output XML must NOT contain `linesegarray` elements in modified section files — remove them after editing.
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
- Date format must be converted: `2026-06-18` → `2026.06.18` (dot format required for safety audits)
- Risk tier requires severity annotation: `High` → `High(즉시조치)` using mapping `{'High':'즉시조치','Medium':'계획보완','Low':'모니터링'}`
- Corrective actions map to numbered placeholders: `{{조치1}}`, `{{조치2}}`, `{{조치3}}` from array indices
- Verify all placeholders including `{{보고대상}}` and any table cell placeholders are filled
- See `references/safety-audit-patterns.md` for detailed patterns.

## Troubleshooting

- **`unzip: command not found`**: Use Python zipfile module instead (always available).
- **Layout cache not fully removed**: If text appears overlapping after filling, the script missed some `<hp:linesegarray>` elements. Remove ALL from modified section files: `re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', content, flags=re.DOTALL)`.
- **Post-replacement append fails**: If searching for `>value</hp:t>` returns False, the placeholder likely has a prefix/suffix. Inspect the XML around the placeholder location to find the actual text node structure, then adjust your search pattern to match the full text content.
- **Unit suffixes appear in output**: Forgot to strip '명', '건', etc. Apply `strip_korean_units()` transformation before building replacement dict.
- **Score format inconsistent**: Raw ratio passed through. Apply `format_satisfaction_korean()` transformation for ratio values.
- **Date format mismatch**: Template expects `YYYY.MM.DD` but received `YYYY-MM-DD`. Apply `format_korean_dot_date()` transformation.
- **Verifier fails despite "successful" fill**: Check that all data came from source files (not hardcoded), and that no unjustified transformations were applied. Cross-check each filled value against the original input.

## Fallback

If the HWPX contains complex fields or form controls instead of plain `{{...}}` text, inspect the XML for `<hp:field>` or `<hp:ctrl>` elements and adjust the replacement strategy accordingly.

## References
- `references/hwpx-structure.md` — detailed HWPX archive structure and XML namespace info
- `references/korean-data-transformations.md` — reusable patterns for Korean age calculation, phone normalization, unit stripping, score reformatting, date formatting, and text appending
- `references/verification.md` — portable verification using Python zipfile fallback
- `references/safety-audit-patterns.md` — specific patterns for Korean warehouse safety audit documents