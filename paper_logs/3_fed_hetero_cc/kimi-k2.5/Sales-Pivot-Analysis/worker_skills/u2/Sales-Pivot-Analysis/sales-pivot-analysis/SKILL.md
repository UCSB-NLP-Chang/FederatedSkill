---
name: sales-pivot-analysis
description: Create multi-sheet Excel pivot reports from PDF+Excel data sources. Use when tasks require joining datasets, calculating derived columns, and generating pivot table summaries. Covers sales, inventory, student performance, library circulation, quality control, event registration, and budget reconciliation domains.
---

# Multi-Sheet Excel Pivot Report Generation

## STOP: Critical Anti-Patterns

**DO NOT USE openpyxl pivot API (TableDefinition, PivotCache).**
- Causes `cacheId` errors and corrupt files.
- Use `pd.pivot_table()` or `groupby()` → write results as static tables.

**DO NOT HARDCODE PDF TABLE DATA INTO PYTHON DICTS.**
- Hardcoding fails verifier when source data differs.
- ALWAYS extract PDF tables programmatically:
```python
import pdfplumber
with pdfplumber.open("/path/to/file.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        if tables:
            df = pd.DataFrame(tables[0][1:], columns=tables[0][0])
```
- If PDF contains text tables (not embedded tables), parse with regex from extracted text.

## Workflow

1. **Load Excel data via pandas** — `pd.read_excel()` (NOT Read tool - binary files fail)
2. **Extract PDF tables programmatically** — `tabula-py`, `camelot`, or `pdfplumber`
   - STOP: Do NOT transcribe PDF content into hardcoded Python dicts.
3. **Align join-key types** — `.astype(str).str.strip()` both sides before merge
4. **Clean/validate** — drop null join keys, verify positive quantities, dedupe IDs
5. **Left merge with suffixes** — `suffixes=('_left','_right')` to prevent duplicate columns
6. **Validate merge** — check post-merge row count > 0
7. **Calculate derived columns** — see Domain Variants section below
8. **Compute pivots with pandas** — `pd.pivot_table()` or `groupby()` (NOT openpyxl API)
   - Rename pivot columns to match spec exactly (e.g., `'Sum of REVENUE'`, `'Count of REG_ID'`)
   - If spec requires Total row:
     ```python
     total_row = pd.DataFrame([['Total', pivot['Sum of REVENUE'].sum()]], columns=pivot.columns)
     pivot = pd.concat([pivot, total_row], ignore_index=True)
     ```
9. **Write multi-sheet Excel** — exact sheet names, column names, categorical casing from spec
10. **Validate output** — openpyxl.load_workbook() succeeds, sheetnames match, categorical casing exact

## Multi-Source Column Alignment

When combining sources with different column names (e.g., online vs walk-in registrations):
```python
# Rename columns to align before concat
walkin_df = walkin_df.rename(columns={
    'walk_in_id': 'REG_ID',
    'event_code': 'EVENT_ID',
    'guest_name': 'ATTENDEE_NAME'
})

# Add source tracking column before combining
online_df['SOURCE'] = 'Online'
walkin_df['SOURCE'] = 'Walk-in'
combined_df = pd.concat([online_df, walkin_df], ignore_index=True)
```

## Wide-to-Long Transformation

When source data has repeated column patterns (e.g., Q1_BUDGET, Q2_BUDGET, Q3_BUDGET, Q4_BUDGET):
```python
# Method 1: pd.melt() for simple cases
budget_long = pd.melt(budget_wide, 
    id_vars=['DEPT_NAME', 'CATEGORY'],
    value_vars=['Q1_BUDGET', 'Q2_BUDGET', 'Q3_BUDGET', 'Q4_BUDGET'],
    var_name='FISCAL_QUARTER',
    value_name='BUDGET_AMOUNT')
budget_long['FISCAL_QUARTER'] = budget_long['FISCAL_QUARTER'].str.replace('_BUDGET', '')

# Method 2: Manual iteration for complex transformations
budget_long = pd.DataFrame()
for _, row in budget_wide.iterrows():
    for q in ['Q1', 'Q2', 'Q3', 'Q4']:
        budget_long = pd.concat([budget_long, pd.DataFrame({
            'DEPT_NAME': [row['DEPT_NAME']],
            'CATEGORY': [row['CATEGORY']],
            'FISCAL_QUARTER': [q],
            'BUDGET_AMOUNT': [row[f'{q}_BUDGET']]
        })], ignore_index=True)
```

