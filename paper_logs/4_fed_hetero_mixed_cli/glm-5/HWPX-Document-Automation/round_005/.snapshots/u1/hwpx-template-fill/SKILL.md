---
name: hwpx-template-fill
description: Fill templates in .hwpx (Hancom Office) documents by replacing {{...}} placeholders with values from JSON. Use when given an .hwpx template and a JSON mapping of field names to values. Handles ZIP extraction, multi-section XML text replacement, and layout cache invalidation.
---

# Fill HWPX Template

HWPX files are ZIP archives containing XML content. To fill placeholders safely:

## Workflow
1. **Inspect structure**: Use Python `zipfile` to list contents. Main text lives in `Contents/section0.xml`, `Contents/section1.xml`, etc. **Always process all `section*.xml` files**, as placeholders may span multiple sections.
2. **Identify placeholders**: Look for `{{key}}` patterns inside `<hp:t>` tags across all sections.
3. **Preprocess Data (if needed)**: `scripts/fill_hwpx.py` performs direct 1:1 replacement. If values require computation, transform the JSON or build a replacement dictionary before applying it to the XML.
4. **Replace & Invalidate Cache**:
   - Replace `{{key}}` with values.
   - **Critical**: Remove `<hp:linesegarray>...</hp:linesegarray>` or `<hp:linesegarray />` from any modified `<hp:p>` element. HWPX caches layout coordinates here; leaving them causes overlapping/garbled text when string lengths change.
5. **Repackage**: Write modified XML back into a new ZIP with `ZIP_DEFLATED` compression, preserving original `ZipInfo` metadata and file order.
6. **Verify**: Open the output ZIP, read *all* section XMLs, and confirm zero `{{...}}` patterns remain.

## Data Transformation Patterns
When source data requires reformatting before placeholder replacement, apply transformations in a preprocessing step:

| Pattern | Input Example | Output | Python Snippet |
|---------|---------------|--------|----------------|
| Extract digits | `"32명"` | `"32"` | `re.sub(r'[^\d]', '', value)` |
| Reformat score | `"4.5/5.0"` | `"4.5점 (5.0점 만점)"` | Parse and reformat per locale |
| Append text | `"comment"` | `"comment. Added."` | `value + " Added."` |
| Conditional text | `"high"` | `"높음"` | Lookup table or if/else |

Build a transformed dictionary before passing to the fill script or applying XML replacements.
See `references/value-preprocessing.md` for detailed reusable code patterns.

## Verification Checklist
1. **No remaining placeholders**: Regex check `{{...}}` across all section XMLs returns empty
2. **Clean linesegarray removal**: Modified paragraphs have no `<hp:linesegarray>` elements; check for orphaned `</hp:linesegarray>` closing tags which indicate incomplete removal
3. **Static paragraphs preserved**: Unmodified paragraphs retain their `linesegarray` elements
4. **Valid ZIP structure**: Output opens as valid ZIP with all original files present

## Known invariants (by sub-task)
### B1: HWPX Template Placeholder Fill
- `<hp:linesegarray>` elements must be removed from any modified `<hp:p>` paragraphs. Failure causes overlapping/garbled characters.

## Anti-Patterns
- Do not treat `.hwpx` as a plain text file. It is a binary ZIP archive.
- Do not skip `<hp:linesegarray>` removal. Modified paragraphs will render incorrectly.
- Do not rely on external HWP libraries unless necessary; standard `zipfile` + `re` is sufficient and more reliable in constrained environments.
- Do not add/remove files from the HWPX archive unless explicitly required. Preserve the original `namelist` and `ZipInfo` objects.
- Do not assume placeholders only exist in `section0.xml`. Always scan and process all `section*.xml` files.
- Do not use incomplete regex for linesegarray removal; match both self-closing `<hp:linesegarray />` and full `<hp:linesegarray>...</hp:linesegarray>` forms.

## Automation
Run `scripts/fill_hwpx.py <template.hwpx> <data.json> <output.hwpx>` for direct 1:1 placeholder replacement across all sections.
If data transformation is required, adapt the script or run a preprocessing step to generate a ready-to-use JSON mapping before invoking the ZIP/XML workflow.