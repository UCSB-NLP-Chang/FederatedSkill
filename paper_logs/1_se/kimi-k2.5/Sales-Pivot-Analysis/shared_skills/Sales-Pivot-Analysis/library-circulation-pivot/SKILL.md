---
name: library-circulation-pivot
description: Generate multi-sheet Excel reports from library circulation records joined with catalog data. Handles PDF catalog parsing, date-based enrichment (loan duration, decade, weekday bucketing), and standard circulation analytics by genre, borrower type, and cross-tabulated matrices. Use when tasks require combining circulation transaction data with bibliographic catalogs, computing loan metrics, or analyzing borrowing patterns by material type and patron category.
---

# Library Circulation Pivot Report Generation

Create enriched circulation reports by joining transaction records with catalog data, computing temporal metrics, and generating multi-dimensional summaries.

## When to Use

- Circulation transaction records (loan/return dates) need joining with bibliographic catalog
- Analysis requires date-derived metrics: loan duration, publication decade, weekday/weekend patterns
- Output needs standard library analytics: loans by material type (genre), by patron type, cross-tabulations
- Data sources mix Excel/CSV transactions with PDF catalog exports

## Standard Workflow

### 1. Parse Catalog Data (PDF)

PDF catalogs require text extraction followed by structured parsing:

```python
import re

# After reading PDF to text, identify consistent field delimiters
# Common patterns: fixed-width columns, pipe-delimited, or labeled rows

# Example: extracting BOOK_ID, TITLE, AUTHOR, GENRE, YEAR_PUBLISHED
pattern = r'(\d{4})\s+(.*?)\s+([A-Za-z\s]+)\s+(\d{4})'
matches = re.findall(pattern, pdf_text)

catalog_df = pd.DataFrame(matches, columns=['BOOK_ID', 'TITLE', 'GENRE', 'YEAR_PUBLISHED'])
catalog_df['YEAR_PUBLISHED'] = catalog_df['YEAR_PUBLISHED'].astype(int)
```

**Parsing strategies when structure varies:**
- Look for repeating header patterns to identify row boundaries
- Extract year from parentheses or "Published: YYYY" labels
- Normalize genre strings: `str.strip().str.title()`

### 2. Load Circulation Records

```python
# Excel/CSV circulation data
circ = pd.read_excel('/path/to/circulation.xlsx')
# Expected columns: LOAN_ID, BOOK_ID, BORROWER_TYPE, LOAN_DATE, RETURN_DATE
```

### 3. Data Quality & Reconciliation

| Check | Method | Failure Action |
|-------|--------|----------------|
| Invalid BOOK_IDs (not in catalog) | `set(circ['BOOK_ID']) - set(catalog['BOOK_ID'])` | Filter out or report count |
| Missing/invalid dates | `circ[['LOAN_DATE', 'RETURN_DATE']].isna().sum()` | Remove rows with null dates |
| Return date ≤ loan date | `circ[circ['RETURN_DATE'] <= circ['LOAN_DATE']]` | Remove impossible durations |
| Duplicate loan records | `circ.duplicated().sum()` | Remove with `drop_duplicates()` |

```python
# Date parsing (handle multiple formats)
circ['LOAN_DATE'] = pd.to_datetime(circ['LOAN_DATE'], errors='coerce')
circ['RETURN_DATE'] = pd.to_datetime(circ['RETURN_DATE'], errors='coerce')

# Filter invalid records
circ = circ[circ['LOAN_DATE'].notna() & circ['RETURN_DATE'].notna()]
circ = circ[circ['RETURN_DATE'] > circ['LOAN_DATE']]
```

### 4. Enrich with Calculated Columns

```python
# Core circulation metrics
df['LOAN_DURATION'] = (df['RETURN_DATE'] - df['LOAN_DATE']).dt.days

# Temporal bucketing
df['DECADE'] = (df['YEAR_PUBLISHED'] // 10 * 10).astype(str) + 's'
df['WEEKDAY_BUCKET'] = df['LOAN_DATE'].dt.weekday.apply(
    lambda x: 'weekend' if x >= 5 else 'weekday'
)
df['RETURN_STATUS'] = 'returned'  # or computed from null return dates if applicable
```

### 5. Join Datasets

```python
# Left join: circulation records enriched with catalog data
merged = circ.merge(catalog_df, on='BOOK_ID', how='left')

# Verify join coverage
unmatched = merged[merged['GENRE'].isna()]['BOOK_ID'].nunique()
print(f"Unmatched catalog entries: {unmatched}")
```

