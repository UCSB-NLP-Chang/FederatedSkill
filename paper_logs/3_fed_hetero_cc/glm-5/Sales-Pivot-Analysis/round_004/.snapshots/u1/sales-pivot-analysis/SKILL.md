---
name: sales-pivot-analysis
description: Build multi-sheet Excel reports by integrating structured data from Excel transactions/grades/circulation/inventory and PDF catalogs/rosters. Use when tasks require cleaning datasets, joining on IDs, calculating domain-specific metrics (revenue, profit, grades, loan duration, circulation counts, inventory value), and generating pivot tables from mixed Excel + PDF sources. Trigger phrases include "sales report", "pivot table", "merge with catalog", "student performance", "grade analysis", "revenue analysis", "PDF catalog to Excel", "circulation report", "library loans", "borrower analysis", "inventory report", "warehouse consolidation", "stock analysis", "multi-warehouse".
---

# Sales Pivot Analysis

Integrates structured data from Excel and PDF sources, calculates domain-specific metrics, and generates multi-sheet Excel pivot reports. Supports sales analysis, academic performance analysis, library circulation analysis, and inventory/warehouse analysis.

## CRITICAL: STOP — Do NOT Use openpyxl Pivot Table APIs

**STOP: Before generating pivots, you MUST use pandas `df.pivot_table()` or `df.groupby()`.**

- `openpyxl.pivot.table.TableDefinition` produces cacheId mismatches, AttributeError, and corrupt files
- `xlsxwriter.add_pivot_table()` does not exist
- Both failures have occurred across multiple rounds (R2, R3)

## Critical Tool Selection Rules

**Binary Excel Files:**
- **DO NOT** use the `Read` tool on `.xlsx` files. It fails with "cannot read binary files".
- **ALWAYS** use Python: `pandas.read_excel()` for reading, `pandas.DataFrame.to_excel()` or `ExcelWriter` for writing.

**PDF Table Extraction:**
- **DO NOT** parse the `Read` tool's base64/encoded output for tabular data.
- **ALWAYS** use `pdfplumber.open()` and `page.extract_tables()` to get structured data. Iterate all pages.

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
3. **Derived column formulas** — e.g., GRADE_BAND thresholds, LOAN_DURATION calculation, VALUE_TIER thresholds
4. **Pivot specifications** — index, columns, values, aggfunc for each pivot
5. **Pivot value column names** — check if spec requires 'Count', 'Total', 'Sum of X', 'Average of X', etc.
6. **Exact categorical values** — case-sensitive strings for flags, status fields, tiers (e.g., "Yes" vs "yes", "at_risk" vs "At Risk")

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
    # Convert numeric columns from PDF strings
    for col in ['UNIT_COST', 'COST', 'PRICE', 'YEAR_PUBLISHED', 'WEIGHT_KG', 'REORDER_LEVEL', 'UNIT_VALUE']:
        if col in df_catalog.columns:
            df_catalog[col] = pd.to_numeric(df_catalog[col], errors='coerce')
```

### 2. Load Transactions/Grades/Circulation/Inventory from Excel

```python
# Single source
df_trans = pd.read_excel('/path/to/transactions.xlsx')

# Multiple sources (e.g., multiple warehouses) — stack before merging
df_wh_a = pd.read_excel('/path/to/warehouse_a.xlsx')
df_wh_b = pd.read_excel('/path/to/warehouse_b.xlsx')
df_trans = pd.concat([df_wh_a, df_wh_b], ignore_index=True)
print(f"Combined {len(df_wh_a)} + {len(df_wh_b)} = {len(df_trans)} rows")
```

### 3. Align Join Key Types (CRITICAL)

**STOP: Before merging, convert join keys to string on BOTH sides.**

PDF extraction returns ALL columns as strings; Excel preserves original types. Merging on mismatched types (str vs int) produces 0 rows with NO error.

```python
join_key = 'PRODUCT_ID'  # or 'STUDENT_ID', 'BOOK_ID', 'SKU' per task spec

