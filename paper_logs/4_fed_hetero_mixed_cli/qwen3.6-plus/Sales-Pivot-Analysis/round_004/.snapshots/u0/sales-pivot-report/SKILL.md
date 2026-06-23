---
name: sales-pivot-report
description: Generate multi-sheet Excel pivot reports from mixed data sources (PDF catalogs, Excel/CSV transactions) across domains (sales, library circulation, academic records, inventory/warehouse). Handles data extraction, cleaning, reconciliation, pivot table creation, and Excel export. Use when combining reference data from PDFs with transactional data from spreadsheets.
---

# Sales Pivot Report Generation

## Before You Code (MANDATORY)

1. **Read `test_output.py` first.** Identify:
   - Expected sheet names (exact spelling/casing)
   - Expected column names in each sheet
   - Derived/computed columns the test checks
   - Join keys and data types
   - Numeric precision requirements
2. **Do not guess sheet names or column names.** The test suite is the specification.
3. **Map your domain to the test expectations** using the Domain Adaptation table below.

## Workflow

1. **Inventory sources** - Identify all input files (PDF, XLSX, CSV) and their formats.

2. **Extract PDF tables** - Use `pdfplumber`:
   ```python
   import pdfplumber
   with pdfplumber.open('catalog.pdf') as pdf:
       tables = []
       for page in pdf.pages:
           table = page.extract_table()
           if table:
               df = pd.DataFrame(table[1:], columns=table[0])
               tables.append(df)
       catalog = pd.concat(tables, ignore_index=True)
   ```
   **Fallback**: If `extract_table()` returns `None`, use `page.extract_text()` and parse lines using domain keywords.

3. **Read & stack multiple XLSX/CSV sources** (when applicable):
   ```python
   files = ['warehouse_a.xlsx', 'warehouse_b.xlsx']
   dfs = [pd.read_excel(f) for f in files]
   combined = pd.concat(dfs, ignore_index=True)
   ```

4. **Clean & normalize** - BEFORE joining:
   - Strip whitespace: `df['col'] = df['col'].str.strip()`
   - Normalize case: Title for names, UPPER for codes/IDs
   - Cast join keys to same dtype: `df['SKU'] = df['SKU'].astype(str).str.strip()`
   - Drop duplicates

5. **Validate keys** - Check referential integrity:
   ```python
   unknown = set(trans['SKU']) - set(catalog['SKU'])
   if unknown:
       print(f"Unmatched IDs: {unknown}")
   ```

6. **Join & reconcile** - Merge transactions with catalog. Fill missing values from reference data.

7. **Calculate domain-specific metrics** (see Domain Adaptation table).

8. **Create pivot tables** - Use `pd.pivot_table()`:
   ```python
   pivot = pd.pivot_table(df, values='REVENUE', index='CATEGORY',
                          columns='REGION', aggfunc='sum', fill_value=0)
   ```

9. **Flatten MultiIndex columns** - BEFORE writing to Excel:
   ```python
   if isinstance(df.columns, pd.MultiIndex):
       df.columns = [c[-1] if isinstance(c, tuple) else str(c) for c in df.columns]
   ```

10. **Write multi-sheet Excel**:
    ```python
    with pd.ExcelWriter('report.xlsx', engine='openpyxl') as writer:
        source_data.to_excel(writer, sheet_name='SourceData', index=False)
        pivot.to_excel(writer, sheet_name='PivotSummary', index=False)
    ```

---

## GATE: pytest verification (Step 11)

**CRITICAL: Run pytest immediately after writing the Excel file.**

```bash
pytest test_output.py -v
```

**If tests pass:**
1. Create marker file: `touch .pytest_passed`
2. Then you may write DONE.txt

**If tests fail:**
- Read the failure message
- Identify the issue from the troubleshooting table below
- Fix the script
- Re-run pytest
- Repeat until pass

**You may NOT write DONE.txt unless `.pytest_passed` exists in the workspace.**

### Locating test files
If `test_output.py` is not found initially:
- Check subdirectories: `find . -name "test_*.py" -o -name "*_test.py"`
- Check the task workspace root (may appear after output generation)
- Run pytest anyway: `pytest -v` (pytest discovers test files automatically)

