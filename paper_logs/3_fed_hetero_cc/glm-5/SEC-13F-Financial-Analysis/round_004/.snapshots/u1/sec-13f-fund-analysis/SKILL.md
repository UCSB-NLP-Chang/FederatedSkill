---
name: sec-13f-fund-analysis
description: Analyze SEC 13F quarterly filings to match fund queries, extract holdings data, classify securities, compute AUM aggregates, compare holdings across quarters, and perform issuer ownership rollups. Use when processing COVERPAGE.tsv and INFOTABLE.tsv files, matching fund manager names with fuzzy logic, calculating stock holdings counts, extracting top CUSIPs by value, computing class breakdowns by TITLEOFCLASS, comparing position changes between quarters, or finding all managers holding a specific issuer.
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

### Issuer Ownership Rollup (B4)
Use when task asks for "who owns", "top holders", "managers holding", or "ownership rollup" for a specific issuer:
```json
{
  "issuer_query": "palantir",
  "quarter": "2025-q3",
  "cusip": "69608A108",
  "top5_managers": ["VANGUARD GROUP INC", "BlackRock, Inc.", "STATE STREET CORP", "SUSQUEHANNA INTERNATIONAL GROUP, LLP", "GEODE CAPITAL MANAGEMENT, LLC"],
  "top5_accessions": ["0000102909-25-000353", "0002012383-25-002949", "0000093751-25-000651", "0001446194-25-000027", "0001214717-25-000016"]
}
```
- `issuer_query`: Original search term for the issuer
- `cusip`: Canonical CUSIP extracted from matching rows
- `top5_managers`: Manager names sorted by total value held (descending)
- `top5_accessions`: Corresponding accession numbers

## Workflow

### B1/B2: Single-Quarter Analysis

1. **Normalize and match fund names**
   - Normalize query: lowercase, remove punctuation, strip suffixes (see `references/normalization-rules.md`)
   - Compute Levenshtein distance between normalized query and each `FILINGMANAGER_NAME`
   - **MANDATORY: Validate match quality before proceeding:**
     - Distance ≤ 2: Good match, proceed
     - Distance 3-4: Marginal, verify manually or flag uncertainty
     - Distance > 4: **REJECT IMMEDIATELY** — output `matched_manager: null` and halt
   - **Semantic sanity-check**: Verify the matched name shares meaningful words or stems with the query. If "elliott" appears in query but not in matched name, the match is suspect regardless of distance.
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

1. **Match fund in both quarters**
   - Apply matching workflow separately for current and baseline quarters
   - Both matches must meet quality thresholds; if either fails, output null fields
   - May match same or different fund names across quarters

2. **Load holdings from both quarters**
   - Filter INFOTABLE for each quarter's accession number
   - Apply stock-like classification to both datasets
   - Build CUSIP → VALUE maps for each quarter

3. **Compute position changes**
   - For each CUSIP in current quarter:
     - Change = current_value - baseline_value (0 if absent in baseline)
   - Increased: positive changes, sort descending by change magnitude
   - Decreased: negative changes, sort ascending (most negative first)
   - New positions: CUSIPs in current but not in baseline, sort by current value descending

4. **Extract top N results**
   - Top 4 increased: first 4 from increased list
   - Top 3 decreased: first 3 from decreased list
   - Top 2 new: first 2 from new positions list

5. **Output JSON with B3 schema**

### B4: Issuer Ownership Rollup

Use when the task asks to find all managers/funds holding a specific issuer (inverse of fund-centric analysis).

1. **Find CUSIP for issuer**
   - Search `INFOTABLE.tsv` for issuer name match (case-insensitive grep on `NAMEOFISSUER`)
   - Issuer names vary: "PALANTIR TECHNOLOGIES INC", "Palantir Technologies Inc Ordinary Shares"
   - Extract `CUSIP` from matching rows — this is the canonical identifier
   - Verify CUSIP is consistent across matches (should be 9 characters)

2. **Aggregate holdings by accession**
   - Filter all rows matching the CUSIP
   - Sum `VALUE` by `ACCESSION_NUMBER`
   - Remember: VALUE is in thousands USD (multiply by 1000 for actual values)

3. **Rank by total value**
   - Sort accession numbers by aggregated value descending
   - Take top N (typically 5)

4. **Map accession to manager**
   - Join top accession numbers with `COVERPAGE.tsv` on `ACCESSION_NUMBER`
   - Extract `FILINGMANAGER_NAME` for each

5. **Output JSON with B4 schema**
   - Include original `issuer_query`, `quarter`, canonical `cusip`
   - `top5_managers` and `top5_accessions` arrays in corresponding order

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
  - If distance > 4, output `matched_manager: null` and halt — do not proceed with holdings analysis
- **Do NOT skip semantic sanity-check**
  - If query contains "elliott" and matched name has no "elliott", reject even if distance is marginal
- **Do NOT use Levenshtein-only matching without threshold validation**
  - The closest distance may still be a completely wrong match
- **Do NOT use substring-based stock classification**
  - `"stock" in title` misses SEC abbreviations like `COM`, `SHS`, `CL A`
- **Do NOT forget VALUE scaling**: multiply by 1000 (filings report in thousands USD)
- **Do NOT mix output schemas**: Use exactly one schema variant based on task type
- **Do NOT include non-stock positions in comparison**
  - Only compare stock-like holdings; exclude bonds, ETFs, etc.
- **Do NOT assume issuer names are normalized**
  - Search case-insensitively; issuer names have wide variation
  - Always use CUSIP as the canonical identifier after discovery

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

### B4: Issuer ownership rollup
- Issuer name search is fuzzy — use case-insensitive grep on NAMEOFISSUER
- CUSIP is the reliable identifier after discovery
- Aggregate VALUE by accession, then map to manager names
- VALUE scaling applies (multiply by 1000)
- Output both manager names and accession numbers for traceability

## Scripts

- `scripts/match_manager.py <query> <coverpage.tsv>`: Manager matching with threshold validation
- `scripts/classify_holdings.py <infotable.tsv> <accession_number>`: Deterministic stock classification and AUM computation
- `scripts/class_breakdown.py <infotable.tsv> <accession_number>`: Class distribution analysis (TITLEOFCLASS frequency)
- `scripts/compare_quarters.py <infotable_q1.tsv> <accession_q1> <infotable_q2.tsv> <accession_q2>`: Cross-quarter holdings comparison
- `scripts/issuer_rollup.py <issuer_query> <infotable.tsv> <coverpage.tsv>`: Find all managers holding a specific issuer

## References

- `references/normalization-rules.md`: Name normalization suffix list, edge cases, and semantic sanity-check examples