### 6. Generate Pivot Summary Sheets

```python
with pd.ExcelWriter('/path/to/output.xlsx', engine='openpyxl') as writer:
    # Full detail with enriched data
    merged.to_excel(writer, sheet_name='SourceData', index=False)
    
    # Loans by Genre
    loans_by_genre = merged.groupby('GENRE').size().reset_index(name='Count')
    loans_by_genre.sort_values('Count', ascending=False, inplace=True)
    loans_by_genre.to_excel(writer, sheet_name='Loans by Genre', index=False)
    
    # Average Duration by Genre
    avg_dur = merged.groupby('GENRE')['LOAN_DURATION'].mean().round(2)
    avg_dur = avg_dur.reset_index(name='Average_LOAN_DURATION')
    avg_dur.sort_values('Average_LOAN_DURATION', ascending=False, inplace=True)
    avg_dur.to_excel(writer, sheet_name='Avg Duration by Genre', index=False)
    
    # Loans by Borrower Type
    by_borrower = merged.groupby('BORROWER_TYPE').size().reset_index(name='Count')
    by_borrower.sort_values('Count', ascending=False, inplace=True)
    by_borrower.to_excel(writer, sheet_name='Loans by Borrower Type', index=False)
    
    # Cross-tab: Genre × Borrower Type
    matrix = merged.pivot_table(
        values='LOAN_ID',
        index='GENRE',
        columns='BORROWER_TYPE',
        aggfunc='count',
        fill_value=0
    ).reset_index()
    matrix.to_excel(writer, sheet_name='Genre Borrower Matrix', index=False)
```

### 7. Verification

```python
xls = pd.ExcelFile('/path/to/output.xlsx')
print(f"Sheets: {xls.sheet_names}")

# Verify expected sheets exist
expected = ['SourceData', 'Loans by Genre', 'Avg Duration by Genre',
            'Loans by Borrower Type', 'Genre Borrower Matrix']
missing = [s for s in expected if s not in xls.sheet_names]
assert not missing, f"Missing sheets: {missing}"

# Verify SourceData has enriched columns
source = pd.read_excel(xls, sheet_name='SourceData')
required = ['LOAN_DURATION', 'DECADE', 'WEEKDAY_BUCKET']
missing_cols = [c for c in required if c not in source.columns]
assert not missing_cols, f"Missing enriched columns: {missing_cols}"

# Spot-check aggregations match
loans_check = source.groupby('GENRE').size()
loans_sheet = pd.read_excel(xls, sheet_name='Loans by Genre')
assert loans_check.sum() == loans_sheet['Count'].sum(), "Aggregation mismatch"
```

## Common Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
|--------------|--------------|------------------|
| Using `Read` tool on .xlsx files | Binary file rejection | Use `pd.read_excel()` via Python |
| Treating dates as strings | Cannot calculate durations | `pd.to_datetime()` with `errors='coerce'` |
| Integer division for decades | Wrong decade assignment | `(YEAR // 10 * 10).astype(str) + 's'` |
| `weekday` property without mapping | 0=Monday, 6=Sunday, 5-6=weekend | Explicit map or `dt.dayofweek >= 5` |
| Default `index=True` in `to_excel()` | Adds unwanted index column | Always use `index=False` |
| Assuming all BOOK_IDs match catalog | Silent data loss | Verify unmatched count post-join |

## Troubleshooting

**PDF catalog yields garbled or unstructured text**
- Try `pdfplumber` for table extraction
- Use regex on extracted text with flexible whitespace patterns
- Check for multi-column layouts that confuse line-based extraction

**Date parsing failures**
- Specify format explicitly: `pd.to_datetime(..., format='%Y-%m-%d')`
- Handle mixed formats: try format=None first, then specific formats

**Verifier test failures**
- Check exact sheet names match expected (case-sensitive)
- Verify column names in pivot tables match expected schema
- Confirm aggregation functions (count vs sum) match requirements
- Review numeric rounding: use `.round(2)` for averages

**Memory errors on large circulation datasets**
- Use `usecols` to load only needed columns
- Process in chunks if >100k records, though rare for typical library data

## References

- `references/circulation-metrics.md` — Detailed formulas for loan duration, renewal rates, turnover calculations
- `references/pdf-catalog-patterns.md` — Regex patterns for common library system PDF exports
