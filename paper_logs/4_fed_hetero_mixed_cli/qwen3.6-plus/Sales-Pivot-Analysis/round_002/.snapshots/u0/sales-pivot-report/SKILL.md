---
name: sales-pivot-report
description: Generate multi-sheet Excel pivot reports from mixed data sources (PDF catalogs, Excel/CSV transactions). Handles data extraction, cleaning, reconciliation, pivot table creation, and Excel export with proper validation.
---

# Sales Pivot Report Generation

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

---

## STOP: MANDATORY TEST EXECUTION

**DO NOT proceed to DONE.txt until this step passes.**

```bash
pytest test_output.py -v
```

- **If tests pass**: Task is complete. You may write DONE.txt.
- **If tests fail**: STOP. Read the failure output. Identify the issue. Fix. Re-run. Repeat until tests pass.

**Self-validation (checking sheets manually, row counts, openpyxl inspection) is NEVER sufficient.** Only the test suite determines pass/fail. Agents repeatedly declare success after manual checks while tests fail.

---

## Test Failure Troubleshooting

When `pytest test_output.py` fails, diagnose by:

1. **Sheet name mismatch** → Check exact spelling/casing in test expectations vs your `sheet_name=` arguments.
2. **Column name mismatch** → Verify header names match test expectations exactly (case-sensitive, no extra spaces).
3. **Numeric precision mismatch** → Ensure you did NOT round/format values. Pass raw floats.
4. **Missing sheet** → Verify all required sheets are written in the `ExcelWriter` block.
5. **Wrong aggregation** → Check `aggfunc` in `pd.pivot_table()` matches test expectations (sum vs mean vs count).
6. **Row count mismatch** → Re-check join logic, whitespace stripping, and dtype casting.

Fix, re-run, re-test. Do not declare success until pytest shows all tests passing.

## Critical Anti-Patterns

### Self-Validation Trap (CRITICAL)
**CRITICAL**: Manual checks pass but verifier fails. This is the #1 failure mode.

**MANDATORY**: Run `pytest test_output.py -v`. Do NOT skip. Do NOT rely on manual inspection.

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

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### pdf-catalog-transaction-merge
- Join key is `PRODUCT_ID` (case-sensitive)
- Expected sheets: `SourceData` + `PivotSummary`
- Pivot headers must be flat strings, not tuples

### student-performance-pivot
- Join key is `STUDENT_ID`
- Expected sheets: `Avg Score by Department`, `Students by Department`, `Credits by Semester`, `Department Semester Matrix`, `SourceData`
- Derived columns: `GRADE_BAND`, `WEIGHTED_SCORE`, `TERM_STATUS`, `RETAKE_FLAG`
