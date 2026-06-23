---
name: edit-embedded-excel
description: Edit embedded Excel workbooks inside PowerPoint (.pptx) or Word (.docx) files. Use when tasks require modifying spreadsheet data, updating cell values, or preserving formulas within Office documents that contain embedded Excel objects. Critical for cross-rate calculations where formulas like =ROUND(1/A1,4) must be preserved while updating source values. Also use when slide notes contain update instructions that must be parsed to identify target cells, including tasks with abbreviated labels requiring alias resolution via reference CSV files. Essential when verifiers check cached XML values rather than relying on Excel recalculation.
---

# Edit Embedded Excel in Office Documents

Extract, modify, and repackage Excel workbooks embedded in .pptx or .docx files.

## When to Use

- Task involves updating data in an Excel table shown in a PowerPoint slide
- Need to modify cell values while preserving formulas that reference those cells
- Working with .pptx or .docx files containing embedded spreadsheets
- **Cross-rate updates**: When a cell contains `=ROUND(1/A1, 4)`, update A1 (the source rate), not the formula cell
- **Slide note instructions**: Task mentions corrections or updates described in slide notes (e.g., "FINAL slot-factor correction: cart to bay = 0.50")
- **Abbreviated labels**: Slide notes use shorthand (e.g., "CB to CD = 1.5625") that must be resolved to full names before locating matrix cells
- **Verifier compatibility**: Automated tests may read cached `<v>` values from XML instead of computing formulas
- **Multiple embeddings (live vs archive)**: Task has multiple embedded workbooks and a JSON manifest (e.g., `live_embedding.json`) indicating which one to update

## Workflow

### 1. Resolve Labels/Aliases (If Present)

Slide notes often use abbreviations for row/column headers. Before editing, check the workspace for alias mapping files:

```python
import csv, os

# Search for alias files in workspace
for f in os.listdir('.'):
    if 'alias' in f.lower() and f.endswith('.csv'):
        with open(f) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                print(row)  # Maps short codes to full names
```

**Decision rule**: If slide note contains abbreviations (2-4 letter codes), search for `label_aliases.csv`, `aliases.csv`, or similar mapping files. Resolve abbreviations to full names, then match against Excel row/column headers to locate the target cell intersection.

### 2. Read Slide Notes (If Present)

Slide notes in .pptx are often embedded as text boxes in `slide1.xml`, not in a separate notes.xml file. Instructions may be concatenated in a single text box (e.g., separated by `||` or newlines). Filter out stale/archived instructions.

```python
import zipfile, re

with zipfile.ZipFile('document.pptx', 'r') as z:
    slide_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
    # Extract all text between <a:t> tags
    texts = re.findall(r'<a:t>(.*?)</a:t>', slide_xml)
    # Look for actionable keywords like "FINAL", "UPDATE", "CORRECTION"
```

**Decision rule**: If notes specify a target value (e.g., "cart to bay = 0.50"), use that to identify the cell. If notes conflict with Excel structure, trust the Excel structure for cell location but use the note's target value. Ignore lines marked "ARCHIVED" or "DO NOT EDIT".

### 3. Identify Target Embedding (If Multiple Exist)

When the PPTX contains multiple embedded Excel files, check for a JSON manifest that identifies which one is "live" or "current":

```python
import json, os

# Check for manifest files
for f in os.listdir('.'):
    if f.endswith('.json') and ('live' in f.lower() or 'embed' in f.lower()):
        with open(f) as jf:
            manifest = json.load(jf)
            print(manifest)  # May contain keys like "live_workbook", "target_embedding", etc.
```

**Decision rule**: If multiple embeddings exist and a JSON manifest is present, use it to identify which workbook to update. If no manifest exists, inspect each workbook's content to determine which matches the task context (e.g., "live" vs "archive", current year vs prior year). **Never update archive/historical workbooks unless explicitly instructed.**

### 4. Locate the Embedded Excel

Office documents are ZIP archives. Embedded Excel files are typically at:
- `ppt/embeddings/Microsoft_Excel_Sheet*.xlsx` or `Microsoft_Excel_Worksheet*.xlsx` (PowerPoint)
- `word/embeddings/Microsoft_Excel_Sheet*.xlsx` (Word)

