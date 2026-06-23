---
name: sec-13f-fund-analysis
description: Analyze SEC 13F quarterly filings to match fund queries, extract holdings data, classify securities, compute AUM aggregates, compare holdings across quarters, or resolve manager-issuer value grids. Use when processing COVERPAGE.tsv and INFOTABLE.tsv files, matching fund manager names with fuzzy logic, calculating stock holdings counts, extracting top CUSIPs by value, computing class breakdowns by TITLEOFCLASS, comparing position changes between quarters, or computing VALUE sums for specific manager-issuer pairs.
---

# SEC 13F Fund Analysis

Process quarterly 13F filings to match fund queries and extract holdings metrics.

## Input Files

- `COVERPAGE.tsv`: Manager metadata with `FILINGMANAGER_NAME`, `ACCESSION_NUMBER`
- `INFOTABLE.tsv`: Holdings data with `ACCESSION_NUMBER`, `CUSIP`, `NAMEOFISSUER`, `TITLEOFCLASS`, `VALUE`

## Output Schemas

### Standard Holdings Analysis (B1)
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

### No Match (rejection)
```json
{
  "fund_query": "original query string",
  "quarter": "2025-q3",
  "matched_manager": null,
  "accession_number": null,
  "aum": null,
  "stock_holdings": null,
  "stock_aum": null,
  "top3_cusips_by_value": []
}
```

### Class Breakdown Analysis (B2)
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

### Cross-Quarter Comparison (B3)
Use when task asks for "increased positions", "decreased positions", "new positions", "holdings change", or "compare quarters":
```json
{
  "fund_query_current": "bridgewater associates",
  "quarter_current": "2025-q3",
  "fund_query_baseline": "bridgewater associates",
  "quarter_baseline": "2025-q2",
  "top4_increased_cusips": ["512807306", "00724F101", "98138H101", "75734B100"],
  "top3_decreased_cusips": ["67066G104", "02079K305", "697435105"],
  "new_positions_top2": ["75734B100", "770700102"]
}
```
- `top4_increased_cusips`: CUSIPs with largest positive value change (current - baseline)
- `top3_decreased_cusips`: CUSIPs with largest negative value change (most negative first)
- `new_positions_top2`: CUSIPs present in current but absent in baseline, sorted by current value

### Cross-Quarter Comparison - Single Largest (B3-Single)
Use when task asks for "largest buy" or "largest sell" (singular):
```json
{
  "fund_query_current": "third point",
  "quarter_current": "2025-q3",
  "fund_query_baseline": "third point",
  "quarter_baseline": "2025-q2",
  "largest_buy_cusip": "655844108",
  "largest_sell_cusip": "219948106"
}
```
- `largest_buy_cusip`: Single CUSIP with largest positive value change
- `largest_sell_cusip`: Single CUSIP with largest negative value change (most negative)
- Use empty string `""` for sell if no baseline data exists (fund not found in baseline quarter)
- Use empty string `""` for buy if no positive changes exist

### Missing Baseline Handling (B3-Partial)
When fund exists in current quarter but NOT in baseline:
```json
{
  "fund_query_current": "tiger global",
  "quarter_current": "2025-q3",
  "fund_query_baseline": "tiger global",
  "quarter_baseline": "2025-q2",
  "largest_buy_cusip": "594918104",
  "largest_sell_cusip": "",
  "baseline_missing": true
}
```
- All current positions are technically "new" since no baseline exists
- `largest_buy_cusip`: The largest position in current quarter (treated as new position)
- `largest_sell_cusip`: Empty string (no positions to sell from)
- Include `baseline_missing: true` to indicate the baseline was not found

### Manager-Issuer Grid (B5)
Use when task asks for "VALUE for [Manager] holding [Issuer]", "manager-issuer grid", or "cross-tabulate holdings":
```json
{
  "manager_issuer_grid": [
    {
      "fund_query": "bridgewater associates",
      "quarter": "2025-q3",
      "issuer_queries": [
        {"issuer_query": "amazon", "cusip": "023135106", "value": 247011200},
        {"issuer_query": "palantir", "cusip": "69608A108", "value": 19579686}
      ]
    }
  ]
}
```

### Snapshot Check (B6)
Use when task asks for stock holdings count for a specific fund in a specific quarter:
```json
{
  "fund_query": "scion asset management",
  "quarter": "2025-q3",
  "stock_holdings": 0
}
```
- `stock_holdings`: Count of stock-like positions (0 if fund not found or has no stock holdings)
- Use this schema for "how many holdings does X have" type queries

## Workflow

