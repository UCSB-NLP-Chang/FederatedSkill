---
name: hwpx-template-fill
description: Fill templates in .hwpx (Hancom Office) documents by replacing {{...}} placeholders with values from JSON. Use when given an .hwpx template and a JSON mapping of field names to values. Handles ZIP extraction, XML text replacement, and layout cache invalidation.
---

# Fill HWPX Template

HWPX files are ZIP archives containing XML content. To fill placeholders safely:

## Workflow
1. **Inspect structure**: Use Python `zipfile` to list contents. Main text lives in `Contents/section0.xml` (or `section*.xml`).
2. **Identify placeholders**: Look for `{{key}}` patterns inside `<hp:t>` tags.
3. **Replace & Invalidate Cache**:
   - Replace `{{key}}` with values from JSON.
   - **Critical**: Remove `<hp:linesegarray>...</hp:linesegarray>` from any modified `<hp:p>` element. HWPX caches layout coordinates here; leaving them causes overlapping/garbled text when string lengths change.
4. **Repackage**: Write modified XML back into a new ZIP with `ZIP_DEFLATED` compression, preserving original file metadata.
5. **Verify**: Open the output ZIP, read the XML, and confirm zero `{{...}}` patterns remain.

## Verification Notes
- `linesegarray` elements **will remain** on static/unmodified paragraphs. This is expected and correct.
- Only verify that paragraphs containing replaced values do *not* contain `linesegarray`.
- A simple regex check for remaining `{{...}}` is usually sufficient for placeholder validation.

## Known invariants (by sub-task)

### B1: HWPX Template Placeholder Fill
- `<hp:linesegarray>` elements must be removed from any modified `<hp:p>` paragraphs. Failure causes overlapping/garbled characters.

## Anti-Patterns
- Do not treat `.hwpx` as a plain text file. It is a binary ZIP archive.
- Do not skip `<hp:linesegarray>` removal. Modified paragraphs will render incorrectly.
- Do not rely on external HWP libraries unless necessary; standard `zipfile` + `re` is sufficient and more reliable in constrained environments.

## Automation
Run `scripts/fill_hwpx.py <template.hwpx> <data.json> <output.hwpx>` to execute the full workflow. It handles paragraph tracking, cache invalidation, and verification automatically.