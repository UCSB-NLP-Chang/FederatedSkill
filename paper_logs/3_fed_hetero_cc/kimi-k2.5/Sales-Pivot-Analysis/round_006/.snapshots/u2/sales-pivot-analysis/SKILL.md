---
name: sales-pivot-analysis
description: Generate multi-sheet Excel reports from joined data sources (Excel, CSV, PDF) with pivot tables, calculated fields, and domain-specific aggregations. Use when tasks require combining transactional data with lookup/reference tables, creating pivot summaries, or building multi-sheet workbooks.
---

# Sales-Pivot-Analysis (Umbrella)

Build multi-sheet Excel reports from joined datasets, with calculated fields and pivot tables.

## STOP: Critical Anti-Patterns (Mandatory Before Workflow)

1. **Do NOT use openpyxl pivot API (TableDefinition, PivotCache, RowColField)** — causes cacheId errors and corrupt Excel files. Use `pd.pivot_table()` or `groupby()` instead, write results as static tables.
2. **Do NOT hardcode PDF lookup data in Python dicts** — use programmatic extraction (tabula-py, camelot, pdfplumber). Hardcoding breaks when source data differs.
3. **Do NOT skip reading the task spec first** — sheet names, column names, categorical values must be extracted from spec before writing.
4. **Do NOT assume sheet name implies aggregation type** — "Fail Rate" = percentage/rate (NOT count), "Avg X" = mean, "Inspections" = count. Match semantics.

## Workflow

0. **Read Task Spec (MANDATORY)** — Extract exact sheet names, column names, categorical values, aggregation types from spec before coding.
1. **Identify all data sources** — Excel, CSV, PDF tables.
2. **Parse each source programmatically**:
   - Excel/CSV: `pandas.read_excel()` or `pandas.read_csv()` (NOT Read tool for data loading)
   - PDF: `tabula-py`, `camelot`, or `pdfplumber` (NOT Read tool, NOT hardcoded dicts)
3. **Align join-key types** — `.astype(str).str.strip()` on both sides before merge.
4. **Join datasets** — `df.merge()` with `suffixes=` to prevent duplicate columns.
5. **Validate merge** — Check post-merge row count non-zero.
6. **Add calculated columns** — Vectorized pandas operations (see Domain Variants below).
7. **Create pivot aggregations** — `pd.pivot_table()` or `groupby()` (NOT openpyxl pivot API).
8. **Write multi-sheet Excel** — `pd.ExcelWriter()` with `engine='openpyxl'`, verify sheet names match spec exactly.
9. **Verify output** — Load with `openpyxl.load_workbook()`, check sheet names, shapes, categorical value casing.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance decides acceptable precision; the skill's job is to give it full precision.

## Semantic Pivot Matching

Sheet names imply aggregation type — verify before computing:

| Sheet Name Pattern | Aggregation Type | Example |
|--------------------|------------------|---------|
| "X Rate by Y" | percentage/rate | `aggfunc='mean'` on ratio column |
| "Avg X by Y" | mean | `aggfunc='mean'` |
| "Total X by Y" | sum | `aggfunc='sum'` |
| "X Count" / "Inspections by Y" | count | `aggfunc='count'` |
| "X-Y Matrix" | cross-tab mean/sum | `pd.pivot_table(index=, columns=, values=)` |

## Domain Variants (by Sub-Task Type)

### B1-Sales (R0)
- **Join key:** PRODUCT_ID
- **Derived columns:** REVENUE = quantity * unit_price, PROFIT = REVENUE - (quantity * unit_cost), MARGIN_PCT = PROFIT / REVENUE * 100
- **Pivots:** Revenue by Category (sum), Units by Region (sum), Category-Region Matrix (sum)

### B1-StudentPerf (R1)
- **Join key:** STUDENT_ID
- **Derived columns:** GRADE_BAND = A/B/C/D/F based on score thresholds, WEIGHTED_SCORE = score * credits, RETAKE_FLAG = Yes/No based on threshold
- **Pivots:** Avg Score by Dept (mean), Students by Dept (count), Credits by Semester (sum)
- **Exact categorical values:** 'Yes', 'No', 'A', 'B', 'C', 'D', 'F' (case-sensitive)