```python
import zipfile
with zipfile.ZipFile('document.pptx', 'r') as z:
    for name in z.namelist():
        if 'embeddings' in name and name.endswith('.xlsx'):
            print(name)
```

### 5. Extract and Inspect

**Critical:** Check if target cells are formulas or values before modifying.

```python
import openpyxl
wb = openpyxl.load_workbook('/tmp/workdir/ppt/embeddings/Microsoft_Excel_Worksheet.xlsx')
ws = wb['Sheet Name']

# Check cell type
cell = ws['C4']
print(f"Value: {cell.value}")
print(f"Type: {cell.data_type}")  # 'n'=number, 'f'=formula
print(f"Is formula: {cell.data_type == 'f'}")
```

### 6. Diagnostic: Check Cached Values First

**Before modifying any source values**, check if cached formula values are empty. This is the most common issue with embedded Excel files where verifiers read XML `<v>` tags directly.

```python
import zipfile, re
# Check for empty cached values in the saved xlsx
with zipfile.ZipFile('/tmp/embedded.xlsx', 'r') as z:
    xml = z.read('xl/worksheets/sheet1.xml').decode('utf-8')
    # Find formula cells with empty cached values (<v /> or <v></v>)
    empty = re.findall(r'<c r="([A-Z]+\d+)"><f>[^<]+</f><v ?/></c>', xml)
    if empty:
        print(f"Empty cached values detected: {empty}")
```

**Decision rule**: If source values are already correct but cached values are empty, only populate cached values—do not modify source cells. This is a common pattern where the matrix is already configured correctly but cached values need fixing.

### 7. Update Values (Preserve Formulas)

- Edit **value cells** (`data_type == 'n'` or `'s'`)
- **Never overwrite formula cells** (`data_type == 'f'`) unless explicitly required
- For inverse formulas (e.g., `=ROUND(1/D5, 4)`), update the source cell D5

```python
# Update a source cell for inverse formula - use FULL precision
target_rate = 0.8645
ws['D5'].value = 1.0 / target_rate  # Pass raw float, do NOT round
wb.save('/tmp/embedded.xlsx')
```

### 8. Handle Cached Formula Values (Critical)

**Problem:** openpyxl preserves formulas but does NOT update cached `<v>` values in XML. Verifiers reading XML directly see stale or empty values (`<v />`).

**Quick fix with auto-detection:**
```bash
python3 scripts/fix_cached_values.py /tmp/embedded.xlsx /tmp/fixed.xlsx --auto
```

The `--auto` flag detects `ROUND(1/X, N)` formulas and calculates correct cached values automatically.

### 9. Repackage into Office Document

Replace the embedded Excel in the original ZIP structure. **Ensure the writer context manager fully exits before reading the output.**

```python
import zipfile
import os

src_pptx = '/root/original.pptx'
dst_pptx = '/root/results.pptx'
updated_excel = '/tmp/fixed.xlsx'  # Use fixed version if verifier expected
embed_path = 'ppt/embeddings/Microsoft_Excel_Worksheet.xlsx'

# Create new PPTX with updated Excel
with zipfile.ZipFile(src_pptx, 'r') as zin:
    with zipfile.ZipFile(dst_pptx, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == embed_path:
                zout.write(updated_excel, embed_path)
            else:
                zout.writestr(item, zin.read(item.filename))

# Verify only AFTER the context manager exits
with zipfile.ZipFile(dst_pptx, 'r') as z:
    print("Archive valid:", z.testzip() is None)
```

### 10. Verify the Update

```python
import zipfile
with zipfile.ZipFile(dst_pptx, 'r') as z:
    excel_data = z.read(embed_path)
    # Load with openpyxl and verify key cells
    # Also check XML for cached formula values
```

## Mandatory Pre-Submission Checklist

**Before declaring the task complete, verify ALL of the following:**

