---
name: sales-pivot-analysis
description: Integrate data from Excel transactions and PDF catalogs, calculate business metrics (revenue, profit, margin), and generate multi-sheet Excel pivot reports. Use when tasks require joining mixed-format source data, computing aggregations, or producing pivot-table summaries. Trigger phrases include "sales report", "pivot table", "merge with catalog", "revenue analysis", "PDF catalog to Excel", "profit margin report".
---

# Sales Pivot Analysis

## Critical Tool Selection Rules

**Binary Excel Files:**
- **DO NOT** use the `Read` tool on `.xlsx` files. It fails with "cannot read binary files".
- **ALWAYS** use Python: `pandas.read_excel()` for reading, `pandas.DataFrame.to_excel()` or `ExcelWriter` for writing.

**PDF Table Extraction:**
- **DO NOT** parse the `Read` tool's base64/encoded output for tabular data.
- **ALWAYS** use `pdfplumber.open()` and `page.extract_tables()` to get structured data.

## Required Libraries
```python
import pandas as pd
import numpy as np
import pdfplumber
```

## Standard Workflow

### 1. Extract Catalog from PDF
```python
with pdfplumber.open('/path/to/catalog.pdf') as pdf:
    rows = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            rows.extend(table)
    df_catalog = pd.DataFrame(rows[1:], columns=rows[0])
    # Convert numeric columns from strings
    for col in df_catalog.columns:
        df_catalog[col] = pd.to_numeric(df_catalog[col], errors='ignore')
    # Clean string columns
    for col in df_catalog.select_dtypes(include='object'):
        df_catalog[col] = df_catalog[col].str.strip()
```

### 2. Load Transactions from Excel
```python
df_trans = pd.read_excel('/path/to/transactions.xlsx')
```

### 3. Data Validation & Cleaning
Check in this order; drop or flag rows that fail:
- Missing `PRODUCT_ID` (null check)
- Non-positive `QUANTITY` (must be > 0)
- Missing `UNIT_PRICE` (null check)
- Duplicate `TRANSACTION_ID` (drop duplicates)

### 4. Merge and Calculate
```python
# Left join transactions to catalog — ALWAYS specify suffixes
merged = df_trans.merge(df_catalog, on='PRODUCT_ID', how='left', suffixes=('', '_cat'))

# Calculate business metrics
merged['REVENUE'] = merged['QUANTITY'] * merged['UNIT_PRICE']
merged['PROFIT'] = merged['REVENUE'] - (merged['QUANTITY'] * merged['UNIT_COST'])
merged['MARGIN_PCT'] = merged['PROFIT'] / merged['REVENUE']
```

### 5. Generate Pivot Tables
**DO NOT** use `xlsxwriter.add_pivot_table()` — it does not exist. Compute pivots in pandas:
```python
# Revenue by Category
pivot1 = merged.pivot_table(index='CATEGORY', values='REVENUE', aggfunc='sum').reset_index()

# Units by Region
pivot2 = merged.pivot_table(index='REGION', values='QUANTITY', aggfunc='sum').reset_index()

# Category-Region Matrix
pivot3 = merged.pivot_table(index='CATEGORY', columns='REGION', values='REVENUE', aggfunc='sum').reset_index()
```

### 6. Multi-Sheet Output
```python
with pd.ExcelWriter('/path/to/output.xlsx', engine='openpyxl') as writer:
    pivot1.to_excel(writer, sheet_name='Revenue by Category', index=False)
    pivot2.to_excel(writer, sheet_name='Units by Region', index=False)
    pivot3.to_excel(writer, sheet_name='Category Region Matrix', index=False)
    merged.to_excel(writer, sheet_name='SourceData', index=False)
```

### 7. Verify Output
Load the generated workbook and assert:
- All required sheets exist with exact names
- Row counts: SourceData count == cleaned transaction count
- Pivot totals reconcile: sum of 'Revenue by Category' == sum of SourceData.REVENUE
- MARGIN_PCT values in valid range

## Anti-Patterns to Avoid
- **`xlsxwriter.add_pivot_table()`**: Does not exist. Always compute pivots in pandas with `groupby()` or `pivot_table()`.
- **Missing merge suffixes**: `pd.merge()` without `suffixes` creates duplicate column names when both sides share columns. This breaks downstream `drop_duplicates()` and column indexing with `KeyError`.
- **PDF text extraction via Read tool**: Base64 output is not parseable for tables. Use pdfplumber.
- **Single-page PDF assumption**: Always iterate `pdf.pages` and `extract_tables()` per page. Tables may span multiple pages or there may be multiple tables per page.
- **Skipping type conversion**: pdfplumber returns all values as strings. Always convert numeric columns with `pd.to_numeric()`.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### B1: PDF Catalog + Excel Transaction Integration
- Read tool on binary .xlsx fails ("cannot read binary files") — use pandas only
- Parsing Read tool's base64 PDF output yields garbage tables — use pdfplumber only
- `xlsxwriter.add_pivot_table()` does not exist — compute pivots in pandas
- `pd.merge()` without suffixes creates duplicate columns → KeyError on drop_duplicates
- MARGIN_PCT can be negative (if costs exceed revenue); do not clamp to [0,1]

## Troubleshooting
- **pdfplumber returns None:** PDF page may have no table, or it may be a scanned image. Try OCR (pytesseract) or report inability to parse.
- **Excel write fails:** Ensure `openpyxl` is installed. Use `engine='openpyxl'` explicitly.
- **Merge produces unexpected nulls:** Check data types of join keys (both must be string or both numeric). Strip whitespace from string keys.
- **Memory issues with large Excel:** Use `read_excel(..., chunksize=...)` for very large files (>100k rows).
