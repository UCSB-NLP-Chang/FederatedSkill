---
name: ocr-data-extraction
description: Extract structured fields (dates, prices, codes, order IDs, line items) from product labels, shelf tags, receipts, invoices, construction forms, or e-commerce documents using OCR with multiple fallback strategies. Use when single-pass OCR misses data, when input images have varying quality, when processing batches requiring deduplication against reference lists, when extracting multi-item tabular data per document, or when handling documents with ambiguous date formats (DD/MM vs MM/DD).
---

# OCR Data Extraction

Extract specific fields from images using multi-strategy OCR. Single configurations often fail on real-world labels; use iterative preprocessing and page segmentation modes. For batch processing with master lists, validate against reference data and handle duplicates explicitly.

## Quick Start

1. **Batch process images** with multiple Tesseract configurations
2. **Extract fields** using domain-specific regex from all OCR outputs
3. **Normalize** dates to ISO format, prices to decimal
4. **Handle ambiguous dates**: Try DD/MM first, fall back to MM/DD if invalid
5. **Validate** against reference lists if provided (e.g., known order IDs)
6. **Deduplicate** using first-occurrence-wins strategy
7. **For multi-item docs**: Deduplicate items across OCR strategies, aggregate summaries
8. **Validate** completeness against input file count

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

### Dates (Priority Order)

1. `EXP(?:IRY)?[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})` - Expiry dates
2. `MFG(?:DATE)?[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})` - Manufacturing dates
3. `(\d{1,2}[/-]\d{1,2}[/-]\d{4})` - Generic fallback

**Critical**: Use ambiguous date resolution (see below) - do not assume DD/MM or MM/DD consistently across a batch.

### Prices

- `(?:RM|MYR|RS|\\$|€|£)\s*(\d{1,3}(?:,\d{3})*\.\d{2})` - Prefixed currency
- `(\d+\.\d{2})\s*(?:RM|MYR|\\$)?` - Suffixed or bare decimal

### Invoice-Specific Totals

Invoices use varying labels for final amounts. Priority order:
1. `GRAND\s*TOTAL` - Most specific
2. `TOTAL\s*DUE`, `TOTAL\s*AMOUNT` - Explicit totals
3. `PAY\s*THIS\s*AMOUNT`, `CURRENT\s*CHARGES`, `AMOUNT\s*DUE` - Utility bill patterns
4. `(?<!SUB)\s*TOTAL` - Generic total (exclude subtotals)

See `references/regex_patterns.md` for complete invoice patterns.

### Multi-Line Keywords

OCR frequently splits compound keywords across lines with blank lines in between, or separates keywords from their values. Common patterns:
- `TOTAL\n\nDUE: 120.75` — keyword split from value
- `PAY THIS AMOUNT\n\n1234.56` — blank line between keyword and value
- `TOTAL\nDUE` on separate lines for "TOTAL DUE"

**Extraction Strategy**: When a keyword is found but no amount follows on the same line, search the next 3-5 lines for the amount pattern. For compound keywords like "TOTAL DUE", check if parts appear on subsequent lines.

See `references/parsing_patterns.md` for the `extract_amount_multiline()` function.

### Order IDs (E-commerce)

- `\bORD-\d{4}-\d{5}\b` - Standard format (ORD-2024-00123)
- `\bSO-\d{4}-\d{3}\b` - Sales orders (SO-2024-001)
- `\bINV-\d{8}\b` - Invoice format (INV-20240001)
- `\b(?:ORD|SO|INV|PO)[-\s]?\d{4}[-\s]?\d{3,6}\b` - Generic fallback

### Quantities from Line Items (Context-Aware)

**Critical Pitfall**: Naive `\d+` regex matches numbers embedded in item names (e.g., "Concrete C30" → matches "30" as quantity instead of actual quantity "50").

**Solution**: Use context-aware patterns matching quantities AFTER the item name.

| Example Line | Wrong Regex | Wrong Match | Correct Regex | Correct Match |
|-------------|-------------|-------------|---------------|---------------|
| "Concrete C30 50 m³" | `\d+` | "30" | `C30\s+(\d+)` | "50" |
| "Steel reinforcement 100 pcs" | `\d+` | "Steel...100" | `reinforcement\s+(\d+)` | "100" |

**Implementation**: See `references/parsing_patterns.md` for `extract_quantity_with_context()` function.

## Multi-Item Extraction

When extracting multiple line items per document (construction forms, order forms, invoices with detailed rows):

1. **Identify item patterns**: Look for repeated row structures (description, quantity, unit price)
2. **Deduplicate across OCR strategies**: Multiple OCR passes return the same items. Track with a set:
   ```python
   seen_items = set()
   for item in extracted_items:
       key = (item['description'],)  # or include more fields for uniqueness
       if key not in seen_items:
           seen_items.add(key)
           items.append(item)
   ```
3. **Extract quantities carefully**: Use context-aware regex (see above)
4. **Aggregate for summaries**: Group by project/order code, calculate totals, use first date

## Date Format Ambiguity Resolution

**The Problem**: The same batch may mix DD/MM/YYYY (EU/Asia) and MM/DD/YYYY (US) formats. `02/03/2024` could be March 2nd or February 3rd.

**Resolution Strategy**:
1. **Try DD/MM/YYYY first** (statistically more common globally)
2. **Validate**: Day ≤ 31, Month ≤ 12, and must be a valid calendar date
3. **If invalid, try MM/DD/YYYY**
4. **If still invalid**, flag for manual review (likely OCR error)

**Decision Rule**: When day ≤ 12 and month ≤ 12, both formats are mathematically valid. Use these heuristics:
- If one interpretation fails calendar validation (e.g., day 31 in month with 30 days), use the other
- If both valid and you have batch context, check surrounding dates for format consistency
- When uncertain, prefer DD/MM for documents from non-US sources

