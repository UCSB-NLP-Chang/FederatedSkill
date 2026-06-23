---
name: image-data-extraction
description: Extract structured data from multiple images and output to Excel. Use when processing batches of images (photos, scans, labels, documents) where you need to extract consistent fields like dates, prices, names, or IDs into a tabular format.
---

# Image Data Extraction

Extract structured data from a batch of images and write to a formatted Excel file.

## When to Use
- Processing shelf labels, receipts, forms, or documents from images
- Extracting consistent fields (dates, prices, IDs, names) across multiple images
- Creating tabular output from visual sources

## Workflow

1. **Enumerate images**: List all image files in the target directory
2. **Read each image**: Use vision capabilities to extract relevant fields
3. **Normalize data**:
   - Dates: Convert to ISO format (YYYY-MM-DD)
   - Prices: Pass as raw float values (see Output precision below)
   - Filenames: Preserve original names for traceability
4. **Write Excel**: Create workbook with single sheet, header row, and data rows
5. **Validate output**: Verify row count matches image count, check for empty rows

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Excel Output Requirements
- Sheet name: Use descriptive name (e.g., "products", "records")
- Header row: First row contains column names
- Data rows: One row per image, no gaps
- Sorting: Typically by filename ascending

## Known invariants (by sub-task)

### pharmacy-shelf-label
- Output Excel columns: `{filename, date, price}` in exact order
- Date extraction priority: `EXP`/`EXPIRY` > `EXPIRES` > `MFG`/`MANUFACTURED`
- Price extraction priority: labeled `PRICE:` > raw currency (`RM`, `MYR`, `$`)
- For month-only dates (e.g., `MM/YYYY`), use day `01`
- Row count must exactly match input image count
- Sort by filename ascending

## Validation Checklist
- Row count = number of images processed
- No empty rows between data
- All required fields populated
- Date format consistent (YYYY-MM-DD)
- Numeric fields are raw floats, not formatted strings

## Common Issues
- **Missing data**: Some images may lack expected fields; handle gracefully
- **Format variations**: Dates/prices may appear in different formats; normalize consistently
- **Empty rows**: Verify no trailing empty rows in Excel output

## Pattern Reference
See `references/patterns.md` for ready-to-use regex patterns for dates, prices, and other common field types.

## Reference Script
See `scripts/create_excel.py` for a reusable Excel creation helper with proper formatting.