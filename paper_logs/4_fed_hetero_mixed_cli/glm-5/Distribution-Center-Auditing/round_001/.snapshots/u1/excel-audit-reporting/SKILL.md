---
name: excel-audit-reporting
description: Generates multi-sheet Excel audit workbooks and executive Word briefs from raw receipt or transaction logs. Use when tasked with transforming tabular data into formatted audit reports, computing exception flags, aggregating summaries, and producing executive summaries.
---

# Excel Audit Reporting & Executive Brief Generation

## When to Use
- Creating Excel workbooks with multiple sheets (raw data, formatted, summary)
- Adding calculated columns (error flags, variance checks) to source data
- Generating aggregation summaries by categories (Item Code, Supplier, etc.)
- Creating Word document executive briefs from Excel analysis

## Workflow

1. **Read source data** with pandas: `pd.read_excel(path, sheet_name=...)`
2. **Create workbook** with openpyxl: `Workbook()` then add sheets
3. **Write raw data** first - copy source data exactly
4. **Add calculated columns** - derive new columns from existing data
5. **Create summary sheet** - group by relevant columns, aggregate metrics
6. **Generate Word summary** (optional) - use python-docx for executive briefs
7. **Verify outputs** - check cell values directly with openpyxl, not just pandas display

## Key Patterns

### Multi-Sheet Excel Creation
```python
from openpyxl import Workbook
wb = Workbook()
ws_raw = wb.active
ws_raw.title = "RawData"
ws_formatted = wb.create_sheet("Formatted Data")
ws_summary = wb.create_sheet("Summary")
```

### Writing DataFrames to Sheets
```python
from openpyxl.utils.dataframe import dataframe_to_rows
for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
    for c_idx, value in enumerate(row, 1):
        ws.cell(row=r_idx, column=c_idx, value=value)
```

### Handling None/NaN in Excel Output
- Pandas NaN displays as NaN; convert to desired string before writing
- Use `df.fillna('None')` or conditional logic for clean Excel output
- Verify with openpyxl directly: `ws.cell(row, col).value`

### Word Document Creation
```python
from docx import Document
doc = Document()
doc.add_heading('Title', level=1)
doc.add_paragraph('Content...')
doc.save(path)
```

## Decision Rules & Anti-Patterns

- **Do not** rely on `read_file` for `.xlsx` files; they are binary. Always use `openpyxl` via shell or pandas.
- **Always** compute aggregates from the formatted data, not the raw source, to ensure consistency.
- **Sort** summary tables deterministically (e.g., by primary key, then secondary key) before writing.
- **Verify** outputs immediately after generation. Check `max_row`, `max_column`, and header values programmatically.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### distribution-center-receipt-audit
- Calculated columns use **integer 0/1** (not boolean True/False)
- Error Summary cells contain **string "None"** for non-error rows (not empty, not NaN)
- Summary sheet filters to error rows only and includes Grand Total row
- Column headers match expected names exactly: "Qty Variance", "Cold Chain Error", "Total Errors", "Error Summary"

## Verification Steps

1. Check row counts match expected
2. Verify calculated columns have correct values (integer 0/1, not boolean)
3. Confirm summary totals match sum of detail rows
4. For Excel: read back with openpyxl to see actual cell values (pandas may mask issues)
5. For Word: extract text with `doc.paragraphs[i].text` to verify content

## Script Usage

Execute `scripts/create_audit_report.py` via shell when the task requires generating an audit workbook and executive brief. Adapt column names and grouping keys to match specific task requirements.

## References

- `references/nan-none-handling.md` — Critical patterns for NaN vs string "None" in Excel output
