---
name: sales-pivot-report
description: Generate multi-sheet Excel pivot reports from mixed data sources (PDF catalogs, Excel/CSV transactions). Use when extracting tables from PDFs, joining transaction data with catalogs, computing financial metrics, or creating pivot summaries by category/region.
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

## STOP: MANDATORY VERIFICATION (Step 10)

**DO NOT declare success or write DONE.txt until tests pass.**

```bash
pytest test_output.py -v
```

- **If tests pass**: Task is complete.
- **If tests fail**: DO NOT claim success. Follow the troubleshooting guide below, fix the issue, re-run the script, and re-test.

### Test Failure Troubleshooting

| Failure type | What to check |
|--------------|---------------|
| Sheet name mismatch | Exact spelling/casing in `sheet_name=` arguments |
| Column name mismatch | Header names match test expectations (case-sensitive, no extra spaces) |
| Numeric precision mismatch | You did NOT round/format values. Pass raw floats. |
| Missing sheet | All required sheets written in `ExcelWriter` block |
| Wrong aggregation | `aggfunc` in `pd.pivot_table()` matches test expectations |
| Row count mismatch | Re-check join logic, whitespace stripping, dtype casting |

Fix the identified issue, re-run your script, then re-run `pytest` until all tests pass.

---

## Critical Anti-Patterns

- **Self-validation trap**: Manually checking sheet names/row counts does NOT replace running the test suite. Agents frequently declare success after manual checks while the verifier fails. **Always run `pytest test_output.py` first.**
- **MultiIndex export failure**: `openpyxl` raises `ValueError` on tuple headers. Always flatten before writing.
- **PivotChart import error**: `from openpyxl.chart import PivotChart` raises ImportError—this class does not exist. Use `pd.pivot_table()` instead.
- **Whitespace in join keys**: PDF extraction often includes trailing spaces. Always `.str.strip()` before merging.
- **Silent join mismatches**: Mismatched dtypes (str vs int IDs) cause silent row drops. Cast to same type before merge.

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
- No orphaned PRODUCT_IDs, no duplicate rows

## Verification Checklist

- [ ] All join keys present and cast to same dtype
- [ ] Whitespace stripped from all string columns
- [ ] MultiIndex columns flattened before Excel write
- [ ] Pivot totals match source data sums
- [ ] All expected sheets exist with correct names
- [ ] **pytest test_output.py passes** (mandatory, not optional)

## Helper Scripts

See `scripts/build_pivot_report.py` for reusable functions:
- `clean_dataframe()` - Trim, normalize case, drop duplicates
- `validate_keys()` - Check referential integrity
- `create_pivot()` - Create pivot with auto-flatten
- `write_multi_sheet_excel()` - Multi-sheet Excel output

## Troubleshooting

See `references/common-issues.md` for extraction failures, encoding issues, and data type mismatches.
