---
name: image-to-structured-excel
description: Extract structured data from image collections using OCR and output to Excel. Use for receipts, invoices, claims, utility bills, labeled data, or tabular forms requiring normalization. Essential when reference CSV files exist for ID validation/enrichment, when dates may be ambiguous (DD/MM vs MM/DD), when OCR text has split-line formatting or unit symbol corruption (m³→m?), when tabular data has variable column alignment, when multiple total/amount keywords must be tried, or when template workbook preservation is required. Also use for construction forms, measurement sheets, and multi-item tables where row count validation is critical.
---

# Image to Structured Excel Extraction

Extract structured data from image collections using OCR, with optional reference-based field enrichment and template preservation.

## When to Use
- Multiple images containing receipts, invoices, claims, utility bills, labels, or documents with consistent structure
- **Tabular forms** with line items (construction measurements, expense reports) requiring multi-row extraction per image
- Need to extract dates, amounts, codes/IDs from images to Excel
- Reference CSV exists with additional fields to merge (e.g., employee_id, trip_id from claim_code)
- Output requires specific column order, ISO dates, and formatted amounts
- Partial matches expected: some extracted IDs won't exist in reference file
- **Invoices/Bills**: Multiple total keywords may appear (GRAND TOTAL, TOTAL DUE, TOTAL, SUBTOTAL, PAY THIS AMOUNT, CURRENT CHARGES, AMOUNT DUE)
- **Template workbooks**: Must preserve existing sheets (e.g., cover) while updating data sheets
- **OCR artifacts present**: Unit symbols corrupted (m³→m?), formatting characters (=, •), split lines

## Workflow

1. **Discover inputs**: List images; note naming pattern
2. **Inspect samples**: View 2-3 images to identify field patterns, **date format** (DD/MM vs MM/DD), **amount keyword patterns**, and **table structure**
3. **Check for reference data**: Load `*_roster.csv`, `known_*.csv`, or similar for ID enrichment
4. **Check for template workbook**: If template exists, preserve all non-data sheets exactly
5. **Determine date format** by inspection:
   - Day > 12 in sample → DD/MM/YYYY format
   - Month > 12 in sample → MM/DD/YYYY format  
   - Second value > 12 → MM/DD format confirmed (e.g., 02/14/2024 = Feb 14)
   - Mixed or ambiguous → inspect multiple samples; prefer DD/MM for international/claim context
6. **Build extraction script**:
   - OCR with `pytesseract`
   - **Normalize OCR artifacts**: See `references/ocr-table-extraction.md` for unit symbol and formatting fixes
   - **Table parsing**: Handle variable column alignment, multi-line items
   - Regex extraction for codes, dates, amounts
   - **Multi-line OCR handling**: Use `re.DOTALL` or normalize newlines for split patterns like `TOTAL\n\nDUE`
   - **Total/Amount extraction**: Check keywords in priority order. See `references/amount-keyword-patterns.md`
   - **Date normalization** to `YYYY-MM-DD` with auto-detection
   - **Price formatting**: string with exactly 2 decimals
7. **Execute with python3**: `python3 script.py` (not `python`)
8. **Validate output**: Check Excel structure, empty cell handling, date/price formatting, template preservation, **and expected row counts per image**

## Key Decision Rules

| Pattern | Action |
|---------|--------|
| Reference CSV exists | Load into dict keyed by ID; enrich rows where key exists |
| Partial roster matches | Expected: some IDs in images, some in CSV; unmatched → empty strings |
| Date format ambiguous | Check sample with day > 12 or month > 12; second value > 12 confirms MM/DD |
| Multiple date formats detected | Support both DD/MM/YYYY and MM/DD/YYYY in parser |
| OCR shows split lines (TOTAL\\n\\nDUE) | Use `re.DOTALL` flag or normalize whitespace first |
| Amount keyword varies | Try priority list: PAY THIS AMOUNT → CURRENT CHARGES → AMOUNT DUE → TOTAL DUE → TOTAL → SUBTOTAL |
| Template workbook exists | Preserve non-target sheets; only update target sheet cells |
| **Tabular data with line items** | See `references/ocr-table-extraction.md` for parsing strategies; validate row count per image |
| **OCR unit symbol corruption** (m³→m?) | Normalize: `re.sub(r'm\\?|=m\\s*=?', 'm3', text)` |
| **Date with second value > 12** | Confirms MM/DD format (e.g., 02/14/2024 = Feb 14, not day 14) |
| Excel shows `None` for missing values | Use empty string `''` not `None` when writing cells |
| Price extraction | Strip currency prefixes; output as `f"{value:.2f}"` string |
| Roster has tab separator | Use `csv.DictReader(f, delimiter='\t')` |
| Row count mismatch expected | Log warning, retry with alternative parsing, or flag for manual review |

## Multi-Line OCR Patterns

OCR output often splits logical lines:

```python
# Split-line pattern: "TOTAL\n\nDUE: 120.75"
# Use DOTALL to match across newlines, or normalize first
text_normalized = re.sub(r'\n+', ' ', text)
# Then: r'TOTAL\s*DUE:\s*\$?([\d.]+)'

# Or with DOTALL:
match = re.search(r'TOTAL\s*DUE:\s*\$?([\d.]+)', text, re.DOTALL | re.IGNORECASE)
```

## Date Auto-Detection

```python
def parse_date_auto(date_str):
    """Parse date string with automatic MM/DD vs DD/MM detection."""
    import re
    
    # Try ISO format first
    iso_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str.strip())
    if iso_match:
        return date_str.strip()
    
    # Try delimited formats
    m = re.match(r'(\d{2})[/-](\d{2})[/-](\d{4})', date_str.strip())
    if not m:
        return None
    
    first, second, year = int(m.group(1)), int(m.group(2)), m.group(3)
    
    # Second value > 12 confirms MM/DD (month first)
    if second > 12:
        return f"{year}-{first:02d}-{second:02d}"  # MM/DD
    # First value > 12 confirms DD/MM (day first)  
    elif first > 12:
        return f"{year}-{second:02d}-{first:02d}"  # DD/MM
    # Ambiguous: default to context (DD/MM for international)
    else:
        return f"{year}-{second:02d}-{first:02d}"  # DD/MM default
```

## Template Workbook Preservation

```python
import openpyxl

# Load template preserving everything
wb = openpyxl.load_workbook(template_path)

# Preserve cover sheet exactly
# Only modify target sheet
cover_sheet = wb['cover']  # Don't touch this
bills_sheet = wb['bills']  # Update this

# Clear existing data rows, keep header
for row in bills_sheet.iter_rows(min_row=2, max_row=bills_sheet.max_row):
    for cell in row:
        cell.value = None

# Write new data starting at row 2
for idx, record in enumerate(records, start=2):
    bills_sheet.cell(row=idx, column=1, value=record['scan_name'])
    bills_sheet.cell(row=idx, column=2, value=record['bill_date'])
    bills_sheet.cell(row=idx, column=3, value=record['amount_due'])

wb.save(output_path)
```

## Validation Checklist

- [ ] Excel opens without errors
- [ ] Template sheets preserved exactly (cover, instructions, etc.)
- [ ] Target sheet name matches requirement exactly
- [ ] Header row with correct column names
- [ ] **Row count validated**: Expected items per image matches extracted
- [ ] Dates in ISO format `YYYY-MM-DD`
- [ ] Prices as strings with exactly 2 decimal places
- [ ] Unmatched roster entries have empty cells (not `None` literal)
- [ ] Rows sorted by filename ascending
- [ ] Reference-enriched fields populated where ID exists
- [ ] **Split-line OCR**: Verify amounts extracted despite newlines between keywords
- [ ] **OCR artifacts normalized**: Unit symbols, formatting characters cleaned

## Anti-Patterns

- **Do not** assume DD/MM vs MM/DD without inspecting sample dates > 12
- **Do not** use `python` without version suffix—use `python3`
- **Do not** write `None` to Excel cells; use `''` for empty values
- **Do not** assume all extracted IDs exist in reference file
- **Do not** preserve currency symbols in output
- **Do not** assume single-line OCR—newlines often split logical fields
- **Do not** overwrite entire workbook when template must be preserved
- **Do not** assume single amount keyword—check priority list
- **Do not** assume fixed column positions in tables—OCR shifts horizontally
- **Do not** parse tables only by split position—use regex for prices and flexible tokenization

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `python: command not found` | Use `python3` |
| Dates parsed incorrectly | Inspect samples first; check for MM/DD vs DD/MM; verify second value > 12 indicates MM/DD |
| Empty cells show as `None` | Convert Python `None` to `''` before writing |
| Roster not loading | Check delimiter—may be tab, not comma |
| Reference lookup failing | Verify ID normalization (strip, case, hyphens match) |
| Wrong row order | Add `sorted(os.listdir(...))` |
| Amount extraction fails | Check for split-line OCR; use `re.DOTALL` or normalize whitespace |
| Template cover sheet modified | Load template with `openpyxl`, modify only target sheet, preserve others |
| **Missing line items** (e.g., 2 of 3 extracted) | Table parsing too brittle—see `references/ocr-table-extraction.md`; add row count validation |
| **OCR unit symbols wrong** (m³→m?) | Normalize with regex before parsing; see `references/ocr-table-extraction.md` |
| **Column alignment varies** | Use flexible parsing—find price by regex, then extract preceding tokens |

## Extended Patterns

See `references/date-parsing.md` for extended date handling.
See `references/order-extraction-patterns.md` for claim/invoice patterns including total keyword priorities.
See `references/amount-keyword-patterns.md` for utility bill and receipt amount extraction patterns.
See `references/ocr-table-extraction.md` for tabular data extraction with OCR artifact handling.
See `scripts/extract_from_images.py` for base implementation.
See `scripts/preserve_template_excel.py` for template preservation helper.