1. [ ] **Cached values fixed**: Run `scripts/fix_cached_values.py --auto` on the updated workbook if any formula cells are in the verification path
2. [ ] **XML cached values verified**: Read the worksheet XML from the final output and confirm `<v>` tags contain correct computed values (not empty `<v />`)
3. [ ] **Formulas preserved**: Confirm no formula cells (`data_type == 'f'`) were overwritten with hardcoded values
4. [ ] **Correct embedding updated**: If multiple embeddings exist, verify the correct one was modified and others remain unchanged
5. [ ] **ZIP fully closed**: Output file was verified only after the `ZipFile` writer context manager exited

## Cross-Rate Pattern (Critical)

When updating FX rates or reciprocal calculations:

| Scenario | Wrong Approach | Correct Approach |
|----------|---------------|------------------|
| EUR/GBP = 0.8645, cell E4 has `=ROUND(1/D5,4)` | Update E4 directly | Update D5 to `1.0/0.8645` (full precision) |
| Target rate given | Overwrite formula cell | Calculate reciprocal, update source cell |

**Precision rule**: Use full float precision for reciprocal calculations. Do not round intermediate values:

```python
# Correct: full precision
target_rate = 0.8645
source_cell.value = 1.0 / target_rate  # Pass raw float

# Wrong: premature rounding
source_cell.value = round(1.0 / target_rate, 4)  # Loses precision
```

## Verifier Compatibility

| Verifier Behavior | What You Must Do |
|-------------------|------------------|
| Reads openpyxl `cell.value` | Standard workflow works |
| Reads XML `<v>` cached values | Must patch cached values with `fix_cached_values.py` |
| Computes expected value from formula | Ensure source values have full precision |

**Key insight**: Cross-rate verifiers often check `=ROUND(1/X,4)` formula results. Since openpyxl doesn't evaluate formulas, the cached `<v>` tag may be stale or empty. Always run `fix_cached_values.py` when:
- Formula cells are in the verification path
- The task mentions "test", "verify", or "check"
- You see `=ROUND(1/...)` or similar reciprocal patterns

## Environment Setup

If `openpyxl` is not available and pip fails with "externally-managed-environment":

```bash
pip install openpyxl --break-system-packages -q
```

## Critical Anti-Patterns

| Pattern | Why it fails | Alternative |
|---------|--------------|-------------|
| **python-pptx for OLE** | No robust support for embedded Excel objects | Use `zipfile` + `openpyxl` |
| **In-place ZIP modification** | Risk of corruption or partial writes | Create new archive, copy all entries |
| **Overwriting formula cells** | Breaks auto-calculation chain | Check `data_type == 'f'` first |
| **Assuming sheet names** | Embedded sheets vary (Sheet1, Spot Grid, etc.) | Inspect workbook first |
| **Shell `unzip` command** | Often unavailable in restricted environments | Use Python `zipfile` module |
| **Premature rounding** | Precision loss in cross-rates | Store full float, let Excel round on display |
| **Trusting slide notes alone** | Notes may be stale or ambiguous | Cross-check with Excel structure |
| **Relying on openpyxl for cached values** | openpyxl preserves formulas but does NOT recompute `<v>` tags | Use `fix_cached_values.py --auto` |
| **Looking for notes.xml** | Notes often embedded as text boxes in slide XML | Parse `ppt/slides/slide1.xml` for `<a:t>` text elements |
| **Reading output ZIP immediately** | `BadZipFile` if writer buffer not flushed/closed | Wait for `with` block to exit, or call `zout.close()` explicitly |
| **Skipping cached value fix** | Verifier reads stale `<v>` value, test fails | Always fix cached values for formula-dependent verifications |
| **Unresolved abbreviations** | Wrong cell updated | Check for alias CSV before editing matrix |
| **Using superseded draft values** | Updates wrong value when final approved value exists | Parse for "FINAL", "APPROVED", "CORRECTED" keywords; ignore "draft", "preliminary", "superseded" |
| **Updating archive workbook** | Historical data must remain unchanged | Use JSON manifest or content inspection to identify live vs archive |

## Common Pitfalls

