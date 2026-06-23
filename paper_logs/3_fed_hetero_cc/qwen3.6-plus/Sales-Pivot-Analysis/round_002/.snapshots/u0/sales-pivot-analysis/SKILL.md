---
name: sales-pivot-analysis
description: Build multi-sheet Excel reports by integrating structured data from Excel and PDF sources. Use when tasks require cleaning datasets, joining on key fields, calculating derived metrics, and generating pivot tables. Covers sales analysis (revenue, profit, margin) and student performance (grade bands, weighted scores, retake flags). Trigger phrases include "sales report", "pivot table", "merge with catalog", "revenue analysis", "student performance", "grade analysis", "department pivot".
---

# Sales Pivot Analysis

## Critical Tool Selection Rules

**Binary Excel Files:**
- **DO NOT** use the `Read` tool on `.xlsx` files. It fails with "cannot read binary files".
- **ALWAYS** use Python: `pandas.read_excel()` for reading, `pandas.DataFrame.to_excel()` or `ExcelWriter` for writing.

**PDF Table Extraction:**
- **DO NOT** parse the `Read` tool's base64/encoded output for tabular data.
- **ALWAYS** use `pdfplumber.open()` and `page.extract_tables()` to get structured data. Iterate all pages.

**Pivot Tables:**
- **DO NOT** call `xlsxwriter.add_pivot_table()` — it does not exist.
- **ALWAYS** compute pivots in pandas with `df.pivot_table()` or `df.groupby()`, then write as static tables.

## Required Libraries

```python
import pandas as pd
import numpy as np
import pdfplumber
import openpyxl
```

## Step 0: Read Task Spec for Exact Names (MANDATORY)

Before writing any output, extract from the task specification:
1. **Exact sheet names** — list every required sheet name, case-sensitive
2. **Exact column names** for each sheet, including SourceData derived columns
3. **Derived column formulas** — e.g., GRADE_BAND thresholds, WEIGHTED_SCORE definition
4. **Pivot specifications** — index, columns, values, aggfunc for each pivot

Write these as a checklist. Every output name must match the spec exactly — the verifier checks exact string equality.

## Standard Workflow

### 1. Extract Catalog/Roster from PDF

```python
with pdfplumber.open('/path/to/catalog.pdf') as pdf:
    rows = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            rows.extend(table)
    df_catalog = pd.DataFrame(rows[1:], columns=rows[0])
    # PDF returns all strings — clean and convert
    for col in df_catalog.select_dtypes(include='object'):
        df_catalog[col] = df_catalog[col].str.strip()
    for col in ['UNIT_COST', 'COST', 'PRICE']:
        if col in df_catalog.columns:
            df_catalog[col] = pd.to_numeric(df_catalog[col], errors='coerce')
```

### 2. Load Transactions/Grades from Excel

```python
df_trans = pd.read_excel('/path/to/transactions.xlsx')
```

### 3. Align Join Key Types (CRITICAL)

**PDF extraction returns ALL columns as strings; Excel preserves original types. Merging on mismatched types (str vs int) produces 0 rows with NO error.**

```python
# ALWAYS convert join keys to string on BOTH sides before merge
join_key = 'PRODUCT_ID'  # or 'STUDENT_ID' per task spec
df_trans[join_key] = df_trans[join_key].astype(str).str.strip()
df_catalog[join_key] = df_catalog[join_key].astype(str).str.strip()

# Verify overlap before merging
overlap = set(df_trans[join_key]) & set(df_catalog[join_key])
print(f"ID overlap: {len(overlap)} values")
if len(overlap) == 0:
    print("WARNING: No overlap — check for whitespace, leading zeros, or type issues")
```

### 4. Data Validation & Cleaning

Check in order; drop or flag rows that fail:
- Missing join key (null check)
- Unknown join key (existence in catalog/roster)
- Non-positive quantities/credits (must be > 0)
- Missing critical numeric fields
- Duplicate record IDs (drop duplicates)
- Standardize casing for categorical fields (e.g., SEMESTER to Title Case)

### 5. Merge with Validation

```python
# CRITICAL: Always specify suffixes to prevent duplicate column names
merged = df_trans.merge(df_catalog, on=join_key, how='left', suffixes=('_trans', '_cat'))

# IMMEDIATELY validate merge — silent 0-row merges are the #1 failure mode
print(f"Pre-merge: {len(df_trans)} rows, Post-merge: {len(merged)} rows")
if len(merged) == 0:
    raise ValueError("Merge produced 0 rows — join key type mismatch or no overlapping values")
if len(merged) < len(df_trans) * 0.5:
    print(f"WARNING: Merge lost >50% of rows. Check join key alignment.")
```

### 6. Calculate Derived Columns

**Read the task spec for exact column names and formulas.** Common patterns:

