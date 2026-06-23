---
name: image-data-extraction
description: Extract structured data (dates, prices, order IDs, totals, line items) from images using Tesseract OCR with robust multi-pass preprocessing, regex parsing, and Excel output. Use when tasks require reading text from product labels, receipts, invoices, orders, travel claims, utility bills, construction measurement forms, fuel/transaction receipts, or scanned documents with varying formats and image quality. Supports single-sheet and multi-sheet Excel outputs, nested directory traversal, document type filtering, and project aggregation.
---

# Image OCR Data Extraction

## Overview
Extract structured fields from images using `pytesseract`. Handles inconsistent image quality, varied formats, nested directory structures, and outputs normalized data to Excel/CSV.

## Workflow
1. **Enumerate & Inspect**: List all image files. For nested structures, use `os.walk()` to preserve relative paths and batch IDs.
2. **Filter Document Types**: For mixed document sets, filter non-target docs (cover sheets, promos) before extraction.
3. **Run Multi-Pass OCR**: Apply preprocessing modes and PSM configs. Stop when text exceeds threshold.
4. **Parse & Normalize**:
   - **Dates**: Match formats, normalize to `YYYY-MM-DD`. Disambiguate DD/MM vs MM/DD.
   - **Prices/Totals**: Match currency symbols or keywords. Use keyword priority for invoices. **Raw floats only**.
   - **IDs/Codes**: Match patterns. Normalize OCR errors (O→0, l→1) for transaction refs.
   - **Line Items**: Extract rows with description, quantity, unit price. See `references/construction-patterns.md`.
5. **Reference/Roster Merging**: Load reference CSV. Lookup matching fields. Leave unmatched as `None`.
6. **Handle Duplicates**: Track seen identifiers. Normalize txn refs before comparing.
7. **Aggregation**: For multi-sheet output, use correct logic (latest date per project, form's total - NOT computed sum).
8. **Output**: Write to Excel. Sort by filename or relative_path. Verify row count.

## Multi-Line Keyword Handling (CRITICAL: Skip Blank Lines)
OCR splits keywords and values across lines with blank lines in between:
```
Line 5: 'TOTAL AMOUNT'
Line 6: ''
Line 7: '78.10'
```
**Do NOT only check `i+1`.** Skip blank lines:
```python
def extract_total_multiline(text):
    lines = [l.strip() for l in text.split('\n')]
    TOTAL_KEYWORDS = ['TOTAL AMOUNT', 'GRAND TOTAL', 'TOTAL DUE', 'AMOUNT DUE']
    for i, line in enumerate(lines):
        upper = line.upper()
        for kw in TOTAL_KEYWORDS:
            if kw in upper:
                # # SKIP BLANK LINES - look at subsequent non-empty lines
                for j in range(i + 1, len(lines)):
                    next_line = lines[j].strip()
                    if not next_line:  # Skip blank lines
                        continue
                    match = re.search(r'[\$€£]?\s*([\d,]+\.\d{2})', next_line)
                    if match:
                        return float(match.group(1).replace(',', ''))
                    break  # Found non-blank line without amount
    return None
```

## Nested Directory Traversal
For batched documents in nested folders (e.g., `batch_north/day1/`):
```python
import os
for root, dirs, files in os.walk(dataset_root):
    for f in files:
        if f.lower().endswith(('.jpg', '.jpeg', '.png')):
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, dataset_root)
            batch_name = rel_path.split(os.sep)[0]  # First directory component
```

## Document Type Filtering
Filter by keyword indicators before extraction:
```python
RECEIPT_INDICATORS = ['FUEL RECEIPT', 'PUMP SALE', 'TAX INVOICE', 'TXN REF']
NON_RECEIPT_INDICATORS = ['COVER SHEET', 'PROMOTION', 'ROUTE NOTE', 'LOYALTY']
def is_receipt(text):
    upper = text.upper()
    return any(ind in upper for ind in RECEIPT_INDICATORS) and not any(nind in upper for nind in NON_RECEIPT_INDICATORS)
```

## Transaction Reference Normalization
OCR misreads characters (O→0, l→1). Normalize before deduplication:
```python
def normalize_txn_ref(ref):
    ref = ref.upper().replace('O', '0').replace('l', '1').replace('I', '1')
    return ref
```

## Output precision
Never round, truncate, or fixed-format numeric values. Pass raw floats:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `str(x)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- **Common failure**: `'64.20'` (string) vs `64.2` (float) - verifier rejects strings

## Anti-Patterns
- Do not manually read images and hardcode data. Always use OCR automation.
- Do not format prices with fixed decimals. Pass raw floats.
- Do not only check `i+1` for multi-line amounts. Skip blank lines.
- Do not compare txn refs without normalization. OCR misreads O as 0, l as 1.
- Do not process non-receipt documents. Filter cover sheets, promos first.
- Do not mistake item codes for quantities. "C30" is grade, NOT quantity.
- Do not sum totals across forms. Use LATEST form's total_amount per project.
- Do not use earliest date for aggregation. Use LATEST date (max).
- Do not use `python` command. Use `python3` explicitly.

## Known invariants (by sub-task)

### pharmacy-shelf-label
- Columns: `filename`, `date`, `price`. Row count = image count.

### invoice-extraction
- Columns: `filename`, `date`, `total_amount`. Sheet: `invoices`.
- Keyword priority: `GRAND TOTAL` > `TOTAL DUE` > `AMOUNT DUE` > `TOTAL` > `AMOUNT`

### travel-claims
- Columns: `filename`, `claim_code`, `employee_id`, `trip_id`, `date`, `total_amount`.
- Match `claim_code` against roster CSV. Unmatched: set `None`.

### utility-bills
- Columns: `scan_name`, `bill_date`, `amount_due`.
- Template workbook: preserve all sheets, remove placeholder rows.

### construction-measurement
- Two sheets: `details` (`filename`, `project_code`, `item_description`, `quantity`, `unit_price`) + `summary` (`project_code`, `date`, `total_amount`).
- Summary: LATEST form's date and total (NOT computed sum).

### fuel-transaction-receipts
- Columns: `batch_name`, `relative_path`, `txn_ref`, `date`, `total_amount`.
- Filter non-receipts (cover sheets, promos, route notes, loyalty forms).
- Normalize txn refs (O→0, l→1). Sort by `relative_path`.
- See `references/transaction-receipt-patterns.md` and `references/batched-extraction-patterns.md`.

## Reference Files
- `references/patterns.md`: Regex patterns for dates, prices, IDs, codes.
- `references/invoice-patterns.md`: Invoice extraction patterns.
- `references/utility-bill-patterns.md`: Multi-line keyword extraction, template filling.
- `references/construction-patterns.md`: Line item extraction, aggregation logic.
- `references/transaction-receipt-patterns.md`: Fuel receipt filtering, multi-line amounts.
- `references/batched-extraction-patterns.md`: Nested traversal, duplicate detection, OCR normalization.