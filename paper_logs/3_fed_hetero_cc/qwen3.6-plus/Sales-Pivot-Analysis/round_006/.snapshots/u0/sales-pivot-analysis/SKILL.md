---
name: sales-pivot-analysis
description: Build multi-sheet Excel reports with pivot table summaries from joined CSV+PDF data sources. Use when tasks require aggregating data into pivot sheets, calculated columns, or joining transaction data with PDF lookup tables.
---

# Sales-Pivot-Analysis

## STOP: Critical Rules That Must Be Followed

1. **NEVER use openpyxl pivot API** (TableDefinition, PivotCache, RowColField, DataField) → corrupt files with cacheId errors
2. **NEVER hardcode PDF lookup data** into Python dicts → fails verifier when source data differs
3. **NEVER round/truncate numeric output** → pass raw float values to Excel cells

---

## Workflow

### Step 0: Understand the Task
- Read all source files with Read tool FIRST (CSV, PDF, Excel)
- Identify: join key column, required derived columns, required pivot sheets
- Check task spec for exact sheet names and column names

### Step 1: Load CSV/Excel Data
```python
import pandas as pd
df = pd.read_excel('/path/to/input.xlsx')  # or pd.read_csv()
# Verify: print(df.shape, df.columns.tolist())
```

### Step 2: Extract PDF Table Programmatically
**STOP: Do NOT transcribe PDF content into code. Use extraction tool.**

```python
# Option A: tabula-py (requires Java)
import tabula
tables = tabula.read_pdf('/path/to/catalog.pdf', pages='all')
pdf_df = tables[0]

# Option B: pdfplumber (no Java required)
import pdfplumber
with pdfplumber.open('/path/to/catalog.pdf') as pdf:
    pdf_df = pdf.pages[0].extract_table()
    pdf_df = pd.DataFrame(pdf_df[1:], columns=pdf_df[0])
```

### Step 3: Align Join Keys
**STOP: Type mismatch causes silent 0-row merges. Normalize keys on BOTH sides.**

```python
# Before merge: normalize join keys on both datasets
df['join_key'] = df['join_key'].astype(str).str.strip()
pdf_df['JOIN_KEY'] = pdf_df['JOIN_KEY'].astype(str).str.strip()
```

### Step 4: Merge with Validation
```python
merged = df.merge(pdf_df, left_on='join_key', right_on='JOIN_KEY', how='left', suffixes=('', '_pdf'))

# VALIDATE: Check merge did not produce 0 rows
if len(merged) == 0:
    print("ERROR: Merge produced 0 rows. Check join key alignment.")
    print(f"df keys: {df['join_key'].unique()[:5]}")
    print(f"pdf keys: {pdf_df['JOIN_KEY'].unique()[:5]}")
```

### Step 5: Calculate Derived Columns
See Domain Variants section below for task-specific formulas.

```python
# Example pattern
merged['REVENUE'] = merged['QUANTITY'] * merged['UNIT_COST']
merged['MARGIN_PCT'] = (merged['REVENUE'] - merged['COST']) / merged['REVENUE'] * 100
```

### Step 6: Clean and Prepare SourceData
```python
# Drop rows with null join keys (but keep null measurements for QC tasks)
merged = merged.dropna(subset=['join_key'])
```

### Step 7: Create Pivot Tables with pandas
**STOP: WRONG vs RIGHT**

| WRONG (causes cacheId errors) | RIGHT (verified working) |
|-------------------------------|--------------------------|
| `openpyxl.pivot.table.TableDefinition` | `pd.pivot_table(df, ...)` |
| `PivotCache`, `RowColField`, `DataField` | `df.groupby(...).agg(...)` |
| Creates corrupt Excel files | Creates static tables |

```python
# Semantic sheet-name → aggregation mapping:
# - "Avg X by Y" → mean aggregation
# - "Total X by Y" → sum aggregation
# - "Count of X" → count aggregation
# - "Fail Rate" → percentage (count_fail / count_total * 100)

# Example pivot creation
pivot = pd.pivot_table(
    merged,
    values='REVENUE',
    index='CATEGORY',
    aggfunc='sum'  # 'mean', 'count', etc.
).reset_index()
pivot.columns = ['CATEGORY', 'Total Revenue']
```

### Step 8: Write Multi-Sheet Excel
```python
with pd.ExcelWriter('/path/to/output.xlsx', engine='openpyxl') as writer:
    merged.to_excel(writer, sheet_name='SourceData', index=False)
    pivot1.to_excel(writer, sheet_name='Revenue by Category', index=False)
    pivot2.to_excel(writer, sheet_name='Units by Region', index=False)
```

