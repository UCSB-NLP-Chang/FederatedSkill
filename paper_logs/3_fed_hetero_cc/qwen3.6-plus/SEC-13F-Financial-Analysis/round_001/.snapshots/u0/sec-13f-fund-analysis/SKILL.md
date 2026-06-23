---
name: sec-13f-fund-analysis
description: Analyze SEC 13F filings to match fund queries, extract holdings data, classify securities, and compute aggregates. Use when processing COVERPAGE.tsv and INFOTABLE.tsv files, matching fund names with fuzzy logic, computing AUM, or extracting top holdings by value.
---

# SEC 13F Fund Analysis

Process quarterly 13F filings to match fund queries and extract holdings metrics.

## Input Files

- `COVERPAGE.tsv`: Manager metadata with `FILINGMANAGER_NAME`, `ACCESSION_NUMBER`
- `INFOTABLE.tsv`: Holdings data with `ACCESSION_NUMBER`, `CUSIP`, `NAMEOFISSUER`, `TITLEOFCLASS`, `VALUE`

## Workflow

1. **Normalize and match fund names**
   - Normalize query: lowercase, remove punctuation, strip legal suffixes (`llc`, `lp`, `inc`, `corp`, `ltd`, `co`)
   - Compute Levenshtein distance between normalized query and each `FILINGMANAGER_NAME`
   - **Critical: Validate match quality before proceeding:**
     - Distance ≤ 2: Good match, proceed
     - Distance 3-4: Marginal, verify manually or flag uncertainty
     - Distance > 4: Likely wrong match, output `matched_manager: null` and halt
   - Extract `ACCESSION_NUMBER` from best match

2. **Filter holdings**
   - Join `INFOTABLE.tsv` on `ACCESSION_NUMBER`

3. **Classify stock holdings**
   - `TITLEOFCLASS` uses SEC abbreviations. Include patterns: `COM`, `SHS`, `CL A`, `CL B`, `CL C`, `ORD`, `CAP STK`, `COMMON`, `STK`, `CLASS A`, `CLASS B`, `CLASS C`
   - Exclude debt/derivatives: `NOTE`, `DEB`, `BOND`, `PUT`, `CALL`, `WTS`, `RIGHT`, `ETF`, `FUND`, `UNIT`, `TR`, `ADR`, `preferred`
   - **Anti-pattern**: Do not use simple substring like `"stock" in title`. It misses >90% of common stock rows labeled `COM` or `SHS`.

4. **Compute aggregates**
   - `VALUE` is in thousands of USD. Multiply by 1,000.
   - Total AUM: sum of all `VALUE` for the accession
   - Stock holdings: count of stock-like positions
   - Stock AUM: sum of `VALUE` for stock-like positions
   - Top N CUSIPs: sort stock-like by `VALUE` descending, take first N

5. **Output**: Generate JSON with required fields. Verify counts and sums.

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

### 13f-fund-match
- Output JSON must contain all 7 fields: `fund_query`, `quarter`, `matched_manager`, `accession_number`, `aum`, `stock_holdings`, `stock_aum`, `top3_cusips_by_value`
- If no acceptable manager match exists (distance > 4), output `matched_manager: null`, `accession_number: null`, and zero-valued aggregates — do not force a wrong match
- CUSIPs are 9 characters; pad with leading zeros if necessary

## Anti-patterns

- **Do not accept a match with distance > 4 without explicit justification** — "Renaissance Technologies" ≠ "Headlands Technologies" despite sharing "technologies"
- Do not assume the closest match is correct — it may be completely wrong
- Do not use `"stock" in title` for classification — use SEC abbreviations: `COM`, `SHS`, `CL A`, etc.

## Scripts

- Run `scripts/classify_holdings.py <infotable_path> <accession_number>` to classify holdings, compute AUM, and extract top CUSIPs
- Run `scripts/match_manager.py <query> <coverpage.tsv>` for threshold-based manager matching

## References

- `references/normalization-rules.md`: Extended suffix lists and edge cases for name normalization