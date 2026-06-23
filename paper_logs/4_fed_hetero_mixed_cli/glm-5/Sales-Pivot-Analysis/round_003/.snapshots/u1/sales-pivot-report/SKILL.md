---
name: sales-pivot-report
description: Generate multi-sheet Excel pivot reports from mixed data sources (PDF catalogs, Excel/CSV transactions). Handles data extraction, cleaning, reconciliation, pivot table creation, and Excel export. Use for any task requiring pivot table summaries, data reconciliation between sources, or multi-sheet Excel report generation.
---

# Sales Pivot Report Generation

## When to Use

- Tasks requiring pivot table summaries from transactional data
- Data reconciliation between PDF catalogs and Excel/CSV transactions
- Multi-sheet Excel report generation with category/region breakdowns
- Business analytics outputs with derived financial metrics

## Workflow

1. **Inventory sources** - Identify all input files (PDF, XLSX, CSV) and their formats.
2. **Extract PDF tables** - Use `pdfplumber` for tabular data:
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
   **Fallback**: If `extract_table()` returns `None` or misaligned columns, use `page.extract_text()` and parse lines using known domain keywords (e.g., genre lists, department names).
3. **Clean & normalize** - BEFORE joining:
   - Strip whitespace: `df['col'] = df['col'].str.strip()`
   - Normalize case: Title for names/regions, UPPER for codes
   - Cast join keys to same dtype: `df['PRODUCT_ID'] = df['PRODUCT_ID'].astype(int)`
   - Drop duplicates
4. **Validate keys** - Check referential integrity:
   ```python
   unknown = set(trans['PRODUCT_ID']) - set(catalog['PRODUCT_ID'])
   if unknown:
       print(f"Unmatched PRODUCT_IDs: {unknown}")
   ```
5. **Join & reconcile** - Merge transactions with catalog. Fill missing prices from catalog. Remove rows with invalid keys.
6. **Calculate metrics**:
   ```python
   df['REVENUE'] = df['QUANTITY'] * df['UNIT_PRICE']
   df['PROFIT'] = df['QUANTITY'] * (df['UNIT_PRICE'] - df['UNIT_COST'])
   df['MARGIN_PCT'] = df['PROFIT'] / df['REVENUE']
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

## After Generating the Report

**INVOKE the `run-pytest-verification` skill to run tests and verify output.**

Do NOT declare success or write DONE.txt until the verification skill confirms all tests pass.

## Domain Adaptation

This workflow applies to any domain where a reference catalog (PDF) is joined with transactional/record data (Excel/CSV). Map invariants accordingly:

| Domain | Join Key | Typical Metrics | Typical Pivot Dimensions |
|--------|----------|-----------------|--------------------------|
| Sales | `PRODUCT_ID` | Revenue, Profit, Margin | Category, Region, Quarter |
| Library Circulation | `BOOK_ID` | Loan Count, Avg Duration, Return Rate | Genre, Borrower Type, Weekday |
| Academic Records | `STUDENT_ID` | Avg Score, Credits, GPA | Department, Semester, Grade Band |

**Rule**: Always verify the exact join key name and expected sheet names from the test file (`test_output.py`) before writing code. Do not assume sales-specific names.

## Known invariants (by sub-task)

### pdf-catalog-transaction-merge
- Join key is `PRODUCT_ID` (case-sensitive)
- Expected sheets: `SourceData` + `PivotSummary`
- Pivot headers must be flat strings, not tuples

### student-performance-pivot
- Join key is `STUDENT_ID`
- Expected sheets: `Avg Score by Department`, `Students by Department`, `Credits by Semester`, `Department Semester Matrix`, `SourceData`
- Derived columns: `GRADE_BAND`, `WEIGHTED_SCORE`, `TERM_STATUS`, `RETAKE_FLAG`

### library-circulation-pivot
- Join key is `BOOK_ID` (case-sensitive)
- Expected sheets: `Loans by Genre`, `Avg Duration by Genre`, `Loans by Borrower Type`, `Genre Borrower Matrix`, `SourceData`
- Derived columns: `LOAN_DURATION`, `DECADE`, `RETURN_STATUS`, `WEEKDAY_BUCKET`
- Source: PDF book catalog + Excel circulation records
- Validation: `RETURN_DATE > LOAN_DATE` for all records

## Critical Anti-Patterns

### MultiIndex Export Failure
`openpyxl` raises `ValueError` on tuple headers. Always flatten before writing:
```python
if isinstance(df.columns, pd.MultiIndex):
    df.columns = [c[-1] if isinstance(c, tuple) else str(c) for c in df.columns]
```

### PivotChart Import Error
`from openpyxl.chart import PivotChart` raises ImportError—this class does not exist. Use `pd.pivot_table()` instead.

### Whitespace in Join Keys
PDF extraction often includes trailing spaces. Always `.str.strip()` before merging.

### Silent Join Mismatches
Mismatched dtypes (str vs int IDs) cause silent row drops. Cast to same type before merge.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Helper Scripts

See `scripts/build_pivot_report.py` for reusable functions:
- `clean_dataframe()` - Trim, normalize case, drop duplicates
- `validate_keys()` - Check referential integrity
- `create_pivot()` - Create pivot with auto-flatten
- `write_multi_sheet_excel()` - Multi-sheet Excel output

## Known Issues

See `references/common-issues.md` for troubleshooting PDF extraction, encoding, and dtype mismatches.
