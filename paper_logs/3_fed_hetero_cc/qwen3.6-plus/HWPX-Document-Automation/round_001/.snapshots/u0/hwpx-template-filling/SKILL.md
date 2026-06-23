---
name: hwpx-template-filling
description: Fill placeholders in HWPX template files using JSON data. Use when given an `.hwpx` file with `{{...}}` placeholders and a corresponding JSON or key-value source. Handles ZIP extraction, XML text replacement, and layout cache cleanup.
---

# HWPX Template Filling

HWPX files are ZIP archives containing XML documents. To fill templates:
1. **Inspect structure**: Use Python `zipfile` to list contents. Look for `Contents/section*.xml` or `Contents/content.hpf`.
2. **Extract & Parse**: Read the target XML file(s).
3. **Replace Placeholders**: Substitute `{{key}}` patterns with provided values. Preserve surrounding text and XML tags.
4. **Clean Layout Cache**: Remove `<hp:linesegarray>...</hp:linesegarray>` elements from modified paragraphs. Leaving them causes overlapping text when opened in Hancom Office.
5. **Repackage**: Write the modified XML back into a new ZIP archive with the exact same internal paths and filenames. Preserve `content.hpf` (OPF manifest) unmodified.

## Workflow
1. Read the JSON/data source.
2. Run `scripts/fill_hwpx.py` for standard `{{key}}` replacement tasks. Execute as:
   ```bash
   python3 scripts/fill_hwpx.py <template.hwpx> <data.json> <output.hwpx>
   ```
3. Verify the output ZIP contains the same files as the input.
4. Verify zero `{{...}}` placeholders remain in the XML.

## Anti-patterns
- Do not rely on `unzip`/`zip` CLI tools; they are often missing in constrained environments. Use Python `zipfile`.
- Do not modify `content.hpf` unless adding new files to the manifest.
- Do not skip `hp:linesegarray` removal on modified paragraphs; it breaks rendering.
- Do not treat `.hwpx` as a plain text file.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### hwpx-template-fill
- Output XML must NOT contain `linesegarray` elements in modified paragraphs — remove them after editing.
- `{{...}}` placeholder format is standard; Korean field names like `{{회사명}}` are common.

## Fallback
If the HWPX contains complex fields or form controls instead of plain `{{...}}` text, inspect the XML for `<hp:field>` or `<hp:ctrl>` elements and adjust the replacement strategy accordingly.

## References
- `references/hwpx-structure.md` — detailed HWPX archive structure and XML namespace info