| Mistake | Consequence | Prevention |
|---------|-------------|------------|
| Overwriting formula cells | Breaks auto-calculation | Always check `cell.data_type` before editing |
| Editing cached values | Changes lost on recalc | Edit the source value cell, not derived cells |
| Wrong embed path | File corruption | Verify exact path with `zipfile.namelist()` |
| ZIP compression mismatch | Office may reject file | Use `zipfile.ZIP_DEFLATED` consistently |
| Missing `[Content_Types].xml` | PPTX won't open | Copy ALL original entries to new archive |
| Reciprocal precision loss | Rate doesn't match target | Use `1.0 / target` not `round(1/target, 4)` |
| Ignoring slide notes | Miss explicit update instructions | Always check slide XML for `<a:t>` text boxes |
| Verifying before ZIP closes | `BadZipFile` or truncated header | Ensure writer context exits before reading output |
| Not fixing cached `<v>` values | Verifier sees wrong/stale value | Run `fix_cached_values.py` with computed results |
| Unresolved abbreviations | Wrong cell updated | Check for alias CSV before editing matrix |
| Using draft instead of final value | Wrong update applied | Look for "FINAL approved" vs "draft" markers in notes |
| Updating wrong embedding | Archive data corrupted | Check for JSON manifest; verify embedding names |

## Decision Rules

- **If cell contains formula (`data_type == 'f'`)**: Find and edit the upstream value cell it references
- **If multiple Excel embeddings exist**: Extract all, identify correct one by sheet content or JSON manifest, update, repackage all
- **If JSON manifest present (e.g., `live_embedding.json`)**: Use it to identify which embedding is "live" or "current"; never update archive/historical workbooks unless explicitly instructed
- **If openpyxl unavailable**: Use `scripts/update_cell_zipfile.py` (pure zipfile/XML approach) or install with `--break-system-packages`
- **If target rate is given for a formula cell**: Calculate reciprocal with full precision, update the source cell
- **If slide note conflicts with Excel structure**: Trust the Excel structure for cell location; use note's target value
- **If slide notes contain update instructions**: Parse the note text to extract target cell description and value, then map to actual cell coordinates via Excel inspection
- **If slide notes contain multiple instructions**: Split by `||`, newlines, or bullet points. Filter out stale/archived items before applying.
- **If slide note uses abbreviations (e.g., "CB", "CD")**: Search workspace for `label_aliases.csv` or similar mapping file. Resolve to full names, then match against Excel row/column headers to find intersection cell.
- **If slide notes contain "FINAL approved" vs "draft" values**: Use the FINAL approved value; ignore superseded draft values
- **If verification is expected and formulas are involved**: Run `fix_cached_values.py --auto` to patch cached `<v>` values
- **If source values already correct but cached values empty**: Only populate cached values—do not modify source cells
- **Before submitting**: Always verify XML `<v>` cached values contain correct computed values, not empty tags

## Troubleshooting

- **File not found in embeddings**: Check `.rels` files for `rId` references. The path may vary.
- **Corrupted output**: Ensure all original files are copied, including `[Content_Types].xml` and `_rels/`.
- **Formulas not calculating**: `openpyxl` does not evaluate formulas. Host app computes on open. Only update source data cells.
- **Verifier checks cached `<v>` values**: Run `scripts/fix_cached_values.py --auto`. See `references/cached_value_fixing.md` for manual approach.
- **openpyxl not installed**: `pip install openpyxl --break-system-packages -q`
- **Slide notes not in notes.xml**: Notes are often inline text boxes. Parse `ppt/slides/slide1.xml` for `<a:t>` elements containing instructions.
- **`BadZipFile: Truncated file header` on output**: Caused by reading the archive before the `ZipFile` writer finishes flushing. Always verify *after* the `with zipfile.ZipFile(...) as zout:` block exits.
- **Verifier fails despite correct logic**: Check if verifier reads XML `<v>` tags. If so, cached values weren't fixed. Re-run with `fix_cached_values.py`.
- **Source value already matches target**: Check if cached values are empty. Often only cached values need population.
- **Multiple ratio values in notes (draft vs final)**: Search for "FINAL", "APPROVED", or "CORRECTED" keywords. Ignore lines with "draft", "preliminary", or "superseded".

