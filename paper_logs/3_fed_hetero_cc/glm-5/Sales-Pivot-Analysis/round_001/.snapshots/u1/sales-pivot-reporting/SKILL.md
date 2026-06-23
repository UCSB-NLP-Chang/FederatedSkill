---
name: sales-pivot-reporting
description: Build multi-sheet Excel reports by integrating structured data from Excel transactions and PDF catalogs. Use when tasks require cleaning datasets, joining on product/catalog IDs, calculating business metrics (revenue, profit, margin), and generating pivot tables from mixed Excel + PDF sources. Trigger phrases include "sales report", "pivot table", "merge with catalog", "revenue analysis", "PDF catalog to Excel".
---

# Sales Pivot Reporting

## Critical Tool Selection Rules

**Binary Excel Files:**
- **DO NOT** use the `Read` tool on `.xlsx` files. It fails with "cannot read binary files".
- **ALWAYS** use Python: `pandas.read_excel()` for reading, `pandas.DataFrame.to_excel()` or `ExcelWriter` for writing.

**PDF Table Extraction:**
- **DO NOT** parse the `Read` tool's base64/encoded output for tabular data.
- **ALWAYS** use `pdfplumber.open()` and `page.extract_tables()` to get structured data.

**Pivot Tables:**
- **DO NOT** call `xlsxwriter.add_pivot_table()` — it does not exist.
- **ALWAYS** compute pivots in pandas with `df.pivot_table()` or `df.groupby()`, then write results as static tables.

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
    # Convert numeric columns from strings (PDF extraction returns all strings)
    for col in df_catalog.columns:
        df_catalog[col] = df_catalog[col].str.strip()
    df_catalog['UNIT_COST'] = pd.to_numeric(df_catalog['UNIT_COST'])
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
- Duplicate `TRANSACTION_ID` (drop duplicates, keep first)

### 4. Merge and Calculate
```python
# Left join transactions to catalog — ALWAYS specify suffixes to prevent duplicate columns
merged = df_trans.merge(df_catalog, on='PRODUCT_ID', how='left', suffixes=('_trans', '_cat'))

# Calculate business metrics
merged['REVENUE'] = merged['QUANTITY'] * merged['UNIT_PRICE']
merged['PROFIT'] = merged['REVENUE'] - (merged['QUANTITY'] * merged['UNIT_COST'])
merged['MARGIN_PCT'] = merged['PROFIT'] / merged['REVENUE']
```

### 5. Generate Pivot Tables
```python
# Revenue by Category
pivot1 = merged.pivot_table(index='CATEGORY', values='REVENUE', aggfunc='sum').reset_index()

# Units by Region
pivot2 = merged.pivot_table(index='REGION', values='QUANTITY', aggfunc='sum').reset_index()

# Category-Region Matrix (rows: Category, cols: Region)
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

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### B1: PDF Catalog + Excel Transaction Integration
- Read tool on binary .xlsx fails — always use pandas.read_excel()
- Parsing Read tool's base64 PDF output yields garbage — always use pdfplumber
- xlsxwriter.add_pivot_table() does not exist — compute pivots in pandas
- pd.merge() without suffixes creates duplicate columns → KeyError on drop_duplicates

## Anti-Patterns to Avoid
- **PDF Text Extraction:** Don't use regex on base64 PDF strings from the Read tool. Use pdfplumber.
- **Manual Pivot Loops:** Don't iterate rows to build pivot summaries. Use `pd.pivot_table()`.
- **Binary Read Attempts:** Don't attempt to parse Excel XML/binary manually. Use pandas abstractions.
- **Merge without suffixes:** Always specify `suffixes=('_a', '_b')` in `pd.merge()` to prevent duplicate column names.

## Verification Checklist
- [ ] Output file exists and opens without corruption
- [ ] All expected sheets present with correct names
- [ ] Row counts match: SourceData count == cleaned transaction count
- [ ] Pivot totals reconcile: Sum of 'Revenue by Category' equals sum of SourceData.REVENUE
- [ ] Calculated metrics in range: MARGIN_PCT between 0 and 1 (or expected bounds)
- [ ] No nulls in critical join columns after merge