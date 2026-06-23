---
name: hwpx-document-processing
description: Process HWPX (Hancom Office) document files - extract, modify, and create HWPX archives. Use when working with .hwpx files, Korean document templates, or filling placeholders in Hancom documents.
---

# HWPX Document Processing

HWPX files are ZIP archives containing XML content. This skill covers reading, modifying, and creating valid HWPX documents.

## Structure

```
.hwpx (ZIP archive)
├── Contents/
│   ├── content.hpf    # Manifest/package file
│   └── section0.xml   # Main document content (primary edit target)
```

## Workflow

1. **Extract and inspect**: Use Python's `zipfile` module (not shell `unzip`, which may be unavailable)
2. **Locate content**: Main text is in `Contents/section0.xml`
3. **Preprocess values**: Transform values as needed before replacement (see Value Preprocessing)
4. **Modify XML**: Replace placeholders, update text in `<hp:t>` elements
5. **Remove layout cache**: Delete `<hp:linesegarray>` elements from any modified `<hp:p>` paragraphs
6. **Repackage**: Create new ZIP with `ZIP_DEFLATED` compression, preserving original `ZipInfo` metadata and file order
7. **Verify**: Validate ZIP integrity, check for remaining placeholders, ensure XML well-formedness

## Critical: Layout Cache Handling

When modifying paragraph text content, **must remove `<hp:linesegarray>` elements** from that paragraph. These are layout caches that become stale when text changes, causing rendering issues.

```xml
<!-- Before: has stale layout cache -->
<hp:p id="1"><hp:run><hp:t>회사명: {{회사명}}</hp:t></hp:run><hp:linesegarray>...</hp:linesegarray></hp:p>

<!-- After: layout cache removed -->
<hp:p id="1"><hp:run><hp:t>회사명: 실제값</hp:t></hp:run></hp:p>
```

## Placeholder Replacement Pattern

Placeholders typically use `{{필드명}}` format (Korean field names). Replace with actual values while preserving surrounding text and XML structure.

## Value Preprocessing

Values often need transformation before placeholder replacement:
- **Date formatting**: Convert dates to target format
- **Age calculation**: Calculate age from birth date and reference date (common in Korean medical documents)
- **Phone normalization**: Format consistently (e.g., `010-0000-0000`)
- **Text enrichment**: Add context like units or calculated fields

Preprocess values before calling the script or performing replacement.

## When to Use the Script vs Custom Code

- **Use the script** (`scripts/hwpx_fill_template.py`) for simple key-value replacement where values are ready to use
- **Use custom code** when you need to transform values, handle complex patterns, or perform additional validation

## Verification

After creating output:
1. Validate ZIP integrity with `zipfile.is_zipfile()`
2. Check for remaining placeholders
3. Parse XML to ensure well-formedness

**Note:** `linesegarray` elements **will remain** on static/unmodified paragraphs. This is expected and correct. Only verify that paragraphs containing replaced values do not contain `linesegarray`.

## Anti-Patterns

- Do not use shell `unzip` command - may not be available
- Do not preserve `<hp:linesegarray>` in modified paragraphs - causes rendering issues
- Do not modify `content.hpf` unless changing document structure
- Do not add/remove files from the HWPX archive unless explicitly required - preserve original `namelist` and `ZipInfo` objects

## Known invariants (by sub-task)

### B1: HWPX Template Placeholder Fill
- `<hp:linesegarray>` elements must be removed from any modified `<hp:p>` paragraphs. Failure causes overlapping/garbled characters.
- Only paragraphs that had placeholders replaced need linesegarray removal; static paragraphs should retain theirs.

## Reference Script

See `scripts/hwpx_fill_template.py` for a working implementation of template filling with layout cache removal.
