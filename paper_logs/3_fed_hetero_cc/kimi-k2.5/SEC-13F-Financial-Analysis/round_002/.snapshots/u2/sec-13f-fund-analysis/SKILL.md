---
name: sec-13f-fund-analysis
description: Analyze SEC 13F filings to match fund queries, extract holdings data, classify securities, and compute aggregates. Use when processing COVERPAGE.tsv and INFOTABLE.tsv files, matching fund names with fuzzy logic, computing AUM and top holdings by value, extracting CUSIP-level data, or generating class breakdowns by TITLEOFCLASS. Trigger phrases include "13F", "holdings", "AUM", "CUSIP", "accession number", "fund manager", "quarter", "class breakdown", or "TITLEOFCLASS".
---

# SEC 13F Fund Analysis

Process quarterly 13F filings to match fund queries and extract holdings metrics.

## Input Files

- `COVERPAGE.tsv`: Manager metadata with `FILINGMANAGER_NAME`, `ACCESSION_NUMBER`
- `INFOTABLE.tsv`: Holdings data with `ACCESSION_NUMBER`, `CUSIP`, `NAMEOFISSUER`, `TITLEOFCLASS`, `VALUE`

## Output Schemas — USE EXACTLY ONE

**DO NOT mix fields between schemas. Each task requires exactly one schema.**

### Standard Holdings Analysis (B1)
Use for tasks asking for "holdings", "AUM", "top CUSIPs", "stock count":
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

### Class Breakdown Analysis (B2)
Use for tasks asking for "class breakdown", "TITLEOFCLASS distribution", "by class label":
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
- `top_class_labels`: Top 4 most frequent TITLEOFCLASS values among stock-like rows (lowercase)
- `top_class_counts`: Corresponding counts
- Tie-breaking: sort alphabetically by label when counts are equal

## Workflow

### Step 1: Normalize and Match Fund Names — MANDATORY THRESHOLD

1. Normalize query: lowercase, remove punctuation, strip suffixes (see `scripts/match_fund.py`)
2. Run `python3 scripts/match_fund.py "<query>" COVERPAGE.tsv`
3. **IF output shows `matched_manager: null` — HALT. DO NOT CONTINUE.**
   - Output the no-match schema and exit
   - DO NOT override with `max_distance=6` or any higher threshold
4. **Semantic sanity-check**: If match has distance 3-4, verify shared key words:
   - "elliott" in query should appear in matched name
   - If no key words match despite marginal distance → reject

### Step 2: Filter Holdings

- Join `INFOTABLE.tsv` on `ACCESSION_NUMBER` from match result

### Step 3: Classify Stock Holdings — TITLEOFCLASS ONLY

- **CLASSIFY BY TITLEOFCLASS ONLY — NEVER BY NAMEOFISSUER**
- Stock patterns: `COM`, `SHS`, `CL A`, `CL B`, `CL C`, `ORD`, `CAP STK`, `COMMON`, `STK`, `CLASS A`, `CLASS B`, `CLASS C`
- Exclude: `NOTE`, `DEB`, `BOND`, `PUT`, `CALL`, `WTS`, `RIGHT`, `ETF`, `FUND`, `UNIT`, `TR`, `ADR`, `PFD`, `PRFD`
- See `references/toc-patterns.md` for complete pattern list and edge cases

### Step 4: Compute Aggregates

- **VALUE is in thousands USD — multiply by 1000**
- For standard analysis: run `python3 scripts/classify_holdings.py INFOTABLE.tsv <accession>`
- For class breakdown: run `python3 scripts/class_breakdown.py INFOTABLE.tsv <accession>`

### Step 5: Output — EXACT SCHEMA MATCH

- Use exactly one schema from above — no mixing
- Verify all required fields present
- DO NOT add extra fields like `stock_row_count` to standard schema

## Critical Anti-Patterns — STOP IF VIOLATED

- **THRESHOLD OVERRIDE = FAILURE**: Distance > 4 means wrong entity. "Elliott Associates" ≠ "JVL Associates" (distance=6, shares "associates" only). DO NOT use `max_distance=6` override.
- **SCHEMA MIXING = FAILURE**: Standard schema needs `stock_holdings`/`top3_cusips_by_value`. Class breakdown needs `stock_row_count`/`top_class_labels`. Never combine.
- **NAMEOFISSUER CLASSIFICATION = FAILURE**: Check TITLEOFCLASS only. Issuer name like "Netflix" doesn't determine stock/fund status.
- **SUBSTRING MATCHES = FAILURE**: `"stock" in title` misses 90%+ of SEC abbreviations (`COM`, `SHS`). Use exact keyword matching.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, Excel, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### B1-13F-fund-match-holdings
- Manager name matching must validate distance threshold before proceeding
- If distance > 4: output `matched_manager: null` and HALT — do not proceed to holdings
- Stock classification must use SEC abbreviations (`COM`, `SHS`, `CL A`, etc.)
- VALUE field is in thousands — multiply by 1,000 for actual USD
- CUSIPs are 9 characters; pad with leading zeros if necessary

### B2-class-breakdown
- Count stock-like rows only (same classification logic as B1)
- Distinct CUSIPs: unique CUSIP values among stock-like rows
- Top 4 classes: by frequency, ties broken alphabetically by label (lowercase)
- Output uses `stock_row_count`, `stock_cusip_count`, `top_class_labels`, `top_class_counts`

## Scripts

- `scripts/match_fund.py <query> <coverpage.tsv>`: Manager matching with threshold validation
  - Default threshold: 4. Output `matched_manager: null` if exceeded.
  - DO NOT add `max_distance` override argument.
- `scripts/classify_holdings.py <infotable> <accession>`: Standard holdings analysis
- `scripts/class_breakdown.py <infotable> <accession>`: Class distribution analysis

## References

- `references/normalization-rules.md`: Name normalization suffix list and edge cases
- `references/toc-patterns.md`: Complete TITLEOFCLASS patterns for stock vs fund classification