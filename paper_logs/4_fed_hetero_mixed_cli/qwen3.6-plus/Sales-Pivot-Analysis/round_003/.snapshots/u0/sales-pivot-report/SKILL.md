---
name: sales-pivot-report
description: Generate multi-sheet Excel pivot reports from mixed data sources (PDF catalogs, Excel/CSV transactions) across domains (sales, library circulation, academic records). Handles data extraction, cleaning, reconciliation, pivot table creation, and Excel export.
---

# Sales Pivot Report Generation

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

3. **Clean & normalize** - BEFORE joining:
   - Strip whitespace: `df['col'] = df['col'].str.strip()`
   - Normalize case: Title for names, UPPER for codes/IDs
   - Cast join keys to same dtype: `df['PRODUCT_ID'] = df['PRODUCT_ID'].astype(str).str.strip()`
   - Drop duplicates

4. **Validate keys** - Check referential integrity:
   ```python
   unknown = set(trans['PRODUCT_ID']) - set(catalog['PRODUCT_ID'])
   if unknown:
       print(f"Unmatched IDs: {unknown}")
   ```

5. **Join & reconcile** - Merge transactions with catalog. Fill missing values from reference data.

6. **Calculate domain-specific metrics**:
   ```python
   # Sales
   df['REVENUE'] = df['QUANTITY'] * df['UNIT_PRICE']
   df['PROFIT'] = df['QUANTITY'] * (df['UNIT_PRICE'] - df['UNIT_COST'])
   df['MARGIN_PCT'] = df['PROFIT'] / df['REVENUE']
   
   # Library circulation
   df['LOAN_DURATION'] = (df['RETURN_DATE'] - df['LOAN_DATE']).dt.days
   df['DECADE'] = df['PUBLISH_YEAR'].apply(lambda x: f"{int(x//10)*10}s")
   
   # Academic records
   df['GRADE_BAND'] = df['SCORE'].apply(lambda x: 'A' if x>=90 else 'B' if x>=80 else 'C' if x>=70 else 'D')
   ```

7. **Create pivot tables** - Use `pd.pivot_table()`:
   ```python
   pivot = pd.pivot_table(df, values='REVENUE', index='CATEGORY',
                          columns='REGION', aggfunc='sum', fill_value=0)
   ```

8. **Flatten MultiIndex columns** - BEFORE writing to Excel:
   ```python
   if isinstance(df.columns, pd.MultiIndex):
       df.columns = [c[-1] if isinstance(c, tuple) else str(c) for c in df.columns]
   ```

9. **Write multi-sheet Excel**:
   ```python
   with pd.ExcelWriter('report.xlsx', engine='openpyxl') as writer:
       source_data.to_excel(writer, sheet_name='SourceData', index=False)
       pivot.to_excel(writer, sheet_name='PivotSummary', index=False)
   ```

## Verification (MANDATORY)

After completing step 9, invoke the `pytest-verification` skill to run the test suite:

```bash
pytest test_output.py -v
```

The test suite is the ONLY authority on pass/fail. Manual file checks do not count as verification.

## Domain Adaptation

This workflow applies to any domain where a reference catalog (PDF) joins with transactional data (Excel/CSV). Map accordingly:

| Domain | Join Key | Metrics | Pivot Dimensions |
|---|---|---|---|
| Sales | `PRODUCT_ID` | Revenue, Profit, Margin | Category, Region |
| Library Circulation | `BOOK_ID` | Loan Duration, Return Rate | Genre, Borrower Type |
| Academic Records | `STUDENT_ID` | Avg Score, GPA | Department, Semester |

Verify exact join key and sheet names from `test_output.py` before coding.

## Critical Anti-Patterns

### MultiIndex Export Failure
`openpyxl` raises `ValueError` on tuple headers. Always flatten before writing.

### PivotChart Import Error
`from openpyxl.chart import PivotChart` raises ImportError. Use `pd.pivot_table()` instead.

### Whitespace in Join Keys
PDF extraction includes trailing spaces. Always `.str.strip()` before merging.

### Silent Join Mismatches
Mismatched dtypes (str vs int IDs) cause silent row drops. Cast to same type before merge.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

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