## SemanticSheet → Aggregation Mapping (R4 Evidence)

Sheet names imply aggregation type. Match exactly:

| Sheet Name Pattern | Aggregation | Example |
|--------------------|-------------|----------|
| "Fail Rate by X" | RATE (percentage) | `df['PASS_FAIL'].eq('Fail').mean()` |
| "Avg X by Y" | MEAN | `df.groupby(Y)[X].mean()` |
| "X by Y" (no qualifier) | COUNT | `df.groupby(Y)[X].count()` |
| "Total X by Y" | SUM | `df.groupby(Y)[X].sum()` |
| "Revenue by X" | SUM | `df.groupby(X)['REVENUE'].sum()` |
| "Spending by X" | SUM | `df.groupby(X)['amount'].sum()` |
| "Variance by X" | SUM | `df.groupby(X)['VARIANCE'].sum()` |
| "Attendance by X" | COUNT | `df.groupby(X).size()` |
| "X-Y Matrix" | Cross-tab with aggfunc | `pd.pivot_table(values=X, index=Y, columns=Z, aggfunc='sum')` |

STOP: Before writing pivot sheet, verify aggregation type matches sheet name.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Domain Variants (Derived Columns by Sub-Task)

### B1-Sales
Join: `PRODUCT_ID` | Derived columns:
- `REVENUE` = `quantity * unit_price`
- `PROFIT` = `REVENUE - (quantity * unit_cost)`
- `MARGIN_PCT` = `PROFIT / REVENUE * 100`
- Pivot sheets: "Revenue by Category", "Units by Region", "Category-Region Matrix"

### B1-StudentPerf
Join: `STUDENT_ID` | Derived columns:
- `GRADE_BAND` = A/B/C/D/F based on score thresholds
- `WEIGHTED_SCORE` = `score * credits`
- `RETAKE_FLAG` = 'Yes' / 'No' (exact casing)
- Pivot sheets: "Avg Score by Dept", "Students by Dept", "Credits by Semester"

### B1-LibraryCirc
Join: `BOOK_ID` | Derived columns:
- `LOAN_DURATION` = `return_date - checkout_date`
- `DECADE` = '1990s', '2000s', etc. based on year
- `RETURN_STATUS` = 'On Time' / 'Late' / 'Missing'
- `WEEKDAY_BUCKET` = 'Weekday' / 'Weekend'
- Pivot sheets: "Loans by Genre", "Avg Duration by Genre", "Loans by Borrower Type"

### B1-Inventory
Join: `SKU` (normalize: strip/uppercase/no-spaces)
- Multi-source stacking via `pd.concat()`
- Derived columns:
  - `TOTAL_VALUE` = `quantity * unit_cost`
  - `TOTAL_WEIGHT` = `quantity * weight_per_unit`
  - `REORDER_FLAG` = 'Yes' / 'No' (exact casing)
  - `STOCK_STATUS` = 'at_risk' / 'healthy' (exact casing)
  - `VALUE_TIER` = 'low' / 'medium' / 'high' (exact casing)
- Pivot sheets: "Stock by Category", "Value by Warehouse", "Items by Category", "Category-Warehouse Matrix"

### B1-QualityControl
Join: `PART_ID` | Derived columns:
- `DEVIATION_MM` = `abs(MEASUREMENT_MM - TARGET_VALUE)`
- `WEIGHT_ERROR` = `abs(ACTUAL_WEIGHT - TARGET_WEIGHT) / TARGET_WEIGHT`
- `QUALITY_GRADE`:
  - 'A' if deviation <= tolerance
  - 'B' if deviation <= 1.5 * tolerance
  - 'C' otherwise
  - 'N/A' if MEASUREMENT_MM is null (DO NOT drop these rows)
- Pivot sheets: "Fail Rate by Line" (rate %, NOT count), "Avg Deviation by Line", "Inspections by Shift", "Line-Shift Matrix"

### B1-EventRegistration
Join: `EVENT_ID` | Multi-source: online + walk-in registrations
- Column alignment required (different names for same data)
- Derived columns:
  - `IS_VIP` = 'Yes' if `REG_TYPE == 'VIP'` else 'No' (exact casing)
  - `PRICE_TIER` = 'Premium' / 'Standard' / 'Budget' based on REG_TYPE mapping
