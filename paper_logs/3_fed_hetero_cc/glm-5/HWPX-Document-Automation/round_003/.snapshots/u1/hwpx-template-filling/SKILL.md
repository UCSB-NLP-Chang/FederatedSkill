---
name: hwpx-template-filling
description: Fill HWPX (Hancom Office) document templates by replacing placeholders with data. Use when working with .hwpx files, Korean office documents, or templates containing {{placeholder}} patterns.
---

# HWPX Template Filling

HWPX is Hancom Office's XML-based document format (ZIP archive containing XML). This skill covers extracting, modifying, and repackaging HWPX templates.

## When to Use
- Input files have `.hwpx` extension
- Templates contain `{{placeholder}}` patterns (often Korean field names like `{{회사명}}`)
- Task requires filling form fields or merging data into documents

## Workflow

1. **Pre-process data** (if needed)
   - Transform raw JSON values before filling
   - Common Korean document transformations:
     - Korean full-year age (만 나이) from birth date + reference date
     - Phone number normalization to `010-0000-0000` format
   - See `references/korean-data-transformations.md` for reusable patterns

2. **Extract the HWPX file**

   Prefer Python zipfile (always available):
   ```python
   import zipfile
   with zipfile.ZipFile('template.hwpx', 'r') as z:
       z.extractall('extracted/')
   ```

   Or use `unzip` if available:
   ```bash
   unzip -o template.hwpx -d extracted/
   ```

3. **Locate content files**
   - Main content: `Contents/section0.xml`, `Contents/section1.xml`, etc.
   - Metadata: `Contents/content.hpf`

4. **Replace placeholders and clean layout cache**
   - Replace `{{field}}` patterns with pre-processed values
   - **Critical**: Remove ALL `<hp:linesegarray>` elements from modified section files
   - The layout cache becomes invalid when text changes; Hancom recalculates it on open
   - See `scripts/fill_hwpx_template.py` for a reusable implementation

5. **Repackage as HWPX**
   ```python
   import zipfile
   with zipfile.ZipFile('output.hwpx', 'w') as z:
       for root, dirs, files in os.walk('extracted/'):
           for f in files:
               path = os.path.join(root, f)
               z.write(path, os.path.relpath(path, 'extracted/'))
   ```

6. **Verify output**
   - Confirm ZIP is valid
   - Check no `{{}}` placeholders remain
   - Verify XML structure intact
   - See `references/verification.md` for Python-only verification methods

## Key Technical Details

- HWPX uses namespace `hp:` with URI `http://www.hancom.co.kr/hwpml/2010/HWPML`
- Text content is in `<hp:t>` elements inside `<hp:run>` inside `<hp:p>` paragraphs
- Layout cache `<hp:linesegarray>` stores computed positions; must be removed when text changes
- Preserve Korean labels and formatting exactly

## Troubleshooting

- **`unzip: command not found`**: Use Python zipfile module instead (always available)
- **Layout cache not fully removed**: If text appears overlapping or misaligned after filling, the script may have missed some `<hp:linesegarray>` elements. Remove ALL occurrences with: `re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', content, flags=re.DOTALL)`
- **Script only modified some paragraphs**: Older script versions tried to track modified paragraphs. This is brittle. Always remove all layout cache elements from any modified section file.

## Anti-Patterns
- Do NOT modify text without removing `<hp:linesegarray>` from that section file
- Do NOT assume UTF-8; always specify encoding when reading/writing XML
- Do NOT skip verification; corrupted HWPX files may open but display incorrectly
- Do NOT assume `unzip` is available; prefer Python zipfile for portability

## Scripts
- `scripts/fill_hwpx_template.py` - Reusable Python script for placeholder replacement with layout cache cleanup (requires JSON input file)

## References
- `references/hwpx-structure.md` - Detailed HWPX file and XML structure
- `references/korean-data-transformations.md` - Korean age calculation and phone normalization patterns
- `references/verification.md` - Python-only verification methods when system tools unavailable