---

## Test Failure Troubleshooting

| Failure | Check |
|---------|-------|
| Sheet name mismatch | Exact spelling/casing in `sheet_name=` |
| Column name mismatch | Headers match test expectations (case-sensitive) |
| Numeric precision mismatch | Raw floats, no rounding |
| Missing sheet | All sheets written in ExcelWriter block |
| Wrong aggregation | `aggfunc` matches test expectations |
| Row count mismatch | Join logic, whitespace stripping, dtype casting |

---

## Domain Adaptation

| Domain | Join Key | Metrics | Pivot Dimensions | Typical Sheets |
|---|---|---|---|---|
| Sales | `PRODUCT_ID` | Revenue, Profit, Margin | Category, Region | SourceData, PivotSummary |
| Library Circulation | `BOOK_ID` | Loan Duration, Return Rate | Genre, Borrower Type | Loans by Genre, Avg Duration by Genre, Loans by Borrower Type, Genre Borrower Matrix, SourceData |
| Academic Records | `STUDENT_ID` | Avg Score, GPA | Department, Semester | Avg Score by Department, Students by Department, Credits by Semester, Department Semester Matrix, SourceData |
| Inventory/Warehouse | `SKU` | Total Value, Total Weight, Reorder Flag | Category, Warehouse | SourceData, Stock by Category, Value by Warehouse, Items by Category, Category Warehouse Matrix |

Verify exact join key and sheet names from `test_output.py` before coding.

---

## Critical Anti-Patterns

### Manual Verification Trap (CRITICAL)
Checking file existence, row counts, printing dataframes, or verifying calculations manually is NOT verification. **Only pytest determines pass/fail.** Do not proceed to DONE.txt based on manual checks.

### MultiIndex Export Failure
`openpyxl` raises `ValueError` on tuple headers. Always flatten before writing.

### PivotChart Import Error
`from openpyxl.chart import PivotChart` raises ImportError. Use `pd.pivot_table()` instead.

### Whitespace in Join Keys
PDF extraction includes trailing spaces. Always `.str.strip()` before merging.

### Silent Join Mismatches
Mismatched dtypes (str vs int IDs) cause silent row drops. Cast to same type before merge.

### Skipping Test Inspection
Never code sheet names or column names from memory or assumptions. Read `test_output.py` first.

---

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision.

---

## Known invariants (by sub-task)

### pdf-catalog-transaction-merge
- Join key: `PRODUCT_ID`
- Sheets: `SourceData`, `PivotSummary`
- Pivot headers must be flat strings

### library-circulation-pivot
- Join key: `BOOK_ID`
- Sheets: `Loans by Genre`, `Avg Duration by Genre`, `Loans by Borrower Type`, `Genre Borrower Matrix`, `SourceData`
- Derived: `LOAN_DURATION`, `DECADE`, `RETURN_STATUS`, `WEEKDAY_BUCKET`
- Validation: `RETURN_DATE > LOAN_DATE`

### student-performance-pivot
- Join key: `STUDENT_ID`
- Sheets: `Avg Score by Department`, `Students by Department`, `Credits by Semester`, `Department Semester Matrix`, `SourceData`
- Derived: `GRADE_BAND`, `WEIGHTED_SCORE`, `TERM_STATUS`, `RETAKE_FLAG`

### inventory-multi-warehouse-pivot
- Join key: `SKU` (normalize case, trim whitespace)
- Expected sheets: `Stock by Category`, `Value by Warehouse`, `Items by Category`, `Category Warehouse Matrix`, `SourceData`
- Derived: `TOTAL_VALUE` (QUANTITY × UNIT_VALUE), `TOTAL_WEIGHT` (QUANTITY × WEIGHT_KG), `REORDER_FLAG` (Yes/No based on REORDER_LEVEL), `STOCK_STATUS` (healthy/at_risk/critical), `VALUE_TIER` (low/medium/high)
- Multi-source: Stack multiple warehouse XLSX files before joining with PDF catalog

---

## Troubleshooting

See `references/common-issues.md` for PDF extraction, encoding, dtype issues, and test discovery problems.