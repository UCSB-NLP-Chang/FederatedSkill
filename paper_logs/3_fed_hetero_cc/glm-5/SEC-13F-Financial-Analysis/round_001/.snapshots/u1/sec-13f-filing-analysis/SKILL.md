---
name: sec-13f-filing-analysis
description: Analyze SEC 13F quarterly filings to match fund queries, extract holdings data, classify securities, and compute AUM aggregates. Use when processing COVERPAGE.tsv and INFOTABLE.tsv files, matching fund manager names with fuzzy logic, calculating stock holdings counts, or extracting top CUSIPs by value.
---

# SEC 13F Filing Analysis

Process quarterly 13F filings to match fund queries and extract holdings metrics.

## Input Files

- `COVERPAGE.tsv`: Manager metadata with `FILINGMANAGER_NAME`, `ACCESSION_NUMBER`
- `INFOTABLE.tsv`: Holdings data with `ACCESSION_NUMBER`, `CUSIP`, `NAMEOFISSUER`, `TITLEOFCLASS`, `VALUE`

## Workflow

1. **Normalize and match fund names**
   - Normalize query: lowercase, remove punctuation, strip suffixes (see `references/normalization-rules.md`)
   - Compute Levenshtein distance between normalized query and each `FILINGMANAGER_NAME`
   - **CRITICAL: Validate match quality before proceeding:**
     - Distance ≤ 2: Good match, proceed
     - Distance 3-4: Marginal, verify manually or flag uncertainty
     - Distance > 4: **Reject**, output `matched_manager: null` and halt
   - Extract `ACCESSION_NUMBER` from best acceptable match

2. **Filter holdings by accession number**
   - Join `INFOTABLE.tsv` on `ACCESSION_NUMBER`
   - Filter rows matching the accession number exactly

3. **Classify stock-like holdings**
   - Match by exact keyword or prefix in `TITLEOFCLASS` (uppercase):
     - Include: `COM`, `SHS`, `CL A`, `CL B`, `CL C`, `ORD`, `CAP STK`, `COMMON`, `STK`, `CLASS A`, `CLASS B`, `CLASS C`
   - Exclude: `NOTE`, `DEB`, `BOND`, `PUT`, `CALL`, `WTS`, `RIGHT`, `ETF`, `FUND`, `UNIT`, `TR`, `ADR`, `PFD`, `PREF`
   - **Anti-pattern**: Do NOT use substring matches like `"stock" in title`. Misses >90% of SEC abbreviations (`COM`, `SHS`).

4. **Compute aggregates**
   - Total AUM: sum of all `VALUE` for the accession (multiply by 1000 — values are in thousands USD)
   - Stock holdings: count of stock-like positions
   - Stock AUM: sum of `VALUE` for stock-like positions (multiply by 1000)
   - Top N CUSIPs: sort stock-like by `VALUE` descending, take first N CUSIPs

5. **Output JSON with required schema**

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

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, Excel, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-patterns

- **Do NOT accept a match with distance > 4 without explicit justification**
  - Example: "Renaissance Technologies" ≠ "Headlands Technologies" (distance=7, wrong entity)
- **Do NOT use Levenshtein-only matching without threshold validation**
  - The closest distance may still be a completely wrong match
- **Do NOT use substring-based stock classification**
  - `"stock" in title` misses SEC abbreviations like `COM`, `SHS`, `CL A`
- **Do NOT forget VALUE scaling**: multiply by 1000 (filings report in thousands USD)

## Known invariants (by sub-task)

### B1: 13F fund match + holdings
- VALUE column is in thousands USD — must multiply by 1000 for actual AUM
- CUSIPs are 9 characters; pad with leading zeros if needed
- If no acceptable match exists, output `matched_manager: null` and halt (do not force wrong match)

## Scripts

- `scripts/match_manager.py <query> <coverpage.tsv>`: Manager matching with threshold validation
- `scripts/classify_holdings.py <infotable.tsv> <accession_number>`: Deterministic stock classification and AUM computation

## References

- `references/normalization-rules.md`: Name normalization suffix list and edge cases