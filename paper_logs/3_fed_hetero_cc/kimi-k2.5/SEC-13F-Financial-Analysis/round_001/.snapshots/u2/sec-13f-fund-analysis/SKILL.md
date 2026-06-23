---
name: sec-13f-fund-analysis
description: Analyze SEC 13F filings to match fund queries, extract holdings data, classify securities, and compute aggregates. Use when processing COVERPAGE.tsv and INFOTABLE.tsv files, matching fund names with fuzzy logic, computing AUM and top holdings by value, or extracting CUSIP-level data. Trigger phrases include "13F", "holdings", "AUM", "CUSIP", "accession number", "fund manager", or "quarter".
---

# SEC 13F Fund Analysis

Process quarterly 13F filings to match fund queries and extract holdings metrics.

## Input Files

- `COVERPAGE.tsv`: Manager metadata with `FILINGMANAGER_NAME`, `ACCESSION_NUMBER`
- `INFOTABLE.tsv`: Holdings data with `ACCESSION_NUMBER`, `CUSIP`, `NAMEOFISSUER`, `TITLEOFCLASS`, `VALUE`

## Workflow

1. **Normalize and match fund names**
   - Normalize query: lowercase, remove punctuation, strip suffixes (`llc`, `lp`, `inc`, `corp`, `ltd`, `co`, etc.)
   - Compute Levenshtein distance between normalized query and each `FILINGMANAGER_NAME`
   - **Validate match quality before proceeding:**
     - Distance ≤ 2: Good match, proceed
     - Distance 3-4: Marginal, flag uncertainty
     - Distance > 4: Likely wrong match, output `matched_manager: null` and halt
   - Extract `ACCESSION_NUMBER` from best match

2. **Filter and classify holdings**
   - Join `INFOTABLE.tsv` on `ACCESSION_NUMBER`
   - Classify as stock-like if `TITLEOFCLASS` matches SEC abbreviations:
     - Include: `COM`, `SHS`, `CL A`, `CL B`, `CL C`, `ORD`, `CAP STK`, `COMMON`, `STK`, `CLASS A`, `CLASS B`, `CLASS C`
   - Exclude if `TITLEOFCLASS` contains: `NOTE`, `DEB`, `BOND`, `PUT`, `CALL`, `WTS`, `RIGHT`, `ETF`, `FUND`, `UNIT`, `TR`, `ADR`, `preferred`

3. **Compute aggregates**
   - `VALUE` in 13F filings is in **thousands of USD** — multiply by 1,000
   - Total AUM: sum of all `VALUE` for the accession
   - Stock holdings: count of stock-like positions
   - Stock AUM: sum of `VALUE` for stock-like positions
   - Top N CUSIPs: sort stock-like by `VALUE` descending, take first N

4. **Validate outputs**
   - Verify stock-like classification by checking `TITLEOFCLASS` values
   - Confirm excluded patterns are not present in final set
   - Check AUM sums match expectations (no double counting)

## Critical Anti-Patterns

- **Do NOT accept poor manager matches.** Levenshtein distance > 4 on normalized names indicates wrong entity. "Renaissance Technologies" ≠ "Headlands Technologies" despite sharing "technologies".
- **Do NOT use substring matches like `"stock" in title`.** This misses >90% of common stock rows labeled `COM` or `SHS`. Use exact SEC abbreviation matching.
- **Do NOT forget VALUE scaling.** Multiply by 1,000 unless dataset documentation states otherwise.
- **Do NOT assume TITLEOFCLASS values are consistent.** Always verify classification rules against actual data.

## Output Schema

```json
{
  "fund_query": "original query string",
  "quarter": "2025-q3",
  "matched_manager": "Best Match LLC",
  "accession_number": "0001234567-25-000001",
  "aum": 1234567890,
  "stock_holdings": 42,
  "stock_aum": 987654321,
  "top3_cusips_by_value": ["123456789", "987654321", "555555555"]
}
```

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### B1-13F-fund-match-holdings
- Manager name matching must validate distance threshold before proceeding. If distance > 4, output `matched_manager: null` and halt.
- Stock classification must use SEC abbreviations (`COM`, `SHS`, `CL A`, etc.), not substring matches.
- VALUE field is in thousands — multiply by 1,000 for actual USD.

## References

- `references/normalization-rules.md`: Extended suffix lists and edge cases

## Scripts

- `scripts/match_fund.py`: Reusable fund matching with Levenshtein distance and threshold validation
- Use this script instead of inline Python for deterministic manager matching.