# For SKU/ID columns: normalize formatting (trim, uppercase, remove internal spaces)
df_trans[join_key] = df_trans[join_key].astype(str).str.strip().str.upper().str.replace(r'\s+', '', regex=True)
df_catalog[join_key] = df_catalog[join_key].astype(str).str.strip().str.upper().str.replace(r'\s+', '', regex=True)

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
- Standardize casing for categorical fields
- **Date validation:** For date ranges (loans, rentals), verify end_date > start_date

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

**STOP: Use exact formulas from Step 0 checklist. Check categorical value casing.**

See **Domain Variants** section below for exact formulas per task type.

### 7. Generate Pivot Tables

**STOP: You MUST use pandas pivot_table() or groupby(). Do NOT use openpyxl or xlsxwriter pivot APIs.**

```python
# Compute pivots in pandas ONLY
pivot1 = merged.pivot_table(index='CATEGORY', values='QUANTITY', aggfunc='sum').reset_index()
pivot2 = merged.pivot_table(index='REGION', values='QUANTITY', aggfunc='sum').reset_index()

# For count pivots, column name varies by spec — check Step 0 checklist
pivot_count = merged.groupby('GENRE').size().reset_index(name='Count')  # or 'LOAN_COUNT' or 'Total' per spec
```

### 8. Multi-Sheet Output

```python
# Use EXACT sheet names from Step 0 checklist — verifier checks exact string equality
with pd.ExcelWriter('/path/to/output.xlsx', engine='openpyxl') as writer:
    pivot1.to_excel(writer, sheet_name='Exact Name From Spec', index=False)
    pivot2.to_excel(writer, sheet_name='Exact Name From Spec', index=False)
    merged.to_excel(writer, sheet_name='SourceData', index=False)
```

### 9. Validate Output (MANDATORY — Do NOT Skip)

**STOP: You MUST verify output matches spec before declaring success. Raise if mismatch.**

```python
wb = openpyxl.load_workbook('/path/to/output.xlsx')
actual_sheets = wb.sheetnames
print(f"Actual sheets: {actual_sheets}")

# MANDATORY: Compare against Step 0 checklist
expected_sheets = ['Sheet1', 'Sheet2', 'SourceData']  # from Step 0
for expected in expected_sheets:
    if expected not in actual_sheets:
        raise ValueError(f"MISSING SHEET: expected '{expected}', got {actual_sheets}")

# Check column headers in each sheet
for sheet_name in actual_sheets:
    df = pd.read_excel('/path/to/output.xlsx', sheet_name=sheet_name)
    print(f"{sheet_name} columns: {list(df.columns)}")
    # Compare against Step 0 checklist — exact match required

# Check categorical values match spec casing
if 'REORDER_FLAG' in df.columns:
    unique_vals = df['REORDER_FLAG'].unique()
    expected_vals = ['Yes', 'No']  # from Step 0 checklist
    for v in unique_vals:
        if v not in expected_vals:
            raise ValueError(f"WRONG CATEGORICAL VALUE in REORDER_FLAG: got '{v}', expected {expected_vals}")
```

## Domain Variants

### Sales Analysis
- **Join key:** `PRODUCT_ID`
- **Derived columns:**
  - `REVENUE = QUANTITY * UNIT_PRICE`
  - `PROFIT = REVENUE - (QUANTITY * UNIT_COST)`
  - `MARGIN_PCT = PROFIT / REVENUE`
- **Pivot sheets:** Revenue by Category, Units by Region, Category-Region Matrix
- **Invariant:** MARGIN_PCT can be negative (if costs exceed revenue); do not clamp to [0,1]

### Student Performance Analysis
- **Join key:** `STUDENT_ID`
- **Derived columns:**
  - `GRADE_BAND`: A (≥90), B (≥80), C (≥70), D (≥60), F (<60) — uppercase single letter
  - `WEIGHTED_SCORE = SCORE * CREDITS`
  - `RETAKE_FLAG`: 'Yes' or 'No' (exact casing)
- **Pivot sheets:** Avg Score by Department, Students by Department, Credits by Semester, Dept-Semester Matrix
- **Invariant:** GRADE_BAND distribution sums to total rows; no null DEPARTMENT after merge

