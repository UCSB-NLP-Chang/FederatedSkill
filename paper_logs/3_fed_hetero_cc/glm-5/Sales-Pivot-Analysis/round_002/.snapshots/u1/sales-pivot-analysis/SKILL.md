---
name: sales-pivot-analysis
description: Build multi-sheet Excel reports by integrating structured data from Excel transactions/grades and PDF catalogs/rosters. Use when tasks require cleaning datasets, joining on IDs, calculating domain-specific metrics (revenue, profit, grades, weighted scores), and generating pivot tables from mixed Excel + PDF sources. Trigger phrases include "sales report", "pivot table", "merge with catalog", "student performance", "grade analysis", "revenue analysis", "PDF catalog to Excel".
---

# Sales Pivot Analysis

Integrates structured data from Excel and PDF sources, calculates domain-specific metrics, and generates multi-sheet Excel pivot reports. Supports both sales analysis (revenue, profit, margin) and academic performance analysis (grade bands, weighted scores, retake flags).

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

### 1. Extract Data from PDF
```python
with pdfplumber.open('/path/to/catalog.pdf') as pdf:
    rows = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            rows.extend(table)
    df_pdf = pd.DataFrame(rows[1:], columns=rows[0])
    # Clean string columns for whitespace
    for col in df_pdf.columns:
        if df_pdf[col].dtype == object:
            df_pdf[col] = df_pdf[col].str.strip()
```

### 2. Load Data from Excel
```python
df_excel = pd.read_excel('/path/to/transactions.xlsx')
```

### 3. CRITICAL: Align Join Key Types Before Merge
```python
# PDF extraction returns ALL columns as strings; Excel preserves original types
# Merge on mismatched types (str vs int) produces 0 rows with NO error
# ALWAYS convert join keys to the same type (string is safest)
df_excel['JOIN_KEY'] = df_excel['JOIN_KEY'].astype(str).str.strip()
df_pdf['JOIN_KEY'] = df_pdf['JOIN_KEY'].astype(str).str.strip()
```

### 4. Data Validation & Cleaning
Check in this order; drop or flag rows that fail:
- Missing join key (null check)
- Non-positive quantities/credits (must be > 0)
- Missing critical numeric fields
- Duplicate record IDs (drop duplicates, keep first)
- Standardize casing for categorical fields

### 5. Merge with Validation
```python
# ALWAYS specify suffixes to prevent duplicate columns
merged = df_excel.merge(df_pdf, on='JOIN_KEY', how='left', suffixes=('_excel', '_pdf'))

# IMMEDIATELY validate merge result — silent failures are common
print(f"Pre-merge: {len(df_excel)} rows, Post-merge: {len(merged)} rows")
if len(merged) == 0:
    raise ValueError("Merge produced 0 rows — check join key types or values")
if len(merged) < len(df_excel) * 0.5:
    print(f"WARNING: Merge lost >50% of rows. Check join key alignment.")
```

### 6. Calculate Domain-Specific Metrics
See **Domain Variants** section below for exact formulas per task type.

### 7. Generate Pivot Tables
```python
# Compute pivots in pandas, NOT xlsxwriter
pivot1 = merged.pivot_table(index='CATEGORY', values='METRIC', aggfunc='sum').reset_index()
pivot2 = merged.pivot_table(index='REGION', values='QUANTITY', aggfunc='sum').reset_index()
pivot3 = merged.pivot_table(index='CATEGORY', columns='REGION', values='METRIC', aggfunc='sum').reset_index()
```

### 8. Multi-Sheet Output
```python
with pd.ExcelWriter('/path/to/output.xlsx', engine='openpyxl') as writer:
    pivot1.to_excel(writer, sheet_name='Exact Sheet Name From Spec', index=False)
    merged.to_excel(writer, sheet_name='SourceData', index=False)
```

## Domain Variants

### Sales Analysis
- **Join key:** `PRODUCT_ID`
- **Derived columns:**
  - `REVENUE = QUANTITY * UNIT_PRICE`
  - `PROFIT = REVENUE - (QUANTITY * UNIT_COST)`
  - `MARGIN_PCT = PROFIT / REVENUE`
- **Pivot sheets:** Revenue by Category, Units by Region, Category-Region Matrix
- **Invariant:** MARGIN_PCT in valid range (0–1 or −1–1)

### Student Performance Analysis
- **Join key:** `STUDENT_ID`
- **Derived columns:**
  - `GRADE_BAND`: A (≥90), B (≥80), C (≥70), D (≥60), F (<60)
  - `WEIGHTED_SCORE = SCORE * CREDITS`
  - `RETAKE_FLAG = 'Yes' if SCORE < 70 else 'No'`
- **Pivot sheets:** Avg Score by Department, Students by Department, Credits by Semester, Dept-Semester Matrix
- **Invariant:** GRADE_BAND distribution sums to total rows; no null DEPARTMENT after merge

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### sales-pivot-analysis
- Read tool on binary .xlsx fails — always use pandas.read_excel()
- Parsing Read tool's base64 PDF output yields garbage — always use pdfplumber
- xlsxwriter.add_pivot_table() does not exist — compute pivots in pandas
- pd.merge() without suffixes creates duplicate columns → KeyError
- MARGIN_PCT can be negative (if costs exceed revenue); do not clamp to [0,1]
- Sheet names must match task spec exactly (case-sensitive)

### student-performance-pivot
- STUDENT_ID type mismatch (PDF str vs Excel int) causes silent 0-row merge
- GRADE_BAND values: 'A', 'B', 'C', 'D', 'F' (uppercase, single letter)
- RETAKE_FLAG values: 'Yes' or 'No' (exact casing)
- Sheet names must match task spec exactly (case-sensitive)

## Anti-Patterns to Avoid
- **PDF Text Extraction:** Don't use regex on base64 PDF strings from the Read tool. Use pdfplumber.
- **Manual Pivot Loops:** Don't iterate rows to build pivot summaries. Use `pd.pivot_table()`.
- **Binary Read Attempts:** Don't attempt to parse Excel XML/binary manually. Use pandas.
- **Merge without suffixes:** Always specify `suffixes=('_a', '_b')` in `pd.merge()`.
- **Merge without type alignment:** ALWAYS convert join keys to the same type before merging.
- **Silent merge acceptance:** Always check row count immediately after merge.
- **Hardcoded sheet names:** READ TASK SPEC for exact sheet names, column names, and derived column formulas BEFORE writing.
- **Assumed column names:** Verify column names match task spec exactly (no extra underscores, correct casing).

## Troubleshooting: Merge Produces Empty Results
If `len(merged) == 0` or much smaller than expected:
1. Check join key dtypes: `print(df1['KEY'].dtype, df2['KEY'].dtype)`
2. If different (e.g., `int64` vs `object`), convert both to string: `df1['KEY'] = df1['KEY'].astype(str)`
3. Check for whitespace: `df1['KEY'] = df1['KEY'].str.strip()`
4. Verify overlap: `print(len(set(df1['KEY']) & set(df2['KEY'])))`

## Verification Checklist
- [ ] Output file exists and opens without corruption
- [ ] All expected sheets present with correct names (case-sensitive match to spec)
- [ ] Row counts match: SourceData count == cleaned transaction count
- [ ] **Merge validation: Post-merge row count is non-zero and reasonable**
- [ ] Pivot totals reconcile: Sum of pivot values equals sum of SourceData metric column
- [ ] Calculated metrics in expected range
- [ ] No nulls in critical join columns after merge
- [ ] Derived columns present in SourceData with correct values
- [ ] Column names match spec exactly (no extra underscores, correct casing)
