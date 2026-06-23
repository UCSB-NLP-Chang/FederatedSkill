---
name: excel-data-integration
description: Build multi-sheet Excel reports by integrating structured data from Excel files and PDF documents. Handles mixed-format source data, type-safe joins, domain-specific derived columns, and pivot table generation. Use when tasks require joining Excel transactions/records with PDF catalogs/rosters, computing aggregations, or producing pivot-table summaries. Trigger phrases include "sales report", "student performance", "pivot table", "merge with catalog", "grade analysis", "PDF to Excel", "department matrix", "revenue analysis".
---

# Excel Data Integration

Integrates data from Excel files with PDF documents to generate multi-sheet reports with calculated metrics and pivot tables.

## Critical Pre-Merge Step: Type Alignment

**ALWAYS normalize join-key types before merging.** PDF extraction returns all values as strings, while Excel preserves original types (often integers). Without alignment, merges produce zero rows silently.

```python
# Force both to string for consistent joining
df_excel['JOIN_KEY'] = df_excel['JOIN_KEY'].astype(str).str.strip()
df_pdf['JOIN_KEY'] = df_pdf['JOIN_KEY'].astype(str).str.strip()

# Verify overlap before merging
overlap = set(df_excel['JOIN_KEY']).intersection(set(df_pdf['JOIN_KEY']))
print(f"Key overlap: {len(overlap)} records")
```

## Tool Selection Rules

**Binary Excel Files:**
- **DO NOT** use the `Read` tool on `.xlsx` files. It fails with "cannot read binary files".
- **ALWAYS** use Python: `pandas.read_excel()` for reading, `pandas.ExcelWriter` for writing.

**PDF Table Extraction:**
- **DO NOT** parse the `Read` tool's base64/encoded output for tabular data.
- **ALWAYS** use `pdfplumber.open()` and `page.extract_tables()` to get structured data.

**Pivot Tables:**
- **DO NOT** call `xlsxwriter.add_pivot_table()` — it does not exist.
- **ALWAYS** compute pivots in pandas with `df.pivot_table()` or `df.groupby()`.

## Required Libraries
```python
import pandas as pd
import numpy as np
import pdfplumber
```

## Standard Workflow

### 1. Extract Data from PDF
```python
with pdfplumber.open('/path/to/document.pdf') as pdf:
    rows = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            rows.extend(table)
    df_pdf = pd.DataFrame(rows[1:], columns=rows[0])

# PDF extraction returns all strings — convert types
for col in df_pdf.columns:
    df_pdf[col] = df_pdf[col].str.strip()
df_pdf = df_pdf.apply(pd.to_numeric, errors='ignore')
```

### 2. Load Data from Excel
```python
df_excel = pd.read_excel('/path/to/data.xlsx')
```

### 3. Align Join-Key Types (CRITICAL)
```python
# Identify join key column (e.g., PRODUCT_ID, STUDENT_ID)
join_key = 'PRODUCT_ID'  # or 'STUDENT_ID' per task

# Convert both sides to string and strip whitespace
df_excel[join_key] = df_excel[join_key].astype(str).str.strip()
df_pdf[join_key] = df_pdf[join_key].astype(str).str.strip()
```

### 4. Data Validation
Check in this order; drop or flag rows that fail:
- Missing join key (null check)
- Non-positive quantities/credits (must be > 0)
- Missing critical numeric fields
- Duplicate record IDs (drop duplicates, keep first)
- Standardize categorical casing (e.g., Title Case for SEMESTER)

### 5. Merge with Validation
```python
merged = df_excel.merge(df_pdf, on=join_key, how='left', suffixes=('', '_pdf'))

# IMMEDIATELY validate merge — silent failures are common
print(f"Pre-merge: {len(df_excel)} rows, Post-merge: {len(merged)} rows")
if len(merged) == 0:
    raise ValueError("Merge produced 0 rows — check join key types or values")
if len(merged) < len(df_excel) * 0.5:
    print("WARNING: Merge lost >50% rows. Check join key alignment.")
```

### 6. Calculate Derived Columns
See `references/sales-metrics.md` or `references/academic-metrics.md` for domain-specific formulas.

### 7. Generate Pivot Tables
Compute pivots in pandas, NOT xlsxwriter:
```python
pivot = merged.pivot_table(index='GROUP_COL', values='VALUE_COL', aggfunc='sum').reset_index()
```

### 8. Multi-Sheet Output
```python
with pd.ExcelWriter('/path/to/output.xlsx', engine='openpyxl') as writer:
    # Use EXACT sheet names from task spec (case-sensitive)
    pivot1.to_excel(writer, sheet_name='Exact Name From Spec', index=False)
    merged.to_excel(writer, sheet_name='SourceData', index=False)
```

### 9. Verify Output
Load the generated workbook and check:
- All required sheets exist with exact names from task spec
- Row counts reconcile: SourceData count matches expected
- Pivot totals reconcile with SourceData aggregations
- No nulls in critical columns after merge
- Derived columns present with correct values

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Verification Checklist

Before finalizing output:
- [ ] Read task spec for EXACT sheet names and column names
- [ ] All expected sheets present with correct names (case-sensitive match)
- [ ] Row counts match: SourceData count equals cleaned input count
- [ ] Post-merge row count is non-zero (merge validation)
- [ ] Pivot totals reconcile with SourceData aggregations
- [ ] Calculated metrics in valid range
- [ ] No nulls in critical join columns after merge
- [ ] Derived columns present in SourceData with correct values
- [ ] Column names match spec exactly (no extra underscores, correct casing)

## Known Invariants (by Sub-task)

### sales-pivot (B1-Sales)
- Join key: PRODUCT_ID
- Derived: REVENUE=QTY×PRICE, PROFIT=REVENUE−(QTY×COST), MARGIN_PCT=PROFIT/REVENUE
- Pivots: Revenue by Category, Units by Region, Category-Region Matrix
- MARGIN_PCT can be negative (costs exceed revenue); do not clamp

### student-performance (B1-StudentPerf)
- Join key: STUDENT_ID
- Derived: GRADE_BAND (A/B/C/D/F), WEIGHTED_SCORE=SCORE×CREDITS, RETAKE_FLAG (Yes if SCORE<70)
- Pivots: Avg Score by Department, Students by Department, Credits by Semester, Dept-Semester Matrix
- GRADE_BAND distribution must sum to total rows

## Anti-Patterns

- **Type mismatch on merge:** Always `.astype(str).str.strip()` join keys on both sides before merging.
- **Silent merge acceptance:** Always check row count after merge; 0 rows = type/value mismatch.
- **Sheet name mismatches:** Match task spec exactly (case-sensitive). Do not invent names.
- **Missing derived columns:** Compute ALL derived columns before pivots; check task spec.
- **xlsxwriter.add_pivot_table():** Does not exist. Compute pivots in pandas.
- **Missing merge suffixes:** Always specify `suffixes=` to prevent duplicate column names.
- **PDF text extraction:** Don't use regex on base64 from Read tool. Use pdfplumber.

## Troubleshooting

- **Zero rows after merge:** Check dtype mismatch on join key (str vs int). Verify ID overlap with `set(df1['KEY']) & set(df2['KEY'])`.
- **pdfplumber returns None:** PDF may be scanned image. Try OCR or report inability to parse.
- **Excel write fails:** Ensure `openpyxl` installed. Use `engine='openpyxl'` explicitly.
- **Missing DEPARTMENT/ CATEGORY values:** Join keys not found in PDF. Check for whitespace or leading zeros.