### B1-LibraryCirc (R2)
- **Join key:** BOOK_ID
- **Derived columns:** LOAN_DURATION = return_date - borrow_date, DECADE = '1990s' from year, RETURN_STATUS, WEEKDAY_BUCKET
- **Pivots:** Loans by Genre (count), Avg Duration by Genre (mean), Loans by Borrower Type (count)

### B1-Inventory (R3)
- **Join key:** SKU — normalize: `.astype(str).str.strip().str.upper().str.replace(' ', '')`
- **Derived columns:** TOTAL_VALUE = quantity * unit_cost, TOTAL_WEIGHT = quantity * weight, REORDER_FLAG = Yes/No based on threshold, STOCK_STATUS = 'at_risk' / 'healthy', VALUE_TIER = 'low' / 'medium' / 'high'
- **Multi-source stacking:** `pd.concat([df1, df2], ignore_index=True)` before join
- **Exact categorical values:** 'Yes', 'No', 'at_risk', 'healthy', 'low', 'medium', 'high' (case-sensitive)

### B1-QualityControl (R4)
- **Join key:** PART_ID
- **Derived columns:** DEVIATION_MM = abs(MEASUREMENT_MM - TARGET_VALUE), WEIGHT_ERROR = abs(ACTUAL_WEIGHT - TARGET_WEIGHT) / TARGET_WEIGHT
- **QUALITY_GRADE:** A if deviation <= tolerance, B if <=1.5*tolerance, C otherwise, **N/A if MEASUREMENT_MM is null** (critical: NOT dropped)
- **Pivots:** Fail Rate by Line (rate/percentage, NOT count), Avg Deviation by Line (mean), Inspections by Shift (count), Line-Shift Matrix
- **Exact categorical values:** 'A', 'B', 'C', 'N/A' (case-sensitive)

## Known Invariants (by Sub-Task)

### B1-QualityControl
- Missing MEASUREMENT_MM rows must stay in SourceData with QUALITY_GRADE = 'N/A'
- "Fail Rate by Line" = percentage/rate, calculated as: `fail_count / total_count * 100`

## PDF Table Extraction

```python
# tabula-py (requires Java)
import tabula
tables = tabula.read_pdf("/path/to/file.pdf", pages="all", multiple_tables=True)
df = tables[0]

# camelot (more robust for complex tables)
import camelot
tables = camelot.read_pdf("/path/to/file.pdf", pages="all")
df = tables[0].df

# pdfplumber (no Java dependency)
import pdfplumber
with pdfplumber.open("/path/to/file.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        df = pd.DataFrame(tables[0])
```

## Verification Checklist

```python
import pandas as pd
xl = pd.ExcelFile("/path/to/output.xlsx")
print("Sheets:", xl.sheet_names)
for sheet in xl.sheet_names:
    df = xl.parse(sheet)
    print(f"{sheet}: {df.shape}")
    print(df.head(3))
    # Check categorical value casing
    for col in df.select_dtypes(include='object').columns:
        print(f"  {col} values: {df[col].unique()[:5]}")
```

## Common Failure Modes

| Symptom | Fix |
|---------|-----|
| Join produces 0 rows | Verify key columns match: `.astype(str).str.strip()` both sides |
| Pivot sheet has wrong values | Check aggregation type matches sheet name semantics |
| Verifier says categorical mismatch | Check exact casing: 'Yes' vs 'yes', 'at_risk' vs 'At Risk' |
| Excel won't open / cacheId error | Did you use openpyxl pivot API? Use pd.pivot_table() instead |
| Derived column wrong | Verify formula matches spec exactly |

## References

- `scripts/extract_pdf_tables.py` — Reusable PDF table extraction (tabula/camelot)
- `scripts/generate_compensation_report.py` — Full report generation template with joins, pivots, multi-sheet output