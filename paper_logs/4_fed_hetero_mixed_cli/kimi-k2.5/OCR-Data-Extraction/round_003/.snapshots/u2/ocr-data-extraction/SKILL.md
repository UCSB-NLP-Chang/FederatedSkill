---
name: ocr-data-extraction
description: Extract structured fields (dates, prices, codes, order IDs) from product labels, shelf tags, receipts, invoices, or e-commerce documents using OCR with multiple fallback strategies. Use when single-pass OCR misses data, when input images have varying quality, or when processing batches requiring deduplication against reference lists.
---

# OCR Data Extraction

Extract specific fields from images using multi-strategy OCR. Single configurations often fail on real-world labels; use iterative preprocessing and page segmentation modes. For batch processing with master lists, validate against reference data and handle duplicates explicitly.

## Quick Start

1. **Batch process images** with multiple Tesseract configurations
2. **Extract fields** using domain-specific regex from all OCR outputs
3. **Normalize** dates to ISO format, prices to decimal
4. **Validate** against reference lists if provided (e.g., known order IDs)
5. **Deduplicate** using first-occurrence-wins strategy
6. **Validate** completeness against input file count

## Multi-Strategy OCR

Run Tesseract with at least these variants and merge results:

| Preprocessing | PSM Mode | Purpose |
|--------------|----------|---------|
| None (auto) | `--psm 6` | Single uniform block; best for structured labels |
| None (auto) | `--psm 11` | Sparse text; finds scattered/distant text |
| Sharpen + Contrast | `--psm 6` | Low-contrast or blurry labels |
| Threshold (binary) | `--psm 6` | High contrast/background noise |

**PSM Decision Rules:**
- Start with `--psm 6` for aligned, block-style labels
- If text is detected but fragmented/misordered, switch to `--psm 11`
- For vertical or single-column text, try `--psm 4`

## Field Extraction Patterns

Scan OCR output with regex. See `references/regex_patterns.md` for extended library.

**Dates (Priority Order):**
1. `EXP(?:IRY)?[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})` - Expiry dates
2. `MFG(?:DATE)?[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})` - Manufacturing dates
3. `(\d{1,2}[/-]\d{1,2}[/-]\d{4})` - Generic fallback

**Prices:**
- `(?:RM|MYR|RS|\\$|€|£)\s*(\d{1,3}(?:,\d{3})*\.\d{2})` - Prefixed currency
- `(\d+\.\d{2})\s*(?:RM|MYR|\\$)?` - Suffixed or bare decimal

**Order IDs (E-commerce):**
- `\bORD-\d{4}-\d{5}\b` - Standard format (ORD-2024-00123)
- `\bSO-\d{4}-\d{3}\b` - Sales orders (SO-2024-001)
- `\bINV-\d{8}\b` - Invoice format (INV-20240001)
- `\b(?:ORD|SO|INV|PO)[-\s]?\d{4}[-\s]?\d{3,6}\b` - Generic fallback

## Reference-Based Validation

When processing documents against a known master list (e.g., valid order IDs, approved SKUs):

1. **Load reference set** before image processing
   - Expect CSV with column headers: `order_id`, `id`, `code`, or `sku`
   - Or single-column list with one ID per row
2. **Extract candidate values** from OCR output
3. **Validate membership**: `candidate in reference_set`
4. **Handle invalids**: Set value to null/None rather than filtering the row (maintains 1:1 file-to-row mapping)

## Deduplication Workflows

For batches containing duplicate documents (e.g., multiple photos of same order):

**First-Occurrence-Wins Strategy:**
1. **Sort filenames** alphabetically to ensure deterministic "first" occurrence
2. **Track seen IDs** in a set during iteration
3. **First occurrence**: Extract and store all fields normally
4. **Subsequent duplicates**: Set extracted fields to null/None (preserve filename for audit)
5. **Maintain row count**: Output must have exactly one row per input image

**Example Logic:**
```python
seen_ids = set()
for filename in sorted(image_files):
    order_id = extract_from_ocr(filename)
    if order_id in seen_ids:
        order_id, date, total = None, None, None
    else:
        seen_ids.add(order_id)
        date, total = extract_other_fields(filename)
    output_row(filename, order_id, date, total)
```

## Normalization Rules

**Dates:**
- Convert all matches to `YYYY-MM-DD`
- Handle partial dates: `MM/YYYY` → `YYYY-MM-01`
- Validate year range (reject < 1900 or > 2100 as OCR errors)
- Watch for day/month transposition (03/15 vs 15/03)

**Prices:**
- Strip currency symbols for numeric columns
- Remove thousand separators (commas)

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV), unless the task explicitly requires a specific string format. Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)` (unless strings required)
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- Exception: If output spec requires "strings with 2 decimal places", format as strings
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Validation Checklist

Before outputting final file:
- [ ] Row count matches input image count exactly
- [ ] Files processed in sorted order (deterministic deduplication)
- [ ] Duplicates marked with nulls, not removed
- [ ] Extracted IDs validated against reference list (if provided)
- [ ] No empty/null critical fields for first occurrences (flag failures for manual review)
- [ ] Dates parse as valid calendar dates
- [ ] Prices are numeric or properly formatted strings (not mixed)
- [ ] Data sorted by filename/identifier

## Anti-Patterns

- **Don't use single PSM mode**: PSM 6 misses scattered text; PSM 11 misorders structured blocks
- **Don't skip preprocessing**: Low-contrast shelf labels often require sharpening
- **Don't assume consistent formats**: Same dataset may mix `DD/MM/YYYY` and `MM-DD-YYYY`
- **Don't trust OCR symbols**: `0` vs `O`, `1` vs `l`, `/` vs `-` require regex flexibility
- **Don't process files in arbitrary order**: Always sort filenames before deduplication to ensure deterministic "first" occurrence
- **Don't skip reference validation**: When `known_orders.csv` or similar is provided, use it to filter invalid extractions
- **Don't remove duplicate rows**: Keep all filenames, mark duplicates with null values to maintain alignment

## Troubleshooting

| Symptom | Solution |
|---------|----------|
| Low confidence scores | Increase image resolution to 300+ DPI before OCR |
| Missing price currency | Try PSM 11; check for split lines between symbol and number |
| Date parsing errors | Accept multiple separators (`/`, `-`, `.`) in regex |
| Partial text extraction | Run sharpening filter then retry with PSM 6 |
| Duplicate detection failing | Ensure filenames are sorted before processing; check case sensitivity |
| Order ID not in reference list | Check for OCR errors (O→0, I→1); try fuzzy matching if exact match fails |
| Inconsistent row count | Verify you're not filtering out invalid/duplicate rows—set to null instead |

## Known invariants (by sub-task)

(No invariants recorded yet. Update this section when verifier failures reveal task-specific rules.)

## References

- `references/regex_patterns.md` - Extended regex library for dates, prices, barcodes, IDs, and order numbers
- `references/dedup_validation_patterns.md` - Python patterns for duplicate detection and reference file validation
- `references/roster_matching_patterns.md` - Roster matching workflows and openpyxl row-writing best practices
- `scripts/extract_to_excel.py` - Complete implementation template for OCR extraction to Excel