- Pivot sheets:
  - "Revenue by Track" → SUM of AMOUNT_PAID by TRACK
  - "Attendance by Venue" → COUNT by VENUE
  - "Track RegType Matrix" → SUM of AMOUNT_PAID by TRACK × REG_TYPE (pivot_table with columns)
  - "Events by Track" → COUNT by TRACK
- Source tracking: Add `SOURCE` column ('Online' / 'Walk-in') before combining

### B1-BudgetReconciliation
Join chain: `team_code` → hierarchy → `DEPT_NAME` + `CATEGORY` + `FISCAL_QUARTER`
- Multi-step join: expenses → hierarchy (on team_code) → budget (on DEPT_NAME + CATEGORY + QUARTER)
- Wide-to-long transformation: budget allocations from Q1_BUDGET, Q2_BUDGET, etc. to long format
- Derived columns:
  - `VARIANCE` = `amount - BUDGET_AMOUNT`
  - `UTILIZATION_PCT` = `amount / BUDGET_AMOUNT`
- Pivot sheets:
  - "Spending by Division" → SUM of amount by DIVISION
  - "Spending by Department" → SUM of amount by DEPT_NAME
  - "Variance by Department" → SUM of VARIANCE by DEPT_NAME
  - "Category Quarter Matrix" → SUM of amount by expense_category × fiscal_quarter
  - "Avg Utilization by Division" → MEAN of UTILIZATION_PCT by DIVISION

## Categorical Value Casing (R3 Evidence)

Exact casing is mandatory. Common failures:
- 'Yes' ≠ 'yes' | 'No' ≠ 'no'
- 'at_risk' ≠ 'At Risk' | 'healthy' ≠ 'Healthy'
- 'low' / 'medium' / 'high' (exact lowercase)
- 'Online' / 'Walk-in' (exact casing for SOURCE column)

Add Step 10 validation:
```python
for val in df['REORDER_FLAG'].unique():
    assert val in ('Yes', 'No'), f"Categorical casing mismatch: {val}"
```

## Known invariants (by sub-task)

### B1-Inventory
- SKU normalization: `.astype(str).str.strip().str.upper().str.replace(' ', '')`
- Multi-source stacking before merge
- Categorical values: 'Yes'/'No', 'at_risk'/'healthy', 'low'/'medium'/'high'

### B1-QualityControl
- Null MEASUREMENT_MM rows: keep in SourceData with QUALITY_GRADE='N/A'
- Fail Rate pivot: must be percentage (rate), NOT count
- Derived formulas use TARGET_VALUE and TARGET_WEIGHT from PDF specs

### B1-Sales
- Join-key type alignment prevents silent 0-row merge

### B1-EventRegistration
- Multi-source column renaming before concat
- Inner join with event catalog drops invalid EVENT_IDs (expected behavior)
- Add SOURCE column before combining to track origin

### B1-BudgetReconciliation
- Budget data often in wide format (Q1_BUDGET, Q2_BUDGET columns)
- Transform to long format before joining with expenses
- Hierarchy lookup: team_code → TEAM_NAME → DEPT_NAME → DIVISION

## PDF Table Extraction Code

```python
# tabula-py (requires Java)
import tabula
tables = tabula.read_pdf("/path/to/file.pdf", pages="all", multiple_tables=True)
df_lookup = tables[0]

# camelot (more robust)
import camelot
tables = camelot.read_pdf("/path/to/file.pdf", pages="all")
df_lookup = tables[0].df

# pdfplumber (pure Python, no Java)
import pdfplumber
with pdfplumber.open("/path/to/file.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
```

## Verification Checklist

Before declaring success:
1. **Sheet names** match spec exactly (casing, spacing)
2. **Pivot column headers** match spec exactly (e.g., `Sum of AMOUNT_PAID`, `Count of REG_ID`). Do not use default pandas names like `AMOUNT_PAID` unless specified.
3. **Total rows** — If spec implies totals, append `Total` row at bottom of pivot sheets. Verify sum matches.
4. Aggregation type matches sheet name (rate vs count vs mean vs sum)
5. Categorical values use exact casing
6. Numeric values written raw (no rounding)
7. Null-derived rows present with 'N/A' grade (QC domain)
8. Merge row count > 0
9. `openpyxl.load_workbook(path)` succeeds
10. PDF data extracted programmatically (NOT hardcoded)
