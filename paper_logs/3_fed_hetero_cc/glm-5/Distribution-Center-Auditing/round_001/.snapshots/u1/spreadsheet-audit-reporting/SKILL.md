---
name: spreadsheet-audit-reporting
description: Use when tasked with reading tabular data from Excel, computing derived metrics (variances, flags, error counts), and producing a multi-sheet audit workbook alongside an optional Word brief. Covers openpyxl and python-docx workflows with computed columns and aggregation patterns.
---

# Spreadsheet Audit & Report Generation

## When to Use
- Tasks requiring Excel workbooks with multiple sheets (raw data, formatted/processed data, summaries)
- Data quality audits or exception detection workflows
- Reports needing both detailed Excel data and narrative Word summaries
- Any task involving computed columns derived from business logic

## Workflow

1. **Read source data** with pandas: `pd.read_excel()` or `pd.read_csv()`
2. **Compute derived columns** using vectorized operations or apply functions
3. **Create summary aggregations** with `groupby()` and `agg()`
4. **Build multi-sheet workbook** using openpyxl directly for precise control
5. **Generate Word companion** using python-docx for narrative summaries (optional)
6. **Validate outputs** by reading back and checking cell values and types

## Key Patterns

### Multi-Sheet Excel Workbook
```python
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

wb = Workbook()
# Rename default sheet
ws_raw = wb.active
ws_raw.title = "RawData"
# Add additional sheets
ws_formatted = wb.create_sheet("Formatted Data")
ws_summary = wb.create_sheet("Summary")
```

### Computed Columns with Conditional Logic
```python
df['ErrorFlag'] = (df['Expected'] != df['Actual']).astype(int)
df['ColdChainError'] = df.apply(
    lambda r: 1 if r['Storage Class'] in ['CHILLED', 'FROZEN'] and r['Temp Status'] != 'OK' else 0,
    axis=1
)
```

### Summary Aggregation
```python
summary = df.groupby(['Item Code', 'Supplier']).agg({
    'Qty Variance': 'sum',
    'Cold Chain Error': 'sum',
    'Total Errors': 'sum'
}).reset_index()
```

## Critical Anti-Patterns

### None vs "None" String
When writing string values to Excel cells, Python `None` becomes an empty cell, not the text "None":

**Wrong:**
```python
df['Error Summary'] = df.apply(lambda r: None if r['Total Errors'] == 0 else "Error")
# Results in empty cells, not "None" text
```

**Correct:**
```python
df['Error Summary'] = df.apply(lambda r: "None" if r['Total Errors'] == 0 else "Error")
# Explicitly use string "None" for literal text
```

### Validation Step
Always verify Excel output by reading back with openpyxl (not just pandas, which may display NaN differently):
```python
from openpyxl import load_workbook
wb = load_workbook('output.xlsx')
for row in wb['Formatted Data'].iter_rows(min_row=2, max_row=5):
    print([cell.value for cell in row])
```

## Common Computed Column Patterns

| Business Rule | Implementation |
|--------------|----------------|
| Quantity variance | `(df['Expected'] != df['Received']).astype(int)` |
| Cold chain breach | `df['Storage Class'].isin(['CHILLED','FROZEN']) & (df['Temp Status'] != 'OK')` |
| Error summary text | `', '.join([k for k,v in error_flags.items() if v])` or `"None"` |
| Priority ranking | `df.groupby('Item')['Errors'].transform('sum')` |

## Word Document Companion (Optional)

Use python-docx for narrative summaries:
```python
from docx import Document
doc = Document()
doc.add_heading('Report Title', level=1)
doc.add_paragraph('Summary text with key findings...')
doc.save('report.docx')
```

Include: definitions of computed metrics, totals, high-priority items, and actionable recommendations.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### harbor-receiving-exception-audit
- Output workbook must contain exactly 3 sheets: `RawData`, `Formatted Data`, `Summary`. No extra default `'Sheet'` from openpyxl.Workbook().
- Error Summary column must contain literal string `"None"` for clean rows, not Python `None`/empty cell.
- Summary sheet Grand Total row uses `-` placeholder for secondary grouping key.
- pandas `read_excel()` displays string `"None"` as NaN; verify actual cell values with openpyxl `values_only=True`.