---
name: sec-13f-analysis
description: Parse and analyze SEC Form 13F quarterly filings data (COVERPAGE.tsv and INFOTABLE.tsv). Use when tasks involve fund manager lookups, holdings extraction, stock classification, AUM calculations, or CUSIP analysis from 13F TSV datasets.
---

# SEC 13F Filing Analysis

## Workflow

1. **Locate Data**: Find `COVERPAGE.tsv` and `INFOTABLE.tsv` in the target quarter directory (e.g., `2025-q3/`).
2. **Filter by Quarter**: Use `REPORTCALENDARORQUARTER` column in COVERPAGE to isolate filings for the requested period (e.g., `30-SEP-2025`).
3. **Match Manager**:
   - Normalize names: lowercase, remove punctuation, strip legal suffixes (`LLC`, `INC`, `LTD`, `CORP`, `LP`).
   - Prefer exact or case-insensitive substring match first.
   - Use fuzzy matching only with high threshold (similarity > 0.85 OR distance < 3).
   - **If no confident match exists, report `null` or "not found" — do not force closest match.**
4. **Extract Holdings**: Join on `ACCESSION_NUMBER` to get all holdings from INFOTABLE.
5. **Classify Stocks**: Use tokenized matching (see Stock Classification section below).
6. **Calculate Metrics**:
   - `Total AUM`: Sum `VALUE` for all holdings.
   - `Stock AUM`: Sum `VALUE` for stock-classified holdings.
   - `Stock Holdings Count`: Count of stock-classified rows.
   - `Top N CUSIPs`: Sort stock holdings by `VALUE` descending, take top N.
7. **Output**: Write JSON with schema `{manager, total_aum, stock_aum, stock_holdings_count, top_cusips}`.

## Fund Name Matching

**Do NOT use naive Levenshtein distance alone.** It produces false positives (e.g., "Headlands Technologies" matched to "Renaissance Technologies").

### Correct matching workflow:
1. Normalize both names: lowercase, remove punctuation, collapse whitespace, strip suffixes.
2. Check for exact match first.
3. Check if query is a substring of any manager name.
4. Check if any manager name contains the query as a word.
5. Only then consider fuzzy matching with similarity > 0.85.
6. If no confident match, report "not found" rather than forcing a bad match.

### Common variations:
- "Renaissance Technologies" may appear as "RENAISSANCE TECHNOLOGIES LLC", "Renaissance Tech", etc.
- Abbreviations, LLC/Inc/Corp suffixes, and spacing variations are common.

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

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Wrong fund matched | Levenshtein too permissive | Use stricter threshold, prefer substring match |
| Low stock count | Missing abbreviations | Include `COM`, `CL A`, `SHS` as stock tokens |
| ValueError on int conversion | Float strings | Use `int(float(value))` |
| Missing holdings | Wrong accession number | Verify manager-to-accession mapping |
| Substring trap | `ISHARES` matched as stock | Use tokenized matching, not substring |

## Anti-Patterns

- Do NOT assume closest Levenshtein match is correct — "Headlands" to "Renaissance" is a known false positive.
- Do NOT exclude `COM`, `CL A`, `SHS` as stock types — these are valid abbreviations.
- Do NOT assume `VALUE` is always integer-formatted — handle floats.
- Do NOT use substring matching for stock classification — use tokenized matching.

## Scripts

- Run `scripts/process_13f.py <data_dir> <manager_name> <quarter_date>` for a deterministic pipeline.

## References

- `references/13f_schema.md`: TSV column schemas and data formats.
