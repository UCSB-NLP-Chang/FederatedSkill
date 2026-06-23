---
name: excel-report-generation
description: Generate multi-sheet Excel reports from multiple data sources (Excel, PDF, CSV) with pivot tables, calculated columns, and data reconciliation. Use when tasks require combining transaction data with reference catalogs, creating summary sheets with aggregations, or outputting formatted business reports with multiple analytical views. Also use for inventory/warehouse analytics, sales reconciliation, library circulation analysis, student performance reporting, and manufacturing quality control with inspection metrics.
---

# Multi-Source Excel Report Generation

Generate professional Excel reports by joining and transforming data from heterogeneous sources. Handles common friction points like binary file parsing, catalog-transaction reconciliation, multi-sheet pivot output, and missing value edge cases.

## When to Use

- Task requires combining data from Excel + PDF/CSV/other sources
- Output needs multiple sheets with different aggregations (pivot tables)
- Data reconciliation required between transaction records and reference catalogs
- Need calculated columns (revenue, margin, inventory metrics, quality grades, etc.) in final output
- **Inventory/warehouse analytics:** Multi-location stock analysis with reorder logic and value tiering
- **Quality control/manufacturing:** Inspection records joined with part specifications, deviation calculations, pass/fail grading with missing value handling

## Standard Workflow

### 1. Load Source Data

**Excel files:** Do NOT use `Read` tool — it fails on binary files. Use Python:
```python
import pandas as pd
df = pd.read_excel('/path/to/file.xlsx', sheet_name=0)  # or 'SheetName'
```

**PDF tables:** Use `Read` tool to extract text, then parse:
```python
# After reading PDF to text, parse structured data
lines = [l.strip() for l in text.split('\n') if l.strip()]
# Extract rows based on consistent delimiter patterns
```

**CSV/JSON:** Use pandas `read_csv()` / `read_json()` directly.

### 2. Data Quality & Reconciliation

Check these standard issues before joining:

| Check | Method | Action if Failed |
|-------|--------|----------------|
| Whitespace in categorical columns | `df['COL'].str.strip()` | Clean and normalize case |
| Negative/zero quantities | `df[df['QUANTITY'] <= 0]` | Filter or flag |
| Missing PRODUCT_IDs in catalog join | `set(trans['PRODUCT_ID']) - set(catalog['PRODUCT_ID'])` | Report unmatched count |
| Price mismatches (transaction vs catalog) | Compare `UNIT_PRICE` columns | Document reconciliation action |
| Duplicate rows | `df.duplicated().sum()` | Remove or investigate |
| Missing measurement values | `df['MEASUREMENT'].isna().sum()` | Preserve NaN, handle in derived columns |

**Missing value preservation:** When calculating derived columns (deviations, grades, errors), explicitly check for NaN source values and propagate NaN or assign sentinel grades like "N/A". Do not silently fill with zeros.

### 3. Create Calculated Columns

**Standard business metrics:**
- `REVENUE` = `QUANTITY` × `UNIT_PRICE`
- `PROFIT` = `REVENUE` - (`QUANTITY` × `UNIT_COST`)
- `MARGIN_PCT` = `PROFIT` / `REVENUE` (handle divide-by-zero)

**Quality control metrics:**
- `DEVIATION` = `abs(MEASUREMENT - TARGET)` — preserve NaN if measurement missing
- `ERROR_PCT` = `abs(ACTUAL - TARGET) / TARGET` — preserve NaN if actual missing
- `GRADE` = tiered based on deviation thresholds — return "N/A" or NaN for missing inputs

```python
def calculate_grade(deviation):
    """Assign quality grade with missing value handling."""
    if pd.isna(deviation):
        return "N/A"  # Will be read back as NaN by pandas, but Excel stores "N/A"
    elif deviation < 0.5:
        return "A"
    elif deviation < 1.0:
        return "B"
    else:
        return "C"

df['GRADE'] = df['DEVIATION'].apply(calculate_grade)
```

**Inventory/warehouse metrics:** See `references/inventory-calculations.md` for full patterns.

Add audit columns documenting source decisions:
- `PRICE_STATUS`: which price source was used
- `CATALOG_MATCH_STATUS`: join success/failure
- `RECONCILIATION_ACTION`: specific resolution taken

### 4. Generate Pivot Summary Sheets

Use pandas aggregation for each required view:

```python
with pd.ExcelWriter('/path/to/output.xlsx', engine='openpyxl') as writer:
    # Source data (full detail)
    source_df.to_excel(writer, sheet_name='SourceData', index=False)
    
    # Revenue by Category
    rev_by_cat = source_df.groupby('CATEGORY')['REVENUE'].sum().reset_index()
    rev_by_cat.to_excel(writer, sheet_name='Revenue by Category', index=False)
    
    # Units by Region
    units_by_region = source_df.groupby('REGION')['QUANTITY'].sum().reset_index()
    units_by_region.to_excel(writer, sheet_name='Units by Region', index=False)
    
    # Cross-tab (pivot table)
    pivot = source_df.pivot_table(
        values='REVENUE', 
        index='CATEGORY', 
        columns='REGION', 
        aggfunc='sum'
    ).reset_index()
    pivot.to_excel(writer, sheet_name='Category Region Matrix', index=False)
```

**Quality control standard sheets:** SourceData, Fail Rate by Line, Avg Deviation by Line, Inspections by Shift, Line Shift Matrix.

**Inventory-specific sheets:** See `references/inventory-calculations.md` for standard warehouse report structure.

### 5. Verification

