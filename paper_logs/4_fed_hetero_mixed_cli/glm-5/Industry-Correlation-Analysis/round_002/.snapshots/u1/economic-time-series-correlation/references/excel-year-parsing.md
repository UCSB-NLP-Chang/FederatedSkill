# Parsing Year Markers from Economic Statistical Tables

Common formatting patterns found in BEA, Census Bureau, and Federal Reserve Excel releases.

## Trailing Dots

Published tables often format years with trailing dots to indicate annual data:
- Pattern: `'1994.'`, `'1995.'`, `'2024.'`
- Cause: Typesetting convention in statistical publications
- Solution:
  ```python
  # Method 1: Strip character
  df['Year'] = df['Year'].astype(str).str.rstrip('.').astype(int)

  # Method 2: Float conversion (robust to dots)
  df['Year'] = df['Year'].astype(str).astype(float).astype(int)
  ```

## Mixed Annual and Quarterly Markers

Recent years often include quarterly breakdowns in annual tables:
- Prefixed: `'2025:I'`, `'2025:II'`, `'2025:III'`, `'2025:IV'`
- Roman continuation: `'I'`, `'II'`, `'III'` (in rows immediately following annual year)
- Prefixed Q: `'2025-Q1'`, `'2025-Q2'`

**Detection**: Check for non-numeric characters after stripping dots:
```python
mask = df['Year'].astype(str).str.contains(r'[:\-IVQ]', regex=True, na=False)
```

**Handling**:
1. Separate annual rows (parseable as integers) from quarterly rows
2. For prefixed quarters: extract year and quarter, groupby year, mean()
3. For continuation rows: forward-fill year from above, then groupby year

Example implementation:
```python
def parse_year_marker(val, last_year=None):
    s = str(val).strip()

    # Handle '2025:I' format
    if ':' in s:
        year, q = s.split(':')
        return int(year), q  # Return quarter for aggregation

    # Handle standalone Roman numerals (continuation)
    if s in ['I', 'II', 'III', 'IV']:
        return last_year, s

    # Handle trailing dots
    if '.' in s:
        return int(float(s)), None

    # Standard year
    return int(s), None
```

## Fiscal Year Notation

Some tables use fiscal year markers:
- Pattern: `'FY1994'`, `'1994/95'`, `'1994-95'`
- Solution: Extract first 4-digit sequence:
  ```python
  df['Year'] = df['Year'].str.extract(r'(\d{4})').astype(int)
  ```

## Verification Checklist

Before analysis:
- [ ] Print `df['Year'].unique()` to spot non-numeric markers
- [ ] Verify year range continuity (no gaps)
- [ ] Confirm latest year handling (partial year quarters averaged or excluded consistently)
- [ ] Check for duplicate years post-parsing