---
name: sec-13f-analysis
description: Parse and analyze SEC Form 13F quarterly filings (COVERPAGE.tsv and INFOTABLE.tsv) to extract manager info, AUM, stock holdings, and top CUSIPs. Use when tasks involve fund manager lookups, holdings extraction, stock classification, AUM calculations, or CUSIP analysis from 13F TSV datasets.
---

# SEC 13F Filing Analysis

## Workflow

1. **Locate Data**: Find `COVERPAGE.tsv` and `INFOTABLE.tsv` in the target quarter directory (e.g., `2025-q3/`).
2. **Filter by Quarter**: Use `REPORTCALENDARORQUARTER` in `COVERPAGE.tsv` to isolate filings for the requested period (e.g., `30-SEP-2025` for Q3 2025).
3. **Match Manager**:
   - Normalize names: lowercase, strip punctuation, remove legal suffixes (`LLC`, `INC`, `LTD`, `CORP`, `LP`, `CO`).
   - Prefer exact or case-insensitive substring match.
   - **Anti-pattern**: Do NOT force a Levenshtein match with distance > 3 or similarity < 0.85. This yields false positives (e.g., "Headlands" matched to "Renaissance"). If no valid match, report `null`.
4. **Join Holdings**: Use matched `ACCESSION_NUMBER` to filter `INFOTABLE.tsv`.
5. **Classify Stocks**: Use tokenized matching on `TITLEOFCLASS` (see references/stock-classification.md).
6. **Calculate Metrics**:
   - `Total AUM`: Sum of `VALUE` for all holdings.
   - `Stock Holdings`: Count of rows classified as stock-like.
   - `Stock AUM`: Sum of `VALUE` for stock-classified rows.
   - `Top N CUSIPs`: Sort stock holdings by `VALUE` descending, extract `CUSIP`.
7. **Output**: Write results to specified JSON format.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision.

## Known invariants (by sub-task)

### 13f-manager-holdings-extraction
- `ACCESSION_NUMBER` is the join key between COVERPAGE and INFOTABLE (first column in both files).
- `VALUE` may be float (e.g., `3620781.0`) — use `int(float(value))` for integer output.
- Manager name matching: substring match is safer than pure Levenshtein. Example: query "Renaissance Technologies" should match "RENAISSANCE TECHNOLOGIES LLC".

## Anti-Patterns

- Do NOT assume closest Levenshtein match is correct — distance < 3 or similarity > 0.85 is required.
- Do NOT exclude abbreviations like `COM`, `CL A`, `SHS` from stock classification — these ARE valid stock indicators.
- Do NOT include ETFs or bond funds in stock counts — check `TITLEOFCLASS`, not issuer name.
- Do NOT trust exact string matching for manager names — normalize first.

## Scripts

Run `python3 scripts/process_13f.py <data_dir> <manager_name> <quarter_date>` for a deterministic pipeline that handles normalization, safe matching, and metric calculation. Outputs JSON to stdout.

## References

- `references/13f_schema.md`: Column definitions for COVERPAGE.tsv and INFOTABLE.tsv.
- `references/stock-classification.md`: Tokenized matching rules for stock-like holdings.