### Library Circulation Analysis
- **Join key:** `BOOK_ID`
- **Derived columns:**
  ```python
  merged['LOAN_DATE'] = pd.to_datetime(merged['LOAN_DATE'])
  merged['RETURN_DATE'] = pd.to_datetime(merged['RETURN_DATE'])
  merged['LOAN_DURATION'] = (merged['RETURN_DATE'] - merged['LOAN_DATE']).dt.days
  merged['DECADE'] = (merged['YEAR_PUBLISHED'] // 10 * 10).astype(str) + 's'  # e.g., '1990s'
  merged['RETURN_STATUS'] = 'returned'  # check spec for exact value
  merged['WEEKDAY_BUCKET'] = merged['LOAN_DATE'].dt.weekday.apply(
      lambda x: 'weekend' if x >= 5 else 'weekday'
  )
  ```
- **Pivot sheets:** Loans by Genre, Avg Duration by Genre, Loans by Borrower Type, Genre-Borrower Matrix
- **Invariant:** LOAN_DURATION > 0; DECADE format is '1990s' with 's' suffix

### Inventory Analysis
- **Join key:** `SKU` (normalize: trim, uppercase, remove internal spaces)
- **Derived columns:**
  ```python
  merged['TOTAL_VALUE'] = merged['QUANTITY_ON_HAND'] * merged['UNIT_VALUE']
  merged['TOTAL_WEIGHT'] = merged['QUANTITY_ON_HAND'] * merged['WEIGHT_KG']

  # CRITICAL: Exact categorical values (case-sensitive)
  merged['REORDER_FLAG'] = merged.apply(
      lambda r: 'Yes' if r['QUANTITY_ON_HAND'] < r['REORDER_LEVEL'] else 'No', axis=1
  )
  merged['STOCK_STATUS'] = merged.apply(
      lambda r: 'at_risk' if r['QUANTITY_ON_HAND'] < r['REORDER_LEVEL'] else 'healthy', axis=1
  )
  # VALUE_TIER thresholds from task spec (check spec for exact values)
  merged['VALUE_TIER'] = merged['TOTAL_VALUE'].apply(
      lambda x: 'low' if x < 5000 else ('medium' if x < 20000 else 'high')
  )
  ```
- **Pivot sheets:** Stock by Category, Value by Warehouse, Items by Category, Category-Warehouse Matrix
- **Exact categorical values (case-sensitive):**
  - `REORDER_FLAG`: "Yes" or "No"
  - `STOCK_STATUS`: "at_risk" or "healthy" (lowercase with underscore)
  - `VALUE_TIER`: "low", "medium", or "high" (all lowercase)

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### sales-pivot-analysis
- Read tool on binary .xlsx fails — always use pandas.read_excel()
- Parsing Read tool's base64 PDF output yields garbage — always use pdfplumber
- xlsxwriter.add_pivot_table() does not exist — compute pivots in pandas
- openpyxl.pivot.table.TableDefinition fails with TypeError/cacheId errors — compute pivots in pandas
- pd.merge() without suffixes creates duplicate columns → KeyError
- MARGIN_PCT can be negative (if costs exceed revenue); do not clamp to [0,1]
- Sheet names must match task spec exactly (case-sensitive)

### student-performance-pivot
- STUDENT_ID type mismatch (PDF str vs Excel int) causes silent 0-row merge
- GRADE_BAND values: 'A', 'B', 'C', 'D', 'F' (uppercase, single letter)
- RETAKE_FLAG values: 'Yes' or 'No' (exact casing)
- Sheet names must match task spec exactly (case-sensitive)

### library-circulation-pivot
- BOOK_ID type mismatch (PDF str vs Excel int) causes silent 0-row merge
- Date parsing: use `pd.to_datetime()` before date arithmetic
- LOAN_DURATION must be integer days (use `.dt.days`)
- DECADE format: '1990s', '2000s', etc. (string with 's' suffix)
- RETURN_STATUS and WEEKDAY_BUCKET values must match spec exactly (case-sensitive)
- Pivot column names must match spec (e.g., 'Count' vs 'LOAN_COUNT' vs 'Average of LOAN_DURATION')

