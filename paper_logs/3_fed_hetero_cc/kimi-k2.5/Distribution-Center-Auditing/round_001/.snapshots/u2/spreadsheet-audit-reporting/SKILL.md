---
name: spreadsheet-audit-reporting
description: Use when tasked with reading tabular data from Excel or CSV, computing derived metrics (variances, flags, error counts), and producing a multi-sheet audit workbook alongside an optional executive Word brief. Covers openpyxl and python-docx workflows for data audits, exception reports, and compliance reviews.
---

# Spreadsheet Audit & Report Generation

Generate multi-sheet Excel audit reports with computed columns, summary aggregations, and optional Word document companions.

## When to Use

- Tasks requiring Excel workbooks with multiple sheets (raw data, formatted/processed data, summaries)
- Data quality audits or exception detection workflows
- Reports needing both detailed Excel data and narrative Word summaries
- Any task involving computed columns derived from business logic

## Workflow

1. **Install dependencies**: `pip install openpyxl python-docx pandas`
2. **Inspect source data**: Load the source file, print sheet names, headers, and sample rows to confirm column names.
3. **Read source data** with pandas: `pd.read_excel()` or `pd.read_csv()`
4. **Compute derived columns** using vectorized operations or apply functions
5. **Create summary aggregations** with `groupby()` and filtering (exclude zero-error groups)
6. **Build multi-sheet workbook** using openpyxl directly for precise control
7. **Generate Word companion** (optional) using python-docx for narrative summaries
8. **Verify outputs** by reading back and checking cell values and types

## Key Patterns

### Multi-Sheet Excel Workbook

```python
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

wb = Workbook()
# Rename default sheet - CRITICAL: avoid leaving empty 'Sheet'
ws_raw = wb.active
ws_raw.title = "RawData"
# Add additional sheets
ws_formatted = wb.create_sheet("Formatted Data")
ws_summary = wb.create_sheet("Summary")
```

### Computed Columns with Conditional Logic

```python
df['Qty Variance'] = (df['Expected Qty'] != df['Received Qty']).astype(int)

df['ColdChainError'] = df.apply(
    lambda r: 1 if r['Storage Class'] in ['CHILLED', 'FROZEN'] and r['Temp Status'] != 'OK' else 0,
    axis=1
)

df['Total Errors'] = df['Qty Variance'] + df['ColdChainError']
```

### Error Summary String Construction

```python
def error_summary(row):
    errors = []
    if row['Qty Variance'] == 1:
        errors.append('Qty Variance')
    if row['ColdChainError'] == 1:
        errors.append('Cold Chain Error')
    return ', '.join(errors) if errors else 'None'  # Return string 'None', not None/NaN

df['Error Summary'] = df.apply(error_summary, axis=1)
```

### Summary Aggregation with Filtering

```python
summary_rows = []
for (key1, key2), group in df.groupby(['Item Code', 'Supplier']):
    total = group['Total Errors'].sum()
    if total > 0:  # Filter out clean records
        summary_rows.append({
            'Item Code': key1,
            'Supplier': key2,
            'Total Errors': total
        })

summary_df = pd.DataFrame(summary_rows).sort_values(['Item Code', 'Supplier'])

# Append grand total row
grand_total = pd.DataFrame([{
    'Item Code': 'Grand Total',
    'Supplier': '-',
    'Total Errors': summary_df['Total Errors'].sum()
}])
summary_df = pd.concat([summary_df, grand_total], ignore_index=True)
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

### Extra Default Sheet

`openpyxl.Workbook()` initializes with a default `'Sheet'`. Always rename or delete it immediately:

```python
wb = Workbook()
ws = wb.active
ws.title = "RawData"  # Rename immediately, never leave 'Sheet' in output
```

### Pandas NaN Display Confusion

Pandas may display string `'None'` as `NaN`. This is display-only; the Excel file is correct. Verify actual cell values with openpyxl:

```python
from openpyxl import load_workbook
wb = load_workbook('output.xlsx', data_only=True)
for row in wb['Formatted Data'].iter_rows(min_row=2, max_row=5):
    print([repr(cell.value) for cell in row])  # Use repr() to see actual type
```

## Common Computed Column Patterns

| Business Rule | Implementation |
|--------------|----------------|
| Quantity variance | `(df['Expected'] != df['Received']).astype(int)` |
| Cold chain breach | `df['Storage Class'].isin(['CHILLED','FROZEN']) & (df['Temp Status'] != 'OK')` |
| Error summary text | `', '.join([k for k,v in error_flags.items() if v])` or `"None"` |
| Priority ranking | `df.groupby('Item')['Errors'].transform('sum')` |

## Word Document Companion

Use python-docx for narrative summaries:

```python
from docx import Document
doc = Document()
doc.add_heading('Audit Report', level=1)
doc.add_paragraph('Summary text with key findings...')
doc.add_heading('High-Priority Items', level=2)
for item in priority_items:
    doc.add_paragraph(f"- {item}")
doc.save('audit_brief.docx')
```

Include: definitions of computed metrics, totals, high-priority items, and actionable recommendations.

## Validation Checklist

- [ ] Source headers match expected names.
- [ ] Output workbook contains exactly the required sheets (no default `'Sheet'`).
- [ ] `Formatted Data` row count matches `RawData`.
- [ ] `Summary` grand total equals sum of detail rows.
- [ ] Word brief contains all required sections (definitions, totals, top items, recommendations).

## Known Invariants (by Sub-task)

### harbor-receiving-exception-audit
- Output workbook must have exactly 3 sheets: `RawData`, `Formatted Data`, `Summary`
- Error Summary column contains literal string `"None"` for clean rows, not Python `None` or empty cell
- Grand Total row uses `'-'` as placeholder for secondary grouping key (e.g., Supplier column)
- Summary sheet excludes zero-error groups (filter before appending Grand Total)