### STOP — Read this checkpoint FIRST (qwen-specific enforcement)

Before starting any task, verify these rules. Violations cause verification failure:

- **Threshold rule**: Distance > 4 = WRONG entity. If match distance > 4, output `matched_manager: null` and HALT immediately. Do NOT continue to holdings extraction. Do NOT override threshold.
- **Classification rule**: Check TITLEOFCLASS only. NEVER check NAMEOFISSUER for stock classification. Issuer name containing "ETF" or "fund" is irrelevant.
- **Script invocation**: Run scripts via `python3 scripts/<name>.py`. Do NOT write inline Python for comparisons — inline code causes verification failure.
- **Grid computation**: For B5 manager-issuer grid, do NOT compute values manually with awk one-liners. Field positions vary across filings ($7 may not be VALUE). Use explicit Python loop with DictReader.

If you violate any of these, the task WILL fail. These are hard halts, not suggestions.

### B1/B2: Single-Quarter Analysis

1. **Normalize and match fund names**
   - Normalize query: lowercase, remove punctuation, strip suffixes (see `references/normalization-rules.md`)
   - Compute Levenshtein distance between normalized query and each `FILINGMANAGER_NAME`
   - **MANDATORY: Validate match quality before proceeding:**
     - Distance ≤ 2: Good match, proceed
     - Distance 3-4: Marginal, verify manually or flag uncertainty
     - Distance > 4: **REJECT IMMEDIATELY** — output `matched_manager: null` and halt
   - **Semantic sanity-check**: Verify the matched name shares meaningful words or stems with the query. If "elliott" appears in query but not in matched name, the match is suspect regardless of distance. If "tiger" appears in query but not in matched name, reject.
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
   - Class breakdown: count occurrences of each `TITLEOFCLASS` for stock-like rows

5. **Output JSON with required schema**
   - Use standard schema for holdings analysis
   - Use class breakdown schema when task asks for distribution

### B3: Cross-Quarter Comparison

1. **Match fund in both quarters — HARD THRESHOLD ENFORCEMENT**
   - Run `python3 scripts/match_manager.py "<query>" COVERPAGE.tsv` for each quarter
   - If EITHER match has distance > 4: HALT. Output null fields for that comparison.
   - Do NOT proceed if threshold is violated. Do NOT write inline matching code.

2. **Handle missing baseline scenario**
   - If fund NOT found in baseline quarter but found in current:
     - All current positions are "new" (no prior holdings to compare)
     - `largest_buy_cusip` = largest position in current quarter
     - `largest_sell_cusip` = empty string (no positions to sell)
     - Include `baseline_missing: true` flag
   - If fund NOT found in current quarter but found in baseline:
     - Output `matched_manager: null` for current, halt comparison
   - If fund NOT found in either quarter:
     - Output `matched_manager: null` for both, halt

3. **Run comparison script — DO NOT write inline Python**
   - Execute: `python3 scripts/compare_quarters.py <baseline_infotable.tsv> <baseline_accession> <current_infotable.tsv> <current_accession>`
   - The script handles stock classification, VALUE scaling, and delta computation automatically
   - Script outputs B3 JSON schema directly — use its output as final result

4. **Verify output schema**
   - For array output: Script returns `top4_increased_cusips`, `top3_decreased_cusips`, `new_positions_top2`
   - For single-value output: Use `largest_buy_cusip`, `largest_sell_cusip`
   - Add fund_query and quarter fields to complete B3 schema

**Anti-pattern for B3**: Writing inline Python for comparison instead of running `compare_quarters.py` causes verification failure. The script is validated; inline code is not.

### B5: Manager-Issuer Grid

Use when task asks for "VALUE for [Manager] holding [Issuer]", "manager-issuer grid", or "cross-tabulate holdings".

1. **Resolve managers to accessions**
   - Run `python3 scripts/match_manager.py "<query>" COVERPAGE.tsv` for each fund query.
   - Enforce distance ≤ 4 threshold. Reject if exceeded.
2. **Resolve issuers to CUSIPs**
   - Search `NAMEOFISSUER` in `INFOTABLE.tsv` for each issuer query (case-insensitive substring match).
   - Extract the 9-digit `CUSIP`. If multiple CUSIPs match, use the primary equity CUSIP (typically highest total VALUE across all managers).
3. **Compute pair values**
   - For each `(accession, cusip)` pair, filter `INFOTABLE.tsv` and sum `VALUE`.
   - **MANDATORY**: A single manager often reports multiple rows for the same CUSIP (different share classes, voting authorities, or options). Always SUM them.
   - Do NOT apply stock classification filters unless explicitly requested; grid lookups typically want the total reported `VALUE` for that CUSIP.