**Sales:**
```python
merged['REVENUE'] = merged['QUANTITY'] * merged['UNIT_PRICE']
merged['PROFIT'] = merged['REVENUE'] - (merged['QUANTITY'] * merged['UNIT_COST'])
merged['MARGIN_PCT'] = merged['PROFIT'] / merged['REVENUE']
```

**Student Performance:**
```python
def assign_grade_band(score):
    if score >= 90: return 'A'
    elif score >= 80: return 'B'
    elif score >= 70: return 'C'
    elif score >= 60: return 'D'
    else: return 'F'
merged['GRADE_BAND'] = merged['SCORE'].apply(assign_grade_band)
merged['WEIGHTED_SCORE'] = merged['SCORE'] * merged['CREDITS']
merged['RETAKE_FLAG'] = merged['SCORE'].apply(lambda x: 'Yes' if x < 70 else 'No')
```

### 7. Generate Pivot Tables

**Read the task spec for exact pivot index/columns/values/aggfunc.**

```python
pivot1 = merged.pivot_table(index='CATEGORY', values='REVENUE', aggfunc='sum').reset_index()
pivot2 = merged.pivot_table(index='REGION', values='QUANTITY', aggfunc='sum').reset_index()
pivot3 = merged.pivot_table(index='CATEGORY', columns='REGION', values='REVENUE', aggfunc='sum').reset_index()
```

### 8. Multi-Sheet Output

```python
# Use EXACT sheet names from task spec — verifier checks exact string equality
with pd.ExcelWriter('/path/to/output.xlsx', engine='openpyxl') as writer:
    pivot1.to_excel(writer, sheet_name='Exact Name From Spec', index=False)
    pivot2.to_excel(writer, sheet_name='Exact Name From Spec', index=False)
    pivot3.to_excel(writer, sheet_name='Exact Name From Spec', index=False)
    merged.to_excel(writer, sheet_name='SourceData', index=False)
```

### 9. Validate Output

After writing, load and verify:
```python
wb = openpyxl.load_workbook('/path/to/output.xlsx')
print(f"Sheets: {wb.sheetnames}")
# Check: sheet names match spec exactly, row count correct, no nulls in join columns
```

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Anti-Patterns to Avoid

- **PDF Text Extraction:** Don't use regex on base64 PDF strings from the Read tool. Use pdfplumber.
- **Binary Read Attempts:** Don't attempt to parse Excel XML/binary manually. Use pandas.
- **xlsxwriter Pivot Tables:** `xlsxwriter` does not support `add_pivot_table()`. Compute pivots in pandas.
- **Merge without type alignment:** PDF returns strings; Excel may have ints. Always `.astype(str).str.strip()` both sides BEFORE merge. Mismatched types produce 0 rows silently.
- **Merge without suffixes:** Always specify `suffixes=` in `pd.merge()`. Duplicate columns cause KeyError.
- **Silent merge acceptance:** Always check post-merge row count. 0 rows = type mismatch.
- **Inventing sheet/column names:** Verifier checks exact names. Read task spec and use names verbatim.
- **Missing derived columns:** Compute ALL derived columns from spec before writing pivots.

## Verification Checklist

- [ ] Step 0 completed: exact names extracted from spec
- [ ] Join keys aligned to string on both sides before merge
- [ ] Merge produced non-zero rows (no silent type mismatch)
- [ ] All derived columns computed per spec
- [ ] All sheets present with exact names (case-sensitive)
- [ ] Row counts match: SourceData count == cleaned record count
- [ ] Pivot totals reconcile with SourceData

## Known invariants (by sub-task)

### sales-pivot-analysis
- Join key: PRODUCT_ID; metrics: REVENUE=QTY×PRICE, PROFIT=REVENUE−(QTY×COST), MARGIN_PCT=PROFIT/REVENUE
- Pivots: Revenue by Category, Units by Region, Category-Region Matrix
- MARGIN_PCT can be negative; do not clamp

### student-performance-pivot
- Join key: STUDENT_ID; derived: GRADE_BAND (A≥90/B≥80/C≥70/D≥60/F<60), WEIGHTED_SCORE=SCORE×CREDITS, RETAKE_FLAG (Yes if SCORE<70)
- Pivots: Avg Score by Department, Students by Department, Credits by Semester, Dept-Semester Matrix
- GRADE_BAND distribution must sum to total rows; no null DEPARTMENT after merge

## Troubleshooting

- **Zero rows after merge:** Check dtype mismatch on join key. Run `.astype(str).str.strip()` on both sides. Verify overlap: `len(set(df1['KEY']) & set(df2['KEY']))`.
- **pdfplumber returns None:** PDF may be scanned image. Try OCR or report inability to parse.
- **Excel write fails:** Ensure `openpyxl` is installed. Use `engine='openpyxl'` explicitly.
- **Verifier fails on sheet names:** Use `wb.sheetnames` to debug. Match exact casing from spec.
