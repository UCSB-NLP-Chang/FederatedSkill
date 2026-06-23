---
name: sec-13f-analysis
description: Parse and analyze SEC 13F filing data (COVERPAGE.tsv and INFOTABLE.tsv) to extract manager info, AUM, stock holdings, and top CUSIPs. Use when tasked with processing quarterly institutional investment reports, matching fund managers, or calculating portfolio metrics from SEC EDGAR 13F datasets.
---

# SEC 13F Filing Analysis

## Workflow

1. **Locate Data**: Identify `COVERPAGE.tsv` and `INFOTABLE.tsv` in the target directory (e.g., `2025-q3/`).

2. **Filter by Quarter**: Use `REPORTCALENDARORQUARTER` in `COVERPAGE.tsv` to isolate filings for the requested period (e.g., `30-SEP-2025` for Q3 2025).

3. **Match Manager**:
   - Normalize names: lowercase, remove punctuation, strip legal suffixes (`LLC`, `INC`, `LTD`, `CORP`, `LP`, `CO`), collapse whitespace.
   - Check exact match first.
   - Check if query is substring of manager name.
   - Check if manager name contains query as a word.
   - Only then consider fuzzy matching with **high threshold**: similarity > 0.85 OR distance < 3.
   - **If no confident match exists, report `null` or "not found" — do NOT force the closest Levenshtein match.**

4. **Get Holdings**: Join matched `ACCESSION_NUMBER` with `INFOTABLE.tsv`.

5. **Classify Stock Holdings**: Filter rows where `TITLEOFCLASS` indicates equity using tokenized matching:
   - **Stock tokens (include)**: `common`, `ordinary`, `share`, `stock`, `com`, `shs`, `class a`, `class b`, `cl a`, `cl b`
   - **Exclude tokens**: `etf`, `put`, `call`, `option`, `bond`, `note`, `preferred`, `pfd`, `adr`, `ads`, `trust`, `fund`, `index`
   - **Rule**: Token must appear as a separate word, not substring. `ISHARES` contains "share" but not as token — excluded.
   - Use `title.lower().split()` and check for exact token matches.

6. **Calculate Metrics**:
   - `Total AUM`: Sum `VALUE` for all matched holdings.
   - `Stock AUM`: Sum `VALUE` for stock-classified holdings.
   - `Stock Holdings Count`: Count of stock-classified rows.
   - `Top N CUSIPs`: Sort stock holdings by `VALUE` descending, take top N, extract `CUSIP`.

7. **Output**: Write JSON with schema `{manager, total_aum, stock_aum, stock_holdings_count, top_cusips}`.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, CSV, Excel). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `result["aum"] = total_aum` with total_aum as raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### sec-13f-manager-lookup
- Manager matching must return `null` if no confident match (Levenshtein distance > 3 AND no substring/word match). Forcing closest match yields false positives (R0 u1: "Headlands" matched to "Renaissance").

### sec-13f-stock-classification
- Abbreviations `COM`, `SHS`, `CL A`, `CL B` are valid stock indicators (R0: all workers undercounted stocks by excluding these abbreviations).
- `ISHARES` contains "share" as substring but NOT as token — must be excluded.
- `TITLEOFCLASS` values like `U.S. REAL ES ETF` must be excluded via `etf` token.

## Anti-Patterns

- Do NOT assume closest Levenshtein match is correct — it frequently yields false positives.
- Do NOT exclude `COM`, `CL A`, `SHS` as stock types — they are valid abbreviations.
- Do NOT use substring matching without tokenization — `ISHARES` contains `share` but is an ETF.
- Do NOT round AUM values — pass raw floats to output.

## Scripts

- Run `python3 scripts/process_13f.py <data_dir> <manager_name> <quarter_date>` for a deterministic pipeline that handles normalization, safe matching, and metric calculation. Outputs JSON to stdout.

## References

- `references/13f_schema.md`: TSV column schemas, stock classification logic, and examples.