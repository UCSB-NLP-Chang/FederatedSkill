---
name: sales-pivot-report
description: Generate multi-sheet Excel pivot reports from mixed data sources (PDF catalogs, Excel/CSV transactions). Handles data extraction, cleaning, reconciliation, pivot table creation, and Excel export with proper validation.
---

# Sales Pivot Report Generation

## When to Use
- Tasks requiring pivot table summaries from transactional data
- Data reconciliation between PDF catalogs and Excel/CSV transactions
- Multi-sheet Excel report generation with category/region breakdowns
- Business analytics outputs with derived financial metrics (REVENUE, PROFIT, MARGIN_PCT)

## Workflow

1. **Inventory data sources** - Identify all input files and their formats
2. **Extract data** - Use appropriate library per format:
   - Excel/CSV: `pandas.read_excel()` or `pandas.read_csv()`
   - PDF tables: `pdfplumber` (preferred over tabula/poppler)
3. **Clean and normalize** - BEFORE joining:
   - Strip whitespace from ALL string columns: `df['col'] = df['col'].str.strip()`
   - Normalize case: Title for names/regions, UPPER for codes/IDs
   - Cast join keys to same dtype (str or int): `df['PRODUCT_ID'] = df['PRODUCT_ID'].astype(int)`
   - Remove duplicates: `df.drop_duplicates()`
4. **Validate** - Check constraints:
   - No null join keys
   - Positive quantities (`QUANTITY > 0`)
   - Referential integrity (all PRODUCT_IDs exist in catalog)
5. **Enrich and reconcile** - Join sources, fill missing values from reference data
6. **Calculate metrics**:
   ```python
   df['REVENUE'] = df['QUANTITY'] * df['UNIT_PRICE']
   df['PROFIT'] = df['QUANTITY'] * (df['UNIT_PRICE'] - df['UNIT_COST'])
   df['MARGIN_PCT'] = df['PROFIT'] / df['REVENUE']
   ```
7. **Create pivot tables** - Use `pd.pivot_table()` with explicit `aggfunc='sum'` and `fill_value=0`
8. **Flatten MultiIndex columns** - CRITICAL before writing to Excel
9. **Write multi-sheet Excel** - Use `pd.ExcelWriter` with `openpyxl` engine
10. **Verify against actual tests** - Run test suite if available; do NOT rely solely on self-validation

## Critical Anti-Patterns

### MultiIndex Export Failure (from R0)
`openpyxl` raises `ValueError: Cannot convert ('A', 'B') to Excel` when writing DataFrames with `pd.MultiIndex` columns.

**Fix**: Flatten columns immediately before writing:
```python
if isinstance(df.columns, pd.MultiIndex):
    df.columns = [c[-1] if isinstance(c, tuple) else str(c) for c in df.columns]
```

### PivotChart Import Error (from R0)
`from openpyxl.chart import PivotChart` raises ImportError - this class does not exist in openpyxl.

**Fix**: Use `pd.pivot_table()` and write the DataFrame directly:
```python
# WRONG
from openpyxl.chart import PivotChart

# CORRECT
pivot = pd.pivot_table(df, values='REVENUE', index='CATEGORY', aggfunc='sum')
pivot.to_excel(writer, sheet_name='PivotSummary')
```

### Silent Join Mismatches (from R0)
Mismatched dtypes (str vs int) or hidden whitespace in join keys cause silent row drops.

**Fix**: Strip whitespace and cast join keys explicitly:
```python
df1['PRODUCT_ID'] = df1['PRODUCT_ID'].astype(str).str.strip()
df2['PRODUCT_ID'] = df2['PRODUCT_ID'].astype(str).str.strip()
```

### Self-Validation Passes But Tests Fail (from R0)
The verifier may have different expectations than what the agent checked.

**Fix**: Always run the actual test suite when available:
```bash
pytest test_output.py -v
```

## Validation Checklist

- [ ] All join keys present and dtype-matched in both sources
- [ ] All string columns stripped of whitespace
- [ ] No null values in critical columns after enrichment
- [ ] Pivot headers are flat strings (not tuples)
- [ ] Sheet names match expected output format
- [ ] Pivot totals match source data sums
- [ ] Run actual test suite if available

## Helper Scripts

See `scripts/build_pivot_report.py` for reusable functions:
- `clean_dataframe()` - Trim, normalize case, drop duplicates
- `validate_keys()` - Check referential integrity
- `create_pivot()` - Create pivot with auto-flatten
- `write_multi_sheet_excel()` - Multi-sheet Excel output

## Known Issues

See `references/common-issues.md` for troubleshooting PDF extraction, encoding, and dtype mismatches.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.
