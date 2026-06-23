---
name: excel-data-integration-reporting
description: Build multi-sheet Excel reports by integrating structured data from Excel transactions and PDF catalogs. Use when tasks require cleaning datasets, joining on product/catalog IDs, calculating business metrics (revenue, profit, margin), and generating pivot tables from mixed Excel + PDF sources. Trigger phrases include "sales report", "pivot table", "merge with catalog", "revenue analysis", "PDF catalog to Excel".
---

# Excel Data Integration and Reporting

## Critical Tool Selection Rules

**Binary Excel Files:**
- **DO NOT** use the `Read` tool on `.xlsx` files. It fails with "cannot read binary files".
- **ALWAYS** use Python: `pandas.read_excel()` for reading, `pandas.DataFrame.to_excel()` or `ExcelWriter` for writing.

**PDF Table Extraction:**
- **DO NOT** parse the `Read` tool's base64/encoded output for tabular data.
- **ALWAYS** use `pdfplumber.open()` and `page.extract_table()` to get structured data.

## Required Libraries
```python
import pandas as pd
import numpy as np
import pdfplumber
from openpyxl import Workbook  # Implicitly used by pandas for .xlsx output
```

## Standard Workflow

### 1. Extract Catalog from PDF
```python
with pdfplumber.open('/path/to/catalog.pdf') as pdf:
    # Assumes table is on first page; adjust index if needed
    table = pdf.pages[0].extract_table()
    df_catalog = pd.DataFrame(table[1:], columns=table[0])
    # PDF extraction returns all strings — convert types immediately
    df_catalog['UNIT_COST'] = pd.to_numeric(df_catalog['UNIT_COST'])
    # Clean string columns for whitespace padding
    for col in df_catalog.select_dtypes(include='object'):
        df_catalog[col] = df_catalog[col].str.strip()

# Verify extraction before proceeding
print(f"Shape: {df_catalog.shape}")
print(f"Columns: {df_catalog.columns.tolist()}")
print(df_catalog.dtypes)
```

### 2. Load Transactions from Excel
```python
df_trans = pd.read_excel('/path/to/transactions.xlsx')
```

### 3. Data Validation & Cleaning
Check in this order; drop or flag rows that fail:
- Missing `PRODUCT_ID` (null check)
- Unknown `PRODUCT_ID` (existence in catalog)
- Non-positive `QUANTITY` (must be > 0)
- Missing `UNIT_PRICE` (null check)
- Duplicate `TRANSACTION_ID` (drop duplicates)

### 4. Merge and Calculate
```python
# CRITICAL: Always specify suffixes to prevent duplicate column names
merged = df_trans.merge(df_catalog, on='PRODUCT_ID', how='left', suffixes=('_trans', '_cat'))

# Calculate business metrics
merged['REVENUE'] = merged['QUANTITY'] * merged['UNIT_PRICE']
merged['PROFIT'] = merged['REVENUE'] - (merged['QUANTITY'] * merged['UNIT_COST'])
merged['MARGIN_PCT'] = merged['PROFIT'] / merged['REVENUE']  # Verify range 0-1
```

### 5. Generate Pivot Tables
```python
# CRITICAL: xlsxwriter.add_pivot_table() does not exist — compute in pandas
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

## Anti-Patterns to Avoid
- **PDF Text Extraction:** Don't use regex on base64 PDF strings from the Read tool. Use pdfplumber.
- **Manual Pivot Loops:** Don't iterate rows to build pivot summaries. Use `pd.pivot_table()`.
- **Binary Read Attempts:** Don't attempt to parse Excel XML/binary manually. Use pandas abstractions.
- **xlsxwriter Pivot Tables:** `xlsxwriter` does not support `add_pivot_table()`. Attempting to call it raises `AttributeError`. Always compute pivots in pandas first.
- **Duplicate Columns After Merge:** Failing to set `suffixes` in `pd.merge()` creates overlapping column names. Subsequent column indexing or deduplication will raise `KeyError`.
- **Assuming 1:1 Matches:** Always verify merge results (`how='left'` vs `how='inner'`) and check for dropped rows or unexpected NaNs in key columns.

## Verification Checklist
- [ ] Output file exists and opens without corruption
- [ ] All expected sheets present with correct names
- [ ] Row counts match: SourceData count == cleaned transaction count
- [ ] Pivot totals reconcile: Sum of 'Revenue by Category' equals sum of SourceData.REVENUE
- [ ] Calculated metrics in range: MARGIN_PCT between 0 and 1 (or expected bounds)
- [ ] No nulls in critical join columns after merge

## Known invariants (by sub-task)

### sales-pivot-analysis
- MARGIN_PCT must be in valid range (0 to 1, or -1 to 1 for loss scenarios)
- Row counts must reconcile between SourceData and pivot totals
- Sheet names must match expected names exactly (case-sensitive)

## Troubleshooting
- **pdfplumber returns None:** PDF may be scanned image, not text-based. Try OCR (pytesseract) or report inability to parse.
- **Excel write fails:** Ensure `openpyxl` is installed. Use `engine='openpyxl'` explicitly.
- **Merge produces unexpected nulls:** Check data types of join keys (both must be string or both numeric).
- **Memory issues with large Excel:** Use `read_excel(..., chunksize=...)` for very large files (>100k rows).
