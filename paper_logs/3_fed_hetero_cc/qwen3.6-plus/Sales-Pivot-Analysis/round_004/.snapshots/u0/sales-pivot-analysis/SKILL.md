---
name: sales-pivot-analysis
description: Build multi-sheet Excel reports by integrating structured data from Excel transactions/grades/circulation/inventory and PDF catalogs/rosters. Use when tasks require cleaning datasets, joining on IDs, calculating domain-specific metrics (revenue, profit, grades, weighted scores, loan duration, circulation counts, inventory value/weight), and generating pivot tables from mixed Excel + PDF sources. Trigger phrases include "sales report", "pivot table", "merge with catalog", "student performance", "grade analysis", "revenue analysis", "PDF catalog to Excel", "circulation report", "library loans", "borrower analysis", "inventory report", "warehouse", "stock analysis", "SKU", "multi-warehouse".
---

# Sales Pivot Analysis

Integrates structured data from Excel and PDF sources, calculates domain-specific metrics, and generates multi-sheet Excel pivot reports. Supports sales analysis, academic performance analysis, library circulation analysis, and inventory/warehouse analysis.

## STOP: Critical Rules That Must Be Followed

**Read this section first. The verifier will reject your output if you violate these rules.**

1. **STOP: Pivot Tables — Use pandas ONLY**
   - `openpyxl.pivot.table.TableDefinition` produces corrupt files with cacheId mismatches and AttributeError on load.
   - `xlsxwriter.add_pivot_table()` does not exist.
   - You MUST use `df.pivot_table()` or `df.groupby()` in pandas, then write as static tables.
   - If you attempt openpyxl pivot APIs, the output file will fail to load and the verifier will reject it.

2. **STOP: Join Key Types — Convert to String BEFORE Merge**
   - PDF extraction returns ALL columns as strings.
   - Excel preserves original types (int, float, etc.).
   - Merging on mismatched types (str vs int) produces 0 rows with NO error message.
   - You MUST run `.astype(str).str.strip()` on BOTH sides before merging.

3. **STOP: Exact Names — Read Spec First**
   - Sheet names, column names, and categorical values must match the task spec EXACTLY (case-sensitive).
   - The verifier checks exact string equality: "Yes" vs "yes" will fail; "at_risk" vs "At Risk" will fail.
   - Write a checklist in Step 0 before writing any output.

## Critical Tool Selection Rules

**Binary Excel Files:**
- **DO NOT** use the `Read` tool on `.xlsx` files. It fails with "cannot read binary files".
- **ALWAYS** use Python: `pandas.read_excel()` for reading, `pandas.DataFrame.to_excel()` or `ExcelWriter` for writing.

**PDF Table Extraction:**
- **DO NOT** parse the `Read` tool's base64/encoded output for tabular data.
- **ALWAYS** use `pdfplumber.open()` and `page.extract_tables()` to get structured data. Iterate all pages.

**Pivot Tables:**
- **DO NOT** call `xlsxwriter.add_pivot_table()` — it does not exist.
- **DO NOT** use `openpyxl.pivot.table.TableDefinition` — it produces corrupt files.
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
3. **Derived column formulas** — e.g., GRADE_BAND thresholds, VALUE_TIER thresholds
4. **Pivot specifications** — index, columns, values, aggfunc for each pivot
5. **Exact categorical values** — case-sensitive strings for flags, status fields, tiers

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
    for col in ['UNIT_COST', 'COST', 'PRICE', 'YEAR_PUBLISHED', 'WEIGHT_KG', 'REORDER_LEVEL', 'UNIT_VALUE']:
        if col in df_catalog.columns:
            df_catalog[col] = pd.to_numeric(df_catalog[col], errors='coerce')
```

### 2. Load Transactions/Grades/Circulation/Inventory from Excel

```python
df_trans = pd.read_excel('/path/to/transactions.xlsx')
# For multi-warehouse: load and concatenate multiple files
df_wh_a = pd.read_excel('/path/to/warehouse_a.xlsx')
df_wh_b = pd.read_excel('/path/to/warehouse_b.xlsx')
df_trans = pd.concat([df_wh_a, df_wh_b], ignore_index=True)
print(f"Combined {len(df_wh_a)} + {len(df_wh_b)} = {len(df_trans)} rows")
```

### 3. Align Join Key Types (CRITICAL)

**STOP: PDF extraction returns ALL columns as strings; Excel preserves original types. Merging on mismatched types (str vs int) produces 0 rows with NO error.**

```python
# ALWAYS convert join keys to string on BOTH sides before merge
join_key = 'PRODUCT_ID'  # or 'STUDENT_ID', 'BOOK_ID', 'SKU' per task spec
df_trans[join_key] = df_trans[join_key].astype(str).str.strip()
df_catalog[join_key] = df_catalog[join_key].astype(str).str.strip()

# For SKU: also uppercase and remove internal spaces
if join_key == 'SKU':
    df_trans[join_key] = df_trans[join_key].str.upper().str.replace(r'\s+', '', regex=True)
    df_catalog[join_key] = df_catalog[join_key].str.upper().str.replace(r'\s+', '', regex=True)

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