### Step 9: Validate Output
**STOP: Check categorical value casing before finalizing.**

```python
import openpyxl
wb = openpyxl.load_workbook('/path/to/output.xlsx')
print(f"Sheet names: {wb.sheetnames}")  # Must match spec exactly

# Check categorical values in derived columns
for col in derived_columns:
    unique_vals = merged[col].unique()
    print(f"{col} unique values: {unique_vals}")
    # Verify: 'Yes' vs 'yes', 'at_risk' vs 'At Risk', 'low' vs 'Low'
```

---

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

---

## Semantic Sheet-Name → Aggregation Mapping

| Sheet Name Pattern | Aggregation Type |
|--------------------|------------------|
| "Avg X by Y" | mean |
| "Average of X" | mean |
| "Total X by Y" | sum |
| "Sum of X" | sum |
| "Count of X" | count |
| "X by Y" (countable) | count |
| "Fail Rate by Y" | percentage: count(fail)/count(all)*100 |
| "Rate by Y" | percentage or ratio |

---

## Domain Variants

### Sales (PRODUCT_ID join)
- Derived: REVENUE = QUANTITY * UNIT_COST, PROFIT = REVENUE - TOTAL_COST, MARGIN_PCT = PROFIT/REVENUE*100
- Pivots: Revenue by Category (sum), Units by Region (sum), Category-Region Matrix (sum)

### Student Performance (STUDENT_ID join)
- Derived: GRADE_BAND (A/B/C/D/F from score), WEIGHTED_SCORE, RETAKE_FLAG ('Yes'/'No')
- Pivots: Avg Score by Dept (mean), Students by Dept (count), Credits by Semester (sum)

### Library Circulation (BOOK_ID join)
- Derived: LOAN_DURATION, DECADE (e.g., '1990s'), RETURN_STATUS, WEEKDAY_BUCKET
- Pivots: Loans by Genre (count), Avg Duration by Genre (mean)

### Inventory/Warehouse (SKU join)
- SKU normalization: strip, uppercase, no spaces
- Derived: TOTAL_VALUE, TOTAL_WEIGHT, REORDER_FLAG ('Yes'/'No'), STOCK_STATUS ('at_risk'/'healthy'), VALUE_TIER ('low'/'medium'/'high')
- Multi-source stacking: `pd.concat([df1, df2, df3])` before merge
- Pivots: Stock by Category (sum), Value by Warehouse (sum), Category-Warehouse Matrix (sum)
- **Exact categorical values:** 'Yes', 'No', 'at_risk', 'healthy', 'low', 'medium', 'high'

### Quality Control (PART_ID join)
- PDF: part specs (PART_ID, TOLERANCE_MM, TARGET_WEIGHT)
- Derived: DEVIATION_MM = abs(MEASUREMENT_MM - TARGET_VALUE), WEIGHT_ERROR = abs(ACTUAL_WEIGHT - TARGET_WEIGHT) / TARGET_WEIGHT
- QUALITY_GRADE: A if deviation ≤ tolerance, B if ≤1.5×tolerance, C otherwise, **N/A if MEASUREMENT_MM is null** (NOT dropped)
- Pivots: Fail Rate by Line (percentage, NOT count), Avg Deviation by Line (mean), Inspections by Shift (count)

---

## Known Invariants (by sub-task)

### inventory-warehouse
- SKU must be normalized: `df['SKU'] = df['SKU'].astype(str).str.strip().str.upper().str.replace(' ', '')`
- Categorical values are case-sensitive: 'Yes' (not 'yes'), 'at_risk' (not 'At Risk'), 'low' (not 'Low')

### quality-control
- Rows with null MEASUREMENT_MM must have QUALITY_GRADE = 'N/A', NOT be dropped from SourceData
- "Fail Rate" sheet = percentage (count_fail/count_all*100), NOT raw count

---

## Anti-Patterns

| Don't Do This | Why It Fails |
|---------------|--------------|
| `openpyxl.pivot.table.TableDefinition` | cacheId errors, corrupt Excel files |
| Hardcode PDF table content in Python dicts | Verifier expects dynamic extraction; fails when source differs |
| `round(x, 2)` or `format(x, ".2f")` | Precision mismatch with verifier |
| 'yes' instead of 'Yes' | Categorical value casing mismatch |
| 'At Risk' instead of 'at_risk' | Categorical value casing mismatch |
| Drop rows with null measurements in QC | SourceData must contain all rows; null measurements → 'N/A' grade |

---

## Scripts

- `scripts/extract_pdf_tables.py` - PDF table extraction using tabula-py or pdfplumber