---
name: sales-pivot-report
description: Build multi-sheet Excel pivot reports from mixed data sources (PDF catalogs, Excel/CSV transactions). Use when tasks require data extraction from PDFs, joining multiple datasets, calculating financial metrics, and generating pivot summaries.
---

# Sales Pivot Report Generation

Generate multi-sheet Excel reports from PDF catalogs and transaction data with pivot table summaries.

## Workflow

1. **Inventory data sources** - Identify all input files and their formats (PDF, XLSX, CSV)
2. **Extract PDF tables** - Use `pdfplumber` for tabular data extraction:
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
3. **Clean and normalize** - Strip whitespace, normalize case, convert types:
   ```python
   for col in df.select_dtypes(include='object').columns:
       df[col] = df[col].str.strip()
   df['REGION'] = df['REGION'].str.title()
   df['PRODUCT_ID'] = pd.to_numeric(df['PRODUCT_ID'])
   ```
4. **Validate keys** - Check referential integrity before joining:
   ```python
   unknown = set(trans['PRODUCT_ID']) - set(catalog['PRODUCT_ID'])
   if unknown:
       print(f"Unknown product IDs: {unknown}")
   ```
5. **Join and enrich** - Merge transactions with catalog, fill missing prices
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
8. **Write multi-sheet Excel**:
   ```python
   with pd.ExcelWriter('report.xlsx', engine='openpyxl') as writer:
       df.to_excel(writer, sheet_name='SourceData', index=False)
       pivot.to_excel(writer, sheet_name='PivotSummary', index=False)
   ```
9. **Run actual tests** - Execute provided test suite if available (e.g., `pytest test_output.py`)

## Critical Anti-Patterns

### DO NOT import PivotChart
`from openpyxl.chart import PivotChart` raises ImportError - this class does not exist. Use `pd.pivot_table()` instead.

### DO NOT write MultiIndex columns directly
`openpyxl` raises `ValueError: Cannot convert ('A', 'B') to Excel` for tuple headers. Flatten before writing:
```python
if isinstance(df.columns, pd.MultiIndex):
    df.columns = [c[-1] if isinstance(c, tuple) else str(c) for c in df.columns]
```

### DO NOT skip whitespace cleaning
PDF extraction often includes trailing spaces that break joins. Always `.str.strip()` before merging.

### DO NOT trust self-validation
Self-validation can pass while tests fail. Run the actual test suite when provided.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### B1: PDF Catalog + Transaction Pivot Report
- Join key is `PRODUCT_ID` (may be str or int - cast both sides to same type)
- Output sheets must be named exactly: `SourceData`, `PivotSummary`
- Pivot headers must be flat strings, not MultiIndex tuples
- No orphaned PRODUCT_IDs, no duplicate rows

## Troubleshooting

See [references/common-issues.md](references/common-issues.md) for extraction failures, encoding issues, and data type mismatches.