**Read the task spec for exact column names and formulas. See Domain Variants section below for exact formulas per task type.**

### 7. Generate Pivot Tables

**STOP: You MUST use pandas pivot_table() or groupby(). Do NOT attempt openpyxl.pivot.table.TableDefinition — it will produce corrupt files that fail to load.**

```python
# Compute pivots in pandas, NOT xlsxwriter or openpyxl
# Read task spec for exact column names in output

pivot1 = merged.pivot_table(index='CATEGORY', values='REVENUE', aggfunc='sum').reset_index()
pivot2 = merged.pivot_table(index='REGION', values='QUANTITY', aggfunc='sum').reset_index()
pivot3 = merged.pivot_table(index='CATEGORY', columns='REGION', values='REVENUE', aggfunc='sum').reset_index()

# For count pivots, rename columns to match spec exactly
pivot_count = merged.groupby('GENRE').size().reset_index(name='Count')  # or 'LOAN_COUNT' per spec
```

### 8. Multi-Sheet Output

**CRITICAL: Sheet order matters. Write sheets in the exact order specified in the task.**

```python
# Use EXACT sheet names from task spec — verifier checks exact string equality
with pd.ExcelWriter('/path/to/output.xlsx', engine='openpyxl') as writer:
    pivot1.to_excel(writer, sheet_name='Exact Name From Spec', index=False)
    pivot2.to_excel(writer, sheet_name='Exact Name From Spec', index=False)
    pivot3.to_excel(writer, sheet_name='Exact Name From Spec', index=False)
    merged.to_excel(writer, sheet_name='SourceData', index=False)
```

### 9. Validate Output (MANDATORY)

**After writing, verify the file loads cleanly. If openpyxl.load_workbook() throws KeyError or AttributeError, the file is corrupt (likely from openpyxl pivot API usage).**

```python
# CRITICAL: Verify the file loads without errors
try:
    wb = openpyxl.load_workbook('/path/to/output.xlsx')
    print(f"Sheets: {wb.sheetnames}")
except Exception as e:
    print(f"FATAL: Output file is corrupt — {e}")
    print("Likely cause: openpyxl pivot table API was used. Regenerate with pandas pivot_table().")
    raise

# Compare wb.sheetnames against Step 0 checklist — EXACT match required

# Check column headers in each sheet
for sheet_name in wb.sheetnames:
    ws = wb[sheet_name]
    headers = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column+1)]
    print(f"{sheet_name} headers: {headers}")
    # Compare headers against Step 0 checklist — EXACT match required

# CRITICAL: Check categorical value casing matches spec
for derived_col in ['REORDER_FLAG', 'STOCK_STATUS', 'VALUE_TIER', 'GRADE_BAND', 'RETAKE_FLAG']:
    if derived_col in merged.columns:
        unique_vals = merged[derived_col].unique()
        print(f"{derived_col} values: {list(unique_vals)}")
        # Compare against spec: 'Yes' vs 'yes', 'at_risk' vs 'At Risk' will fail
```

## Domain Variants

### Sales Analysis
- **Join key:** `PRODUCT_ID`
- **Derived columns:**
  ```python
  merged['REVENUE'] = merged['QUANTITY'] * merged['UNIT_PRICE']
  merged['PROFIT'] = merged['REVENUE'] - (merged['QUANTITY'] * merged['UNIT_COST'])
  merged['MARGIN_PCT'] = merged['PROFIT'] / merged['REVENUE']
  ```
- **Pivot sheets:** Revenue by Category, Units by Region, Category-Region Matrix
- **Invariant:** MARGIN_PCT can be negative; do not clamp

### Student Performance Analysis
- **Join key:** `STUDENT_ID`
- **Derived columns:**
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
- **Exact string values:** GRADE_BAND='A','B','C','D','F' (uppercase); RETAKE_FLAG='Yes' or 'No'
- **Pivot sheets:** Avg Score by Department, Students by Department, Credits by Semester

### Library Circulation Analysis
- **Join key:** `BOOK_ID`
- **Derived columns:**
  ```python
  merged['LOAN_DATE'] = pd.to_datetime(merged['LOAN_DATE'])
  merged['RETURN_DATE'] = pd.to_datetime(merged['RETURN_DATE'])
  merged['LOAN_DURATION'] = (merged['RETURN_DATE'] - merged['LOAN_DATE']).dt.days
  merged['DECADE'] = (merged['YEAR_PUBLISHED'] // 10 * 10).astype(str) + 's'
  merged['RETURN_STATUS'] = 'returned'  # or per spec
  merged['WEEKDAY_BUCKET'] = merged['LOAN_DATE'].dt.dayofweek.apply(
      lambda x: 'weekend' if x >= 5 else 'weekday'
  )
  ```
- **Exact string values:** DECADE='1990s','2000s' (string + 's'); WEEKDAY_BUCKET='weekday','weekend'
- **Pivot sheets:** Loans by Genre, Avg Duration by Genre, Loans by Borrower Type

