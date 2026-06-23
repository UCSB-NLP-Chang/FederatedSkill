---
name: hwpx-template-filling
description: Fill placeholders in HWPX template files using JSON data. Use when given an `.hwpx` file with `{{...}}` placeholders and a corresponding JSON or key-value source. Handles ZIP extraction, XML text replacement, and layout cache cleanup. Also covers common pre-processing patterns like Korean age calculation and phone normalization.
---

# HWPX Template Filling

HWPX files are ZIP archives containing XML documents. To fill templates:

## Workflow

1. **Pre-process data** (if needed): Transform raw JSON values before filling. Common transformations:
   - Korean full-year age (만 나이) from birth date + reference date
   - Phone number normalization to `000-0000-0000` format
   - See `references/korean-data-transformations.md` for reusable patterns.
2. **Inspect structure**: Use Python `zipfile` to list contents. Look for `Contents/section*.xml` or `Contents/content.hpf`.
   ```python
   import zipfile
   with zipfile.ZipFile('template.hwpx', 'r') as z:
       z.extractall('extracted/')
   ```
   Or use `unzip` if available (fallback):
   ```bash
   unzip -o template.hwpx -d extracted/
   ```
3. **Extract & Parse**: Read the target XML file(s).
4. **Replace Placeholders**: Substitute `{{key}}` patterns with pre-processed values. Preserve surrounding text and XML tags.
5. **Clean Layout Cache**: Remove `<hp:linesegarray>...</hp:linesegarray>` elements from modified section files. Leaving them causes overlapping text when opened in Hancom Office.
6. **Repackage**: Write the modified XML back into a new ZIP archive with the exact same internal paths and filenames. Preserve `content.hpf` (OPF manifest) unmodified.

## Using the helper script

Run `scripts/fill_hwpx.py` for standard `{{key}}` replacement tasks after pre-processing your data:
```bash
python3 scripts/fill_hwpx.py <template.hwpx> <data.json> <output.hwpx>
```

If your data requires transformation (age, phone, dates), pre-process the JSON first, then pass the transformed JSON to the script.

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

## Anti-patterns
- Do not rely on `unzip`/`zip` CLI tools; they are often missing in constrained environments. Use Python `zipfile`.
- Do not modify `content.hpf` unless adding new files to the manifest.
- Do not skip `hp:linesegarray` removal on modified section files; it breaks rendering.
- Do not treat `.hwpx` as a plain text file.
- Do not pass raw birth dates or unformatted phone numbers directly to placeholders if the template expects computed ages or normalized formats.
- Do not assume `{{key}}` is the only content in its `<hp:t>` element when doing post-replacement edits.

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

## Troubleshooting

- **`unzip: command not found`**: Use Python zipfile module instead (always available).
- **Layout cache not fully removed**: If text appears overlapping after filling, the script missed some `<hp:linesegarray>` elements. Remove ALL from modified section files: `re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', content, flags=re.DOTALL)`.
- **Post-replacement append fails**: If searching for `>value</hp:t>` returns False, the placeholder likely has a prefix/suffix. Inspect the XML around the placeholder location to find the actual text node structure, then adjust your search pattern to match the full text content.

## Fallback
If the HWPX contains complex fields or form controls instead of plain `{{...}}` text, inspect the XML for `<hp:field>` or `<hp:ctrl>` elements and adjust the replacement strategy accordingly.

## References
- `references/hwpx-structure.md` — detailed HWPX archive structure and XML namespace info
- `references/korean-data-transformations.md` — reusable patterns for Korean age calculation and phone normalization