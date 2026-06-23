---
name: sec-13f-analysis
description: Parse and analyze SEC Form 13F quarterly filings (COVERPAGE.tsv and INFOTABLE.tsv) to extract manager info, AUM, stock holdings, top CUSIPs, and class breakdowns. Use when tasks involve fund manager lookups, holdings extraction, stock classification, AUM calculations, CUSIP analysis, or aggregating holdings by security class from 13F TSV datasets.
---

# SEC 13F Filing Analysis

## Quick Decision Tree

1. **Task asks for 'class breakdown', 'top classes', or 'stock classes'** → Use [Class Breakdown Workflow](#class-breakdown-workflow)
2. **Task asks for 'top holdings', 'top CUSIPs', or 'holdings list'** → Use [Standard Holdings Workflow](#standard-holdings-workflow)
3. **Manager name not found** → Try [Word-Overlap Matching](#manager-name-matching) before declaring null

## Standard Holdings Workflow

1. **Verify Column Positions**: Before extracting any column, run `head -1 <file>.tsv | tr '\t' '\n' | nl` to see column names with positions. Do NOT assume column numbers.
2. **Locate Data**: Find `COVERPAGE.tsv` and `INFOTABLE.tsv` in the target quarter directory (e.g., `2025-q3/`).
3. **Filter by Quarter**: Use `REPORTCALENDARORQUARTER` column in COVERPAGE to isolate filings for the requested period (e.g., `30-SEP-2025`).
4. **Match Manager** (apply in order, stop at first confident match):
   - **Exact match**: Normalize both names, compare for equality.
   - **Substring match**: Query is substring of manager name or vice versa.
   - **Word-level match**: Any word from the normalized query appears as a complete word in the normalized manager name (or vice versa). Example: query "elliott associates" matches "jvl associates llc" via shared word "associates".
   - **Fuzzy match**: Only accept if similarity ratio > 0.85.
   - **If no confident match exists after all steps**, return `manager: null` — do NOT force the closest Levenshtein match.
5. **Extract Holdings**: Join on `ACCESSION_NUMBER` to get all holdings from INFOTABLE.
6. **Classify Stocks**: Use tokenized matching (see Stock Classification section below).
7. **Calculate Metrics**:
   - `Total AUM`: Sum `VALUE` for all holdings.
   - `Stock AUM`: Sum `VALUE` for stock-classified holdings.
   - `Stock Holdings Count`: Count of stock-classified rows.
   - `Top N CUSIPs`: Sort stock holdings by `VALUE` descending, take top N.
8. **Output**: Write JSON with schema `{manager, total_aum, stock_aum, stock_holdings_count, top_cusips}`. If no match, `manager: null` and numeric fields `null`.

## Class Breakdown Workflow

Use when the task asks for "class breakdown", "top stock classes", "breakdown by security class", or output fields include `top_class_labels`/`top_class_counts`.

1. **Verify Column Positions**: Run `head -1 <file>.tsv | tr '\t' '\n' | nl` first.
2. **Match Manager** as in standard workflow (steps 2-4).
3. **If no match**: Return `manager: null`, `aum_total: null`, `top_class_labels: []`, `top_class_counts: []`.
4. **Filter to Stock Holdings**: Keep only rows where `is_stock_like(TITLEOFCLASS)` is true.
5. **Aggregate by Class**: Group by `TITLEOFCLASS`.
   - `stock_row_count`: Total count of stock rows.
   - `stock_cusip_count`: Count of unique `CUSIP` values in stock rows.
   - For each class: count of rows and sum of `VALUE`.
6. **Select Top N**: Sort classes by count (descending), take top N (typically 3).
7. **Output Schema**:
   ```json
   {
     "manager": "FILINGMANAGER_NAME",
     "aum_total": 12345678.0,
     "stock_row_count": 45,
     "stock_cusip_count": 40,
     "top_class_labels": ["COM", "CLASS A", "SHS"],
     "top_class_counts": [20, 15, 10]
   }
   ```

## Manager Name Matching

**Do NOT use naive Levenshtein distance alone.** It produces false positives (e.g., "Headlands Technologies" matched to "Renaissance Technologies").

### Normalization
Lowercase, strip punctuation, remove suffixes (`LLC`, `INC`, `LTD`, `CORP`, `LP`, `CO`, `ADVISORY`, `MANAGEMENT`, `GROUP`, `PARTNERS`).

### Matching priority (stop at first success):
1. **Exact normalized match**: `norm(query) == norm(candidate)`
2. **Substring match**: `norm(query) in norm(candidate)` OR `norm(candidate) in norm(query)`
3. **Word overlap**: Significant word intersection (e.g., "associates" matches "jvl associates llc"). Exclude stop words: `the`, `and`, `of`, `associates`, `group`, `capital`, `partners`, `management`.
4. **Fuzzy**: Only if similarity > 0.85 AND no false positive risk.

### No match handling
If steps 1-4 fail, return `manager: null`. Do NOT force a match. Do NOT return zeros for AUM — return `null` or omit the field.

## Stock Classification

TITLEOFCLASS values use many abbreviations. Use **tokenized matching** to avoid substring traps.

### Stock indicators (include):
- `COMMON`, `COM` → common stock
- `ORDINARY`, `SHARES`, `SHS` → ordinary shares
- `STOCK` → stock
- `CLASS A`, `CLASS B`, `CL A`, `CL B` → class shares

### Exclude non-stock types:
- `PUT`, `CALL`, `OPTION` → options
- `ETF`, `EXCHANGE TRADED FUND` → ETFs
- `ADR`, `ADS` → depositary receipts
- `NOTE`, `BOND`, `DEBT` → fixed income
- `PFD`, `PREFERRED`, `PRF` → preferred stock
- `TRUST`, `FUND`, `INDEX` → funds

### Classification algorithm:
```python
tokens = title.lower().split()
include = {'common', 'com', 'ordinary', 'shares', 'shs', 'stock', 'class', 'cl'}
exclude = {'etf', 'put', 'call', 'option', 'bond', 'note', 'preferred', 'pfd', 'adr', 'trust', 'fund', 'index'}
has_include = any(t in include for t in tokens)
has_exclude = any(t in exclude for t in tokens)
is_stock = has_include and not has_exclude
```

**Anti-pattern**: `ISHARES` contains "share" as substring but tokenizes to `['ishares']` — correctly excluded.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (JSON, Excel, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: Write the raw float value directly
- The verifier's tolerance decides acceptable precision; the skill's job is full precision.

## Data Type Handling

- `VALUE` and `SSHPRNAMT` may be floats (e.g., `3620781.0`) — convert to int after parsing if needed.
- `CUSIP` is alphanumeric and may include leading zeros — preserve as string.
- Accession numbers follow format: `XXXXXXXX-XX-XXXXXX`

## Known Invariants (by sub-task)

### B1: SEC 13F Manager Lookup + Holdings
- Levenshtein distance > 10 between normalized names usually means no match — do not force it.
- If `stock_holdings_count` is 0, check for unhandled TITLEOFCLASS abbreviations.
- `COM` alone means Common Stock (include it), but `COM` within a brand name needs context.
- Word-level matching bridges the gap between substring and fuzzy matching — do NOT skip it.

### B2: SEC 13F Class Breakdown
- Output fields differ from B1: `aum_total`, `stock_row_count`, `stock_cusip_count`, `top_class_labels`, `top_class_counts`.
- Aggregate by `TITLEOFCLASS`, sort by count descending.

## Anti-Patterns

- Do NOT assume closest Levenshtein match is correct — "Headlands" to "Renaissance" is a known false positive.
- Do NOT exclude `COM`, `CL A`, `SHS` as stock types — these are valid abbreviations.
- Do NOT assume `VALUE` is always integer-formatted — handle floats.
- Do NOT use substring matching for stock classification — use tokenized matching.
- Do NOT assume column positions — verify with `head -1 file.tsv | tr '\t' '\n' | nl` before extracting.
- Do NOT return zeros when manager not found — return `null` for manager and numeric fields.
- Do NOT skip word-level matching — many tasks expect resolution via shared words.

## Scripts

- Run `python3 scripts/process_13f.py <data_dir> <manager_name> <quarter_date> [--analysis-type {holdings|class_breakdown}]` for a deterministic pipeline.

## References

- `references/13f_schema.md`: TSV column schemas and data formats.
- `references/matching_strategies.md`: Detailed manager matching strategies and word-level matching examples.
- `references/output-schemas.md`: Detailed JSON schemas for different analysis types.