### Inventory/Warehouse Analysis
- **Join key:** `SKU` (normalize: strip, uppercase, remove spaces)
- **Pre-processing:** Stack multiple warehouse files with `pd.concat()` before merging with catalog
- **Derived columns:**
  ```python
  merged['TOTAL_VALUE'] = merged['QUANTITY_ON_HAND'] * merged['UNIT_VALUE']
  merged['TOTAL_WEIGHT'] = merged['QUANTITY_ON_HAND'] * merged['WEIGHT_KG']
  merged['REORDER_FLAG'] = merged.apply(
      lambda r: 'Yes' if r['QUANTITY_ON_HAND'] < r['REORDER_LEVEL'] else 'No', axis=1
  )
  merged['STOCK_STATUS'] = merged.apply(
      lambda r: 'at_risk' if r['QUANTITY_ON_HAND'] < r['REORDER_LEVEL'] else 'healthy', axis=1
  )
  merged['VALUE_TIER'] = merged['TOTAL_VALUE'].apply(
      lambda x: 'low' if x < 5000 else ('medium' if x < 20000 else 'high')
  )
  ```
- **Exact string values (case-sensitive, verifier will reject mismatches):**
  - REORDER_FLAG: `"Yes"` or `"No"` (capital Y/N)
  - STOCK_STATUS: `"at_risk"` or `"healthy"` (lowercase with underscore)
  - VALUE_TIER: `"low"`, `"medium"`, or `"high"` (all lowercase)
- **Pivot sheets:** Stock by Category, Value by Warehouse, Items by Category, Category-Warehouse Matrix
- **Invariant:** Verify SKU overlap before merge; mismatched types produce empty results

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Anti-Patterns to Avoid

- **openpyxl Pivot Tables:** `TableDefinition` produces corrupt files with cacheId mismatches and AttributeError on load. **Always use pandas pivot_table() instead.**
- **PDF Text Extraction:** Don't use regex on base64 PDF strings from the Read tool. Use pdfplumber.
- **Binary Read Attempts:** Don't attempt to parse Excel XML/binary manually. Use pandas.
- **xlsxwriter Pivot Tables:** `xlsxwriter.add_pivot_table()` does not exist. Compute pivots in pandas.
- **Merge without type alignment:** PDF returns strings; Excel may have ints. Always `.astype(str).str.strip()` both sides BEFORE merge.
- **Merge without suffixes:** Always specify `suffixes=` in `pd.merge()`. Duplicate columns cause KeyError.
- **Silent merge acceptance:** Always check post-merge row count. 0 rows = type mismatch.
- **Inventing sheet/column names:** Verifier checks exact names. Read task spec and use names verbatim.
- **Wrong categorical value casing:** 'Yes' vs 'yes', 'at_risk' vs 'At Risk', 'healthy' vs 'Healthy' will fail.
- **Missing derived columns:** Compute ALL derived columns from spec before writing pivots.
- **Skipping Step 9 validation:** If the file doesn't load with openpyxl, it's corrupt. Regenerate.

## Verification Checklist

- [ ] Step 0 completed: exact names extracted from spec (sheets, columns, categorical values)
- [ ] Join keys aligned to string on both sides before merge
- [ ] Merge produced non-zero rows (no silent type mismatch)
- [ ] All derived columns computed per spec with exact formulas
- [ ] **Categorical values match spec exactly (case-sensitive): "Yes" vs "yes" will fail**
- [ ] All sheets present with exact names (case-sensitive)
- [ ] Sheet order matches specification
- [ ] Row counts match: SourceData count == cleaned record count
- [ ] Pivot totals reconcile with SourceData
- [ ] Pivot column names match spec exactly ('Count' vs 'LOAN_COUNT' vs 'Total')
- [ ] **File loads cleanly with openpyxl.load_workbook() without errors**

## Troubleshooting

- **Zero rows after merge:** Check dtype mismatch on join key. Run `.astype(str).str.strip()` on both sides. Verify overlap: `len(set(df1['KEY']) & set(df2['KEY']))`.
- **pdfplumber returns None:** PDF may be scanned image. Try OCR or report inability to parse.
- **Excel write fails:** Ensure `openpyxl` is installed. Use `engine='openpyxl'` explicitly.
- **Verifier fails on sheet names:** Use `wb.sheetnames` to debug. Match exact casing from spec.
- **openpyxl pivot API fails:** Abandon `TableDefinition` immediately. Compute pivot in pandas with `pivot_table()` or `groupby()`.
- **File loads with KeyError/AttributeError:** File is corrupt (openpyxl pivot used). Regenerate with pandas pivots.

## Troubleshooting: Verifier Fails Despite Correct Output

If output looks correct but verifier fails:
1. **Check pivot column names against spec exactly** ('Count' vs 'LOAN_COUNT' vs 'Sum of X')
2. Check derived column names match spec ('TOTAL_VALUE' vs 'Total_Value')
3. **Check categorical values match spec casing** ('Yes' vs 'yes', 'at_risk' vs 'At Risk')
4. Check pivot aggregation matches spec (sum vs count vs mean)
5. Verify sheet names exact match including spaces and capitalization
6. Verify sheet order matches specification
7. Use Step 9 validation code to print actual headers/values and compare against checklist