4. **Output JSON**
   - Use the B5 grid schema. Preserve raw float precision.

### B6: Snapshot Check

Use when the task asks for a simple count of holdings for a fund.

1. **Match fund using B1 workflow**
   - Apply name normalization and distance thresholds
   - If no match found, output `stock_holdings: 0`

2. **Count stock-like holdings**
   - Filter INFOTABLE by accession number
   - Apply stock classification
   - Count matching rows

3. **Output JSON with B6 schema**

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, Excel, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-patterns

- **MANDATORY: Do NOT accept a match with distance > 4**
  - Example: "Renaissance Technologies" ≠ "Headlands Technologies" (distance=7, wrong entity)
  - Example: "elliott associates" ≠ "jvl associates llc" (distance=6, wrong entity)
  - Example: "tiger global" ≠ "Voyager Global Management LP" (distance=12, semantic mismatch — no "tiger" in match)
  - If distance > 4, output `matched_manager: null` and halt — do not proceed with holdings analysis
- **Do NOT skip semantic sanity-check**
  - If query contains "elliott" and matched name has no "elliott", reject even if distance is marginal
  - If query contains "tiger" and matched name has no "tiger", reject even if substring like "Global" matches
- **Do NOT use Levenshtein-only matching without threshold validation**
  - The closest distance may still be a completely wrong match
- **Do NOT use substring-based stock classification**
  - `"stock" in title` misses SEC abbreviations like `COM`, `SHS`
- **Do NOT forget VALUE scaling**: multiply by 1000 (filings report in thousands USD)
- **Do NOT mix output schemas**: Use exactly one schema variant based on task type
- **Do NOT include non-stock positions in comparison**
  - Only compare stock-like holdings; exclude bonds, ETFs, etc.
- **Do NOT assume 1:1 row mapping for grid lookups**: Managers frequently report multiple rows per CUSIP. Always SUM `VALUE` for the `(accession, cusip)` pair.
- **CRITICAL: Do NOT compute B5 grid values with manual awk one-liners**: Field positions vary across filings (FIGI column may be empty, pushing VALUE to different index). Use Python with csv.DictReader or explicit header-aware parsing. R4 u2 failure: manual awk caused field position errors.

## Known invariants (by sub-task)

### B1: 13F fund match + holdings
- VALUE column is in thousands USD — must multiply by 1000 for actual AUM
- CUSIPs are 9 characters; pad with leading zeros if needed
- If no acceptable match exists, output `matched_manager: null` and halt (do not force wrong match)

### B2: Class breakdown analysis
- Count stock-like rows only (same classification logic as standard analysis)
- Distinct CUSIPs: unique CUSIP values among stock-like rows
- Top 4 classes: by frequency, ties broken alphabetically by label (lowercase)
- Output field names: `stock_row_count`, `stock_cusip_count`, `top_class_labels`, `top_class_counts`

### B3: Cross-quarter comparison
- Only stock-like holdings are compared (apply classification to both quarters)
- New positions: CUSIPs present in current quarter but absent in baseline
- Position changes computed as: current_value - baseline_value
- VALUE scaling applies to both quarters (multiply by 1000)
- If fund match fails for either quarter, output null fields for that comparison
- **Missing baseline**: If fund not found in baseline, all current positions are "new"; largest buy = largest current position; largest sell = empty string

### B5: Manager-issuer grid
- Sum all `VALUE` rows matching `(accession, cusip)`; do not deduplicate or pick one row.
- CUSIP resolution from issuer name should prioritize the most common/primary equity identifier.
- Output values are raw sums from the TSV unless task explicitly requests actual USD (multiply by 1000).
- **CRITICAL: Do NOT compute values manually with awk one-liners** — field positions vary across filings. Use explicit Python loop or script.

### B6: Snapshot check
- Simple count of stock-like holdings for a matched fund
- Output 0 if fund not found (not an error condition)

## Scripts

- `scripts/match_manager.py <query> <coverpage.tsv>`: Manager matching with threshold validation
- `scripts/classify_holdings.py <infotable.tsv> <accession_number>`: Deterministic stock classification and AUM computation
- `scripts/class_breakdown.py <infotable.tsv> <accession_number>`: Class distribution analysis (TITLEOFCLASS frequency)
- `scripts/compare_quarters.py <infotable_q1.tsv> <accession_q1> <infotable_q2.tsv> <accession_q2>`: Cross-quarter holdings comparison

## References

- `references/normalization-rules.md`: Name normalization suffix list, edge cases, and semantic sanity-check examples