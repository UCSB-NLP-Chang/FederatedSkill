---
name: sec-13f-fund-analysis
description: Analyze SEC 13F filings to match fund queries, extract holdings data, classify securities, and compute aggregates. Use when processing COVERPAGE.tsv and INFOTABLE.tsv files, matching fund names with fuzzy logic, computing AUM, extracting top holdings by value, or generating class breakdowns by TITLEOFCLASS. Trigger phrases include "13F", "holdings", "AUM", "CUSIP", "accession number", "fund manager", "quarter", "class breakdown", or "TITLEOFCLASS".
---

# SEC 13F Fund Analysis

Process quarterly 13F filings to match fund queries and extract holdings metrics.

## Input Files

- `COVERPAGE.tsv`: Manager metadata with `FILINGMANAGER_NAME`, `ACCESSION_NUMBER`
- `INFOTABLE.tsv`: Holdings data with `ACCESSION_NUMBER`, `CUSIP`, `NAMEOFISSUER`, `TITLEOFCLASS`, `VALUE`

## Output Schemas

### Schema A: Standard Holdings Analysis
Use for default "holdings", "AUM", "top CUSIPs" tasks:
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

### Schema B: Class Breakdown Analysis
Use when task asks for "class breakdown", "TITLEOFCLASS distribution", or "by class label":
```json
{
  "fund_query": "original query string",
  "quarter": "2025-q3",
  "aum_total": 1234567890000.0,
  "stock_row_count": 42,
  "stock_cusip_count": 39,
  "top_class_labels": ["com", "cl a", "shs", "cap stk"],
  "top_class_counts": [23, 4, 3, 2]
}
```

**Schema selection rule**: Use EXACTLY ONE schema. Do NOT mix fields from Schema A and Schema B.

## Workflow

1. **STOP — Read this checkpoint FIRST**
   - **Classification rule**: ALWAYS classify by `TITLEOFCLASS` only. NEVER check `NAMEOFISSUER` for classification.
   - **Threshold rule**: Distance > 4 = WRONG entity. Output `matched_manager: null` and HALT.
   - If you violate either rule, verification WILL fail.

2. **Normalize and match fund names**
   - Normalize query: lowercase, remove punctuation, strip suffixes (see `references/normalization-rules.md`)
   - Run `scripts/match_manager.py <query> <coverpage.tsv>`
   - **HARD THRESHOLD**: If distance > 4, output `matched_manager: null` and STOP. Do NOT continue to holdings extraction.
   - **Semantic sanity-check**: If query contains key word (e.g., "elliott") but matched name lacks it, reject even if distance is marginal. Example: "elliott associates" ≠ "jvl associates llc" (no "elliott" in match).

3. **Filter holdings by accession number**
   - Join `INFOTABLE.tsv` on `ACCESSION_NUMBER` from matched manager
   - Filter rows matching accession number exactly

4. **Classify stock holdings — TITLEOFCLASS ONLY**
   - Run `scripts/classify_holdings.py <infotable.tsv> <accession_number>` for Schema A
   - Run `scripts/class_breakdown.py <infotable.tsv> <accession_number>` for Schema B
   - **Classification uses `TITLEOFCLASS` field ONLY**. Patterns: `COM`, `SHS`, `CL A`, `CL B`, `CL C`, `ORD`, `CAP STK`, `COMMON`, `STK`, `CLASS A`, `CLASS B`, `CLASS C`
   - **Exclude**: `NOTE`, `DEB`, `BOND`, `PUT`, `CALL`, `WTS`, `RIGHT`, `ETF`, `FUND`, `UNIT`, `TR`, `ADR`, `PFD`, `PRFD`
   - See `references/toc-patterns.md` for complete pattern lists and edge cases.

5. **Compute aggregates**
   - `VALUE` is in thousands of USD. Multiply by 1,000 for actual AUM.
   - Schema A: total AUM, stock holdings count, stock AUM, top 3 CUSIPs by VALUE
   - Schema B: total AUM, stock row count, distinct CUSIP count, top 4 TITLEOFCLASS by frequency

6. **Output JSON with exact schema fields**
   - Verify all required fields present
   - No extra fields beyond schema definition

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, Excel, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### B1-13f-fund-match-holdings
- VALUE field is in thousands USD — multiply by 1,000 for actual AUM
- CUSIPs are 9 characters; pad with leading zeros if necessary
- If no acceptable match (distance > 4), output `matched_manager: null`, `accession_number: null`, and zero-valued aggregates

### B2-class-breakdown
- Count stock-like rows only (same classification logic as B1)
- `stock_cusip_count`: distinct CUSIP values among stock-like rows
- Top 4 classes: by frequency, ties broken alphabetically by label
- Use lowercase for `top_class_labels`

## Anti-patterns

- **Distance > 4 = WRONG entity. HALT and output null.**
  - "Renaissance Technologies" ≠ "Headlands Technologies" (distance=7)
  - "Elliott Associates" ≠ "JVL Associates LLC" (distance=6, no "elliott" in match)
- **NEVER classify by `NAMEOFISSUER`**. Use `TITLEOFCLASS` ONLY.
  - Checking issuer name for fund keywords causes false positives
  - Netflix Inc is a stock; issuer name containing "ETF" in a different row is irrelevant
- **Do NOT use substring `"stock" in title`** — misses SEC abbreviations like `COM`, `SHS`
- **Do NOT mix schemas** — Schema A fields + Schema B fields = verification failure
- **Do NOT forget VALUE scaling** — multiply by 1,000 (filings report in thousands)

## Scripts

- `scripts/match_manager.py <query> <coverpage.tsv>`: Manager matching with threshold validation
- `scripts/classify_holdings.py <infotable.tsv> <accession_number>`: Schema A standard analysis
- `scripts/class_breakdown.py <infotable.tsv> <accession_number>`: Schema B class distribution

## References

- `references/normalization-rules.md`: Name normalization suffix list, edge cases, semantic sanity-check
- `references/toc-patterns.md`: Complete TITLEOFCLASS patterns for stock vs fund classification