Always read back and validate:
```python
xls = pd.ExcelFile('/path/to/output.xlsx')
print(f"Sheets: {xls.sheet_names}")
for sheet in xls.sheet_names:
    df_check = pd.read_excel(xls, sheet_name=sheet)
    print(f"{sheet}: shape {df_check.shape}")

# For quality control: verify missing value handling
source = pd.read_excel(xls, sheet_name='SourceData')
print(f"Missing measurements: {source['MEASUREMENT'].isna().sum()}")
print(f"N/A grades: {(source['GRADE'] == 'N/A').sum()}")
```

**Important:** Pandas reads string "N/A" as NaN. Verify with `openpyxl` directly if exact string preservation matters:
```python
from openpyxl import load_workbook
wb = load_workbook('/path/to/output.xlsx')
ws = wb['SourceData']
# Check actual cell values
```

## Domain-Specific Patterns

### Inventory/Warehouse Reports

When task involves multiple warehouses, stock levels, and product catalogs:

1. **Join pattern:** Inventory records (left) → Product master (right) on SKU/PRODUCT_ID
2. **Enrichment:** Compute TOTAL_VALUE, TOTAL_WEIGHT, VALUE_TIER
3. **Flagging:** REORDER_FLAG when QUANTITY_ON_HAND < REORDER_POINT
4. **Status tiers:** STOCK_STATUS based on quantity thresholds
5. **Standard sheets:** SourceData, Stock by Category, Value by Warehouse, Items by Category, Category-Warehouse Matrix

See `references/inventory-calculations.md` for full implementation.

### Quality Control / Manufacturing Reports

When task involves inspection records, part specifications, and deviation analysis:

1. **Join pattern:** Inspection records (left) → Part specifications (right) on PART_ID/SKU
2. **Enrichment:** Compute DEVIATION, ERROR_PCT, GRADE (with NaN handling)
3. **Aggregation:** Count by line/shift, average deviation, cross-tab matrices
4. **Missing value handling:** Explicit NaN checks before calculations; preserve in output
5. **Standard sheets:** SourceData, Fail Rate by Line, Avg Deviation by Line, Inspections by Shift, Line Shift Matrix

See `references/quality-control-patterns.md` for deviation formulas and grade tier logic.

## Common Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Correct Approach |
|--------------|--------------|------------------|
| Using `Read` tool on `.xlsx` files | Tool rejects binary files | Use `python3 -c "import pandas as pd; ..."` |
| Assuming catalog prices are authoritative | Business rules may prefer transaction prices | Explicitly reconcile and document decision |
| Creating pivot tables with `pd.pivot()` | Only reshapes, doesn't aggregate | Use `pivot_table()` with `aggfunc` |
| Writing DataFrames with default `index=True` | Adds unwanted index column | Always use `index=False` in `to_excel()` |
| Ignoring case/whitespace in joins | Causes missed matches | Normalize: `str.strip().str.title()` before joining |
| Hardcoding VALUE_TIER thresholds | Different datasets need different cutoffs | Use percentile-based tiers (95th/75th) or category-specific rules |
| Missing REORDER_FLAG validation | Silent data quality issues | Verify flag logic against edge cases (zero quantities, missing reorder points) |
| **Silent NaN filling in calculations** | Creates false data (grade C for missing measurement) | Explicit NaN checks: `if pd.isna(x): return "N/A"` or `return np.nan` |
| **Assuming pandas preserves "N/A" strings** | Pandas reads "N/A" as NaN; verifier may fail | Use openpyxl for direct verification if exact strings matter |

## Troubleshooting

**"No module named 'openpyxl'"**
```bash
pip install openpyxl
```

**PDF parsing yields garbled structure**
- Try `PyPDF2` or `pdfplumber` for structured extraction
- Fall back to regex patterns if table formatting is irregular

**Memory error on large Excel files**
- Use `read_excel(..., chunksize=10000)` for processing
- Or convert to CSV first: `pd.read_excel().to_csv()` then process CSV

**Date columns parsed as integers**
- Pass `parse_dates=['DATE_COL']` or use `pd.to_datetime()` after load

**Inventory-specific: VALUE_TIER shows unexpected distribution**
- Check for outliers/extreme values skewing percentiles
- Consider log-scaling or winsorizing before tier assignment
- Verify negative/zero UNIT_VALUEs are filtered first

**Multi-warehouse join produces unexpected record counts**
- Verify SKU uniqueness in product master (should be 1:1 or 1:many, not many:many)
- Check for trailing whitespace in SKU columns before join

**Quality control: GRADE shows wrong distribution or verifier fails**
- Verify NaN handling: `df['MEASUREMENT'].isna().sum()` should match "N/A" count
- Check deviation calculation: `abs(MEASUREMENT - TARGET)` not signed difference
- Confirm grade thresholds align with requirements (verify < vs <=)
- **If verifier expects exact "N/A" strings:** Use `openpyxl.load_workbook()` to check cell values directly, not pandas

**Missing value columns show as NaN when re-reading**
- Expected behavior: pandas interprets "N/A" as NaN
- To verify exact Excel contents: use openpyxl directly
- To force string preservation in pandas: use `keep_default_na=False` on read (but this may cause other issues)

## Scripts

- `scripts/reconcile_prices.py` — Complex price reconciliation logic
- `scripts/calculate_deviation_grades.py` — Quality control deviation and grade calculation with missing value handling

## References

- `references/pandas-excel-patterns.md` — Common pandas Excel operations
- `references/price-reconciliation-schema.md` — Detailed reconciliation decision tree
- `references/inventory-calculations.md` — Inventory metrics, tier logic, and warehouse report patterns
- `references/quality-control-patterns.md` — Deviation formulas, grade tier logic, and inspection report patterns
