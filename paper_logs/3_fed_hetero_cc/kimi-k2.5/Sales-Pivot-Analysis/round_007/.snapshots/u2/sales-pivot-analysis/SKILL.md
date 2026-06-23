---
name: sales-pivot-analysis
description: Generate multi-sheet Excel reports from joined data sources (Excel, CSV, PDF) with pivot tables, calculated fields, and domain-specific aggregations. Use when tasks require combining transactional data with lookup/reference tables, creating pivot summaries, or building multi-sheet workbooks.
---

# Multi-Source Pivot Analysis

Build multi-sheet Excel reports from joined datasets with calculated fields and pivot aggregations.

## STOP: Critical Anti-Patterns (Mandatory Before Workflow)

1. **NEVER use openpyxl pivot API** (`TableDefinition`, `PivotCache`, `RowColField`, `DataField`) → causes `cacheId` errors and corrupt Excel files. Use `pd.pivot_table()` or `groupby()` instead, write results as static tables.
2. **NEVER hardcode PDF lookup data in Python** → always extract programmatically using `tabula-py`, `camelot`, or `pdfplumber`. Hardcoding breaks verifier when source data changes.
3. **NEVER round or format numeric output** → pass raw float values directly. Verifier's tolerance decides acceptable precision.
4. **Do NOT skip reading the task spec first** → extract exact sheet names, column names, categorical values, and aggregation types before coding.
5. **Do NOT assume sheet name implies aggregation type** → "Rate" = percentage, "Avg" = mean, "Count/Inspections" = count. Match semantics exactly.

## Workflow

0. **Read Task Spec (MANDATORY)** — Extract exact sheet names, column names, categorical values, aggregation types.
1. **Load/Extract Data Programmatically**:
   - Excel/CSV: `pandas.read_excel()` or `pandas.read_csv()`
   - PDF: Use `scripts/extract_pdf_tables.py` or inline extraction — **never hardcode**
2. **Identify & Align Multi-Source Columns** — Map columns from different sources (e.g., online vs walk-in) to a unified schema using `.rename()`. Add `SOURCE` tracking column before `pd.concat()`.
3. **Normalize Join Keys** — `.astype(str).str.strip()` on both sides before merge to prevent type mismatches.
4. **Join Datasets** — `df.merge()` with `suffixes=` and appropriate `how=`. Validate post-merge row count > 0.
5. **Calculate Derived Columns** — Use vectorized pandas operations (see Domain Variants below).
6. **Create Pivot Aggregations** — `pd.pivot_table()` or `df.groupby().agg()`. Map sheet names to correct `aggfunc`. Rename output columns to match spec exactly (e.g., `Sum of REVENUE`).
7. **Handle Totals (if required)** — Append a `Total` row at the bottom of pivot sheets if the spec implies it.
8. **Write Multi-Sheet Excel** — `pd.ExcelWriter(engine='openpyxl')`, verify sheet names match spec exactly.
9. **Verify Output** — Load with `openpyxl.load_workbook()`, check shapes, categorical casing, and raw float precision.

## Multi-Source Column Alignment

```python
# Map walk-in columns to online schema
walkin_df = walkin_df.rename(columns={
    "walk_in_id": "REG_ID", "event_code": "EVENT_ID",
    "guest_name": "ATTENDEE_NAME", "registration_type": "REG_TYPE", "fee_paid": "AMOUNT_PAID"
})
online_df["SOURCE"] = "Online"
walkin_df["SOURCE"] = "Walk-in"
combined = pd.concat([online_df, walkin_df], ignore_index=True)
```

## Join Key Normalization

```python
def normalize_key(df, col):
    df[col] = df[col].astype(str).str.strip()
    return df

df_source = normalize_key(df_source, "JOIN_KEY")
df_lookup = normalize_key(df_lookup, "JOIN_KEY")
```

## Semantic Pivot Matching

| Sheet Name Pattern | Aggregation Type | pandas `aggfunc` / Logic |
|--------------------|------------------|--------------------------|
| "X Rate by Y" / "Fail Rate" | Percentage/Rate | `count_fail / count_total * 100` or `mean` on ratio col |
| "Avg X by Y" / "Average of X" | Mean | `'mean'` |
| "Total X by Y" / "Sum of X" | Sum | `'sum'` |
| "Count of X" / "Inspections by Y" | Count | `'count'` or `'size'` |
| "X-Y Matrix" | Cross-tab | `pivot_table(index=, columns=, values=, aggfunc=)` |

**CRITICAL:** Rename pivot columns to match spec exactly (e.g., `Sum of AMOUNT_PAID`). Default pandas names like `AMOUNT_PAID` will fail verifiers.