**Implementation Pattern**:
```python
def parse_date_ambiguous(text):
    match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', text)
    if not match:
        return None
    a, b, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
    
    # Try DD/MM first
    if a <= 31 and b <= 12:
        try:
            datetime(y, b, a)  # year, month, day
            return f"{y:04d}-{b:02d}-{a:02d}"
        except ValueError:
            pass
    
    # Fall back to MM/DD
    if a <= 12 and b <= 31:
        try:
            datetime(y, a, b)
            return f"{y:04d}-{a:02d}-{b:02d}"
        except ValueError:
            pass
    
    return None
```

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
- **Watch for format mixing**: Same batch may use DD/MM/YYYY and MM/DD/YYYY - use ambiguity resolution

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
- [ ] Dates parse as valid calendar dates (not just regex matches)
- [ ] Ambiguous dates resolved using validation logic (not assumed format)
- [ ] Prices are numeric or properly formatted strings (not mixed)
- [ ] Data sorted by filename/identifier

## Anti-Patterns

- **Don't use single PSM mode**: PSM 6 misses scattered text; PSM 11 misorders structured blocks
- **Don't skip preprocessing**: Low-contrast shelf labels often require sharpening
- **Don't assume consistent date formats**: Same dataset may mix `DD/MM/YYYY` and `MM/DD/YYYY`
- **Don't trust OCR symbols**: `0` vs `O`, `1` vs `l`, `/` vs `-` require regex flexibility
- **Don't process files in arbitrary order**: Always sort filenames before deduplication to ensure deterministic "first" occurrence
- **Don't skip reference validation**: When `known_orders.csv` or similar is provided, use it to filter invalid extractions
- **Don't remove duplicate rows**: Keep all filenames, mark duplicates with null values to maintain alignment
- **Don't assume single date format per batch**: Always validate date feasibility (day/month ranges) before accepting a format interpretation
- **Don't assume keywords and values are on the same line**: OCR splits compound keywords and inserts blank lines; always check subsequent lines when a keyword has no immediate value
- **Don't use naive `\d+` regex for quantities**: Item names may contain numbers (e.g., "C30") — match quantities AFTER item name
- **Don't forget to deduplicate across OCR strategies**: Multiple strategies return the same items — use a set keyed by item identifier

## Troubleshooting

| Symptom | Solution |
|---------|----------|
| Low confidence scores | Increase image resolution to 300+ DPI before OCR |
| Missing price currency | Try PSM 11; check for split lines between symbol and number |
| Date parsing errors | Accept multiple separators (`/`, `-`, `.`) in regex; use ambiguity resolution for DD/MM vs MM/DD |
| Partial text extraction | Run sharpening filter then retry with PSM 6 |
| Duplicate detection failing | Ensure filenames are sorted before processing; check case sensitivity |
| Order ID not in reference list | Check for OCR errors (O→0, I→1); try fuzzy matching if exact match fails |
| Inconsistent row count | Verify you're not filtering out invalid/duplicate rows—set to null instead |
| Some dates off by month/day | Implement fallback parsing: if DD/MM yields invalid date, try MM/DD |
| Invoice totals not found | Try alternative labels: "GRAND TOTAL", "TOTAL DUE", "PAY THIS AMOUNT", "CURRENT CHARGES", "AMOUNT DUE" before generic "TOTAL" |
| Keyword found but no value | Search next 3-5 lines for amount; OCR splits compound keywords across lines with blank gaps |
| Quantities are wrong | Check if item names contain numbers that regex is matching instead — use context-aware patterns |
| Duplicate items in output | Add deduplication using a set keyed by item identifier across OCR strategies |

## Known invariants (by sub-task)

### B1: Image OCR → Excel with date/price extraction
- Output Excel must have columns exactly as specified (e.g., {filename, date, price})
- Dates must be ISO format YYYY-MM-DD; partial MM/YYYY → YYYY-MM-01
- Prices as float with full precision (no rounding in script)
- Row count must match image count
- Sorted by filename

### B2: OCR with duplicate handling & reference validation
- When duplicate keys exist across images, keep first occurrence by filename sort order
- Null out data fields for duplicate rows (preserve filename)
- Validate extracted keys against reference file if provided
- Output must include all input files as rows, even if data is null

### B3: OCR with roster matching (e.g., travel claims)
- Extract key field (e.g., claim_code) from each image
- Load roster/reference CSV into a dict keyed by the extracted field
- For each image, populate additional columns (e.g., employee_id, trip_id) from the roster dict
- If key not in roster, leave those columns empty (None in openpyxl → empty cell in Excel)
- All input files must appear as rows, even if unmatched

### B4: Multi-item extraction per document (e.g., construction forms)
- Each document may contain multiple line items (description, quantity, unit price)
- Deduplicate items across OCR strategies using a set keyed by item identifier
- Use context-aware regex for quantities when item names contain numbers
- Output details sheet with one row per item, summary sheet with aggregated totals
- Group by project/order code for summaries

## References

- `references/regex_patterns.md` - Extended regex library for dates, prices, barcodes, IDs, order numbers, and invoice-specific patterns
- `references/parsing_patterns.md` - Date disambiguation logic, invoice total keyword priority, price extraction patterns, quantity extraction with context-aware regex, and multi-item deduplication
- `references/dedup_validation_patterns.md` - Python patterns for duplicate detection and reference file validation
- `references/roster_matching_patterns.md` - Roster matching workflows and openpyxl row-writing best practices
- `scripts/extract_to_excel.py` - Complete implementation template for OCR extraction to Excel