### inventory-multi-warehouse-pivot
- SKU normalization required: trim, uppercase, remove internal spaces
- Multi-source consolidation: use pd.concat() before joining with product master
- Pivot column names often include aggregation prefix: 'Sum of X', 'Count', etc.
- **CRITICAL categorical values (case-sensitive):**
  - `REORDER_FLAG`: "Yes" or "No" (capitalized)
  - `STOCK_STATUS`: "at_risk" or "healthy" (lowercase, underscore for at_risk)
  - `VALUE_TIER`: "low", "medium", or "high" (all lowercase)
- VALUE_TIER thresholds: check task spec (commonly 5000/20000)

## Anti-Patterns to Avoid

- **STOP: openpyxl Pivot Tables:** `TableDefinition` produces corrupt files. Always use pandas `pivot_table()`.
- **STOP: xlsxwriter Pivot Tables:** `add_pivot_table()` does not exist. Compute pivots in pandas.
- **PDF Text Extraction:** Don't use regex on base64 PDF strings from the Read tool. Use pdfplumber.
- **Binary Read Attempts:** Don't attempt to parse Excel XML/binary manually. Use pandas.
- **Merge without type alignment:** ALWAYS convert join keys to string on BOTH sides BEFORE merge.
- **Merge without suffixes:** Always specify `suffixes=('_a', '_b')` in `pd.merge()`.
- **Silent merge acceptance:** Always check post-merge row count. 0 rows = type mismatch.
- **Inventing sheet/column names:** Verifier checks exact names. Read task spec and use names verbatim.
- **Wrong categorical value casing:** "Yes" ≠ "yes", "at_risk" ≠ "At Risk". Check Step 0 checklist.
- **Missing derived columns:** Compute ALL derived columns from spec before writing pivots.
- **Skipping Step 9 validation:** MUST verify output matches spec before declaring success.

## Verification Checklist

- [ ] Step 0 completed: exact names extracted from spec (sheets, columns, pivot values, categorical values)
- [ ] Join keys aligned to string on both sides before merge
- [ ] Merge produced non-zero rows (no silent type mismatch)
- [ ] All derived columns computed per spec with exact formulas
- [ ] Categorical values match spec exactly (case-sensitive)
- [ ] All sheets present with exact names (case-sensitive)
- [ ] Row counts match: SourceData count == cleaned record count
- [ ] Pivot totals reconcile with SourceData
- [ ] Pivot column names match spec exactly (e.g., 'Count', 'Sum of X')
- [ ] **Step 9 validation completed: actual output compared against spec, raise if mismatch**

## Troubleshooting

- **Zero rows after merge:** Check dtype mismatch on join key. Run `.astype(str).str.strip()` on both sides. Verify overlap: `len(set(df1['KEY']) & set(df2['KEY']))`.
- **pdfplumber returns None:** PDF may be scanned image. Try OCR or report inability to parse.
- **Excel write fails:** Ensure `openpyxl` is installed. Use `engine='openpyxl'` explicitly.
- **Verifier fails on sheet names:** Use `wb.sheetnames` to debug. Match exact casing from spec.
- **openpyxl pivot API fails:** Abandon `TableDefinition` immediately. Compute pivot in pandas with `pivot_table()` or `crosstab()`, then write as static data.
- **Verifier fails on categorical values:** Check exact string casing. Common failures: "Yes" vs "yes", "at_risk" vs "At Risk", "healthy" vs "Healthy".
- **File loads with KeyError/AttributeError:** File is corrupt from openpyxl pivot API. Regenerate with pandas pivots.

## Troubleshooting: Verifier Fails Despite Correct Output

If output looks correct but verifier fails:
1. **Check pivot column names against spec exactly** (e.g., 'Sum of QUANTITY_ON_HAND' vs 'QUANTITY_ON_HAND')
2. Check derived column names match spec (e.g., 'TOTAL_VALUE' vs 'Total_Value')
3. Check categorical values match spec casing (e.g., 'healthy' vs 'Healthy', 'at_risk' vs 'At Risk')
4. Check if pivot aggregation matches spec (sum vs count vs mean)
5. Verify sheet names are exact match including spaces and capitalization
6. Verify sheet order matches specification
7. Use `wb.sheetnames` and `df.columns.tolist()` to debug actual vs expected names
8. Re-read task spec for any missed requirements