## Domain Variants (by Sub-Task)

### B1-Sales
- **Join key:** `PRODUCT_ID`
- **Derived:** `REVENUE = qty * unit_price`, `PROFIT = REVENUE - (qty * unit_cost)`, `MARGIN_PCT = PROFIT / REVENUE * 100`
- **Pivots:** Revenue by Category (sum), Units by Region (sum), Category-Region Matrix (sum)

### B1-StudentPerf
- **Join key:** `STUDENT_ID`
- **Derived:** `GRADE_BAND` (A/B/C/D/F), `WEIGHTED_SCORE`, `RETAKE_FLAG` ('Yes'/'No')
- **Pivots:** Avg Score by Dept (mean), Students by Dept (count), Credits by Semester (sum)

### B1-LibraryCirc
- **Join key:** `BOOK_ID`
- **Derived:** `LOAN_DURATION`, `DECADE` ('1990s'), `RETURN_STATUS`, `WEEKDAY_BUCKET`
- **Pivots:** Loans by Genre (count), Avg Duration by Genre (mean), Loans by Borrower Type (count)

### B1-Inventory
- **Join key:** `SKU` (normalize: strip/uppercase/no-spaces)
- **Derived:** `TOTAL_VALUE`, `TOTAL_WEIGHT`, `REORDER_FLAG` ('Yes'/'No'), `STOCK_STATUS` ('at_risk'/'healthy'), `VALUE_TIER` ('low'/'medium'/'high')
- **Pivots:** Stock by Category (sum), Value by Warehouse (sum), Category-Warehouse Matrix (sum)
- **Multi-source:** `pd.concat()` before merge. See `references/inventory-patterns.md`.

### B1-QualityControl
- **Join key:** `PART_ID`
- **Derived:** `DEVIATION_MM`, `WEIGHT_ERROR`, `QUALITY_GRADE` ('A'/'B'/'C', **'N/A' if measurement is null** — DO NOT drop)
- **Pivots:** Fail Rate by Line (percentage, NOT count), Avg Deviation by Line (mean), Inspections by Shift (count)
- **Invariant:** Null measurements → `QUALITY_GRADE = 'N/A'`. See `references/quality-control-patterns.md`.

### B1-EventRegistration
- **Join key:** `EVENT_ID` (multi-source: online + walk-in)
- **Derived:** `SOURCE` ('Online'/'Walk-in'), `IS_VIP` ('Yes'/'No'), `PRICE_TIER` ('Budget'/'Standard'/'Premium'/'Free')
- **Pivots:** Revenue by Track (sum), Attendance by Venue (count), Track RegType Matrix (sum), Events by Track (count)
- **Invariant:** Inner join with catalog drops invalid IDs. See `references/event-registration-patterns.md`.

## Output Precision
Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: `ws.cell(row=r, column=c, value=x)` with raw float

## PDF Table Extraction
```python
# pdfplumber (no Java, recommended)
import pdfplumber
with pdfplumber.open("/path/to/file.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        df = pd.DataFrame(tables[0][1:], columns=tables[0][0])

# tabula-py (requires Java)
import tabula
tables = tabula.read_pdf("/path/to/file.pdf", pages="all", multiple_tables=True)
df = tables[0]
```

## Verifier Validation Checklist
1. **Sheet Names**: Exact match with spec (case-sensitive, spaces matter).
2. **Pivot Headers**: Match spec exactly (e.g., `Sum of AMOUNT_PAID`). Do not use default pandas column names.
3. **Total Rows**: If spec implies totals, append a `Total` row at the bottom.
4. **Categorical Values**: Verify exact casing (`Yes` vs `yes`, `at_risk` vs `At Risk`, `N/A` vs `na`).
5. **Row Counts**: `SourceData` must contain all joined rows. Do not drop valid rows unless instructed.
6. **Precision**: All numeric cells are raw floats. No string formatting.
7. **File Integrity**: `openpyxl.load_workbook(path)` succeeds without errors.
8. **PDF Extraction**: Data was extracted programmatically, NOT hardcoded.

## Scripts
- `scripts/extract_pdf_tables.py` — Reusable PDF table extraction (tabula/camelot/pdfplumber)
- `scripts/generate_report.py` — Full report generation template with joins, pivots, multi-sheet output

## References
- `references/event-registration-patterns.md` — Column alignment, tiered pricing logic, source tracking
- `references/inventory-patterns.md` — SKU normalization, stock status calculations
- `references/quality-control-patterns.md` — Grade calculations with null handling, fail rate formulas