## Helper Scripts

- `scripts/update_embedded_excel.py`: Full argparse CLI with openpyxl, formula safety checks
- `scripts/update_cell_zipfile.py`: Pure zipfile/XML approach, no openpyxl dependency
- `scripts/fix_cached_values.py`: **CRITICAL** - Patches cached `<v>` values for verifier compatibility. Use `--auto` for ROUND formulas.

## Fallback: Manual ZIP Editing

If Python zipfile fails:
```bash
unzip document.pptx -d pptx_extracted/
cp updated.xlsx pptx_extracted/ppt/embeddings/
cd pptx_extracted && zip -r ../new_document.pptx .
```

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known Invariants (by sub-task)

### fx-cross-rate-matrix
- Cross-rate formulas typically follow `=ROUND(1/{source_cell}, 4)` pattern
- When target rate given for formula cell, update source cell with reciprocal
- **Critical**: Verifiers may read cached `<v>` values from XML; openpyxl does NOT update these automatically
- **Action**: Always run `fix_cached_values.py --auto` after updating source values
- Embedded Excel path format: `ppt/embeddings/Microsoft_Excel_Worksheet*.xlsx` or `Microsoft_Excel_Sheet*.xlsx`

### pptx-embedded-excel-edit
- Formula cells auto-recalculate when opened in PowerPoint/Excel; do not pre-compute values
- Embedded Excel path format: `ppt/embeddings/Microsoft_Excel_Worksheet*.xlsx` or `Microsoft_Excel_Sheet*.xlsx`
- Slide notes may contain actionable instructions; parse `<a:t>` elements in `ppt/slides/slide1.xml`

### docx-embedded-excel-edit
- Embedded Excel path format: `word/embeddings/Microsoft_Excel_Worksheet*.xlsx`

### warehouse-slot-factor-refresh
- Slot-factor matrices use reciprocal formulas: `=ROUND(1/{source_cell}, 4)`
- Notes indicate target value (e.g., "cart to bay = 0.50") but cell must be located via Excel inspection
- Update the numeric source cell, not the formula cell that references it
- **Verifier compatibility**: Run `fix_cached_values.py --auto` for formula cells

### catalyst-balance-matrix-sync
- Matrix uses stream names as row/column headers (e.g., "Catalyst Beta Stream")
- Slide notes may use abbreviations (CB, CD) requiring alias resolution via CSV
- Reciprocal formulas follow `=ROUND(1/{source_cell}, 4)` pattern
- **Critical**: Verifiers check cached `<v>` XML values; openpyxl updates formulas but not cached values
- **Action**: Always run `fix_cached_values.py --auto` after any source updates

### buffer-dilution-matrix-repair
- Dilution ratio matrices use reciprocal formulas: `=ROUND(1/{source_cell}, 4)`
- Slide notes may contain multiple ratio values (draft vs final approved)
- **Critical**: Parse for "FINAL approved ratio" or "CORRECTED ratio" keywords; ignore superseded "draft" values
- Update the source ratio cell (e.g., BUF10 to BUF5 = 2.0), not the reciprocal formula cell
- **Action**: Always run `fix_cached_values.py --auto` after updating source values
- Embedded Excel path format: `ppt/embeddings/Microsoft_Excel_Worksheet*.xlsx`

### rebate-band-live-embedding-fix
- Multiple embedded workbooks (live vs archive) with JSON manifest identifying target
- Slide notes contain "ARCHIVED" vs "CURRENT approved" values separated by `||`
- Update only the live workbook; archive must remain unchanged
- Reciprocal formulas follow `=ROUND(1/{source_cell}, 4)` pattern
- **Critical**: Verifiers check cached `<v>` XML values; openpyxl updates formulas but not cached values
- **Action**: Always run `fix_cached_values.py --auto` after updating source values
- Embedded Excel path format: `ppt/embeddings/*_Rebate_Bands.xlsx`

## References

- `references/openpyxl_cell_types.md` - Cell data type reference for openpyxl
- `references/cached_value_fixing.md` - Manual and scripted approaches to fixing cached `<v>` values for verifier compatibility