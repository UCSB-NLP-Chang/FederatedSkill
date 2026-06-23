---
name: sales-pivot-report
description: Generate multi-sheet Excel pivot reports from mixed data sources (PDF catalogs, Excel/CSV transactions, library circulation records, student data). Use when extracting tables from PDFs, joining transaction data with catalogs, computing derived metrics, or creating pivot summaries.
---

# Multi-Domain Pivot Report Generation

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
   **Fallback**: If `extract_table()` returns `None` or misaligned columns, use `page.extract_text()` and parse lines using known domain keywords.
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
6. **Calculate domain-specific metrics**:
   - Sales: `REVENUE = QUANTITY * UNIT_PRICE`, `PROFIT`, `MARGIN_PCT`
   - Library: `LOAN_DURATION`, `DECADE`, `RETURN_STATUS`, `WEEKDAY_BUCKET`
   - Academic: `GRADE_BAND`, `WEIGHTED_SCORE`, `TERM_STATUS`, `RETAKE_FLAG`
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

---

## GATE: pytest verification (Step 10)

**Run this command and check its output:**

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

## Critical Anti-Patterns

### Manual Verification Trap (CRITICAL)
Checking file existence, row counts, or printing dataframes is NOT verification. Only pytest determines pass/fail.

### MultiIndex Export Failure
`openpyxl` raises `ValueError` on tuple headers. Always flatten before writing.

### PivotChart Import Error
`from openpyxl.chart import PivotChart` raises ImportError. Use `pd.pivot_table()`.

### Whitespace in Join Keys
PDF extraction includes trailing spaces. Always `.str.strip()` before merge.

### Silent Join Mismatches
Mismatched dtypes (str vs int) cause silent row drops. Cast before merge.

---

## Domain Adaptation

| Domain | Join Key | Typical Metrics | Typical Pivot Dimensions |
|---|---|---|---|
| Sales | `PRODUCT_ID` | Revenue, Profit, Margin | Category, Region, Quarter |
| Library Circulation | `BOOK_ID` | Loan Count, Avg Duration, Return Rate | Genre, Borrower Type, Weekday |
| Academic Records | `STUDENT_ID` | Avg Score, Credits, GPA | Department, Semester, Grade Band |

Always verify exact join key name and expected sheet names from `test_output.py`.

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
- Join key is `PRODUCT_ID` (case-sensitive)
- Expected sheets: `SourceData` + `PivotSummary`
- Pivot headers must be flat strings, not tuples
- No orphaned PRODUCT_IDs, no duplicate rows

### library-circulation-pivot
- Join key is `BOOK_ID` (case-sensitive)
- Expected sheets: `Loans by Genre`, `Avg Duration by Genre`, `Loans by Borrower Type`, `Genre Borrower Matrix`, `SourceData`
- Derived columns: `LOAN_DURATION`, `DECADE`, `RETURN_STATUS`, `WEEKDAY_BUCKET`
- Source: PDF book catalog + Excel circulation records
- Validation: `RETURN_DATE > LOAN_DATE` for all records

### student-performance-pivot
- Join key is `STUDENT_ID`
- Expected sheets: `Avg Score by Department`, `Students by Department`, `Credits by Semester`, `Department Semester Matrix`, `SourceData`
- Derived columns: `GRADE_BAND`, `WEIGHTED_SCORE`, `TERM_STATUS`, `RETAKE_FLAG`

---

## Helper Scripts

See `scripts/build_pivot_report.py` for reusable functions:
- `clean_dataframe()` - Trim, normalize case, drop duplicates
- `validate_keys()` - Check referential integrity
- `create_pivot()` - Create pivot with auto-flatten
- `write_multi_sheet_excel()` - Multi-sheet Excel output

---

## Troubleshooting

See `references/common-issues.md` for PDF extraction, encoding, and dtype issues.