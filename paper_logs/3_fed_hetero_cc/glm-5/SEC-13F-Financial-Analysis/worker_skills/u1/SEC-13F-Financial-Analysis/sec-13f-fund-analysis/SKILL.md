---
name: sec-13f-fund-analysis
description: Analyze SEC 13F quarterly filings to match fund queries, extract holdings data, classify securities, compute AUM aggregates, compare holdings across quarters, perform issuer ownership rollups, and build manager-issuer grids. Use when processing COVERPAGE.tsv and INFOTABLE.tsv files, matching fund manager names with fuzzy logic, calculating stock holdings counts, extracting top CUSIPs by value, computing class breakdowns by TITLEOFCLASS, comparing position changes between quarters, finding all managers holding a specific issuer, querying specific issuer holdings for specific managers, or filling structured report templates with 13F-derived data.
---

# SEC 13F Fund Analysis

Process quarterly 13F filings to match fund queries and extract holdings metrics.

## SCHEMA LOOKUP TABLE — READ FIRST

Before outputting JSON, determine which schema variant the task requires:

| Task wording | Schema variant | Field names to use |
|--------------|----------------|-------------------|
| "top 4 increased" / "top 3 decreased" / "top 2 new" | B3-Array | `top4_increased_cusips`, `top3_decreased_cusips`, `new_positions_top2` |
| "largest buy" / "largest sell" (singular) | B3-Single | `largest_buy_cusip`, `largest_sell_cusip` |
| Fund missing in baseline quarter | B3-Partial | `largest_buy_cusip`, `largest_sell_cusip: ""`, `baseline_missing: true` |
| "how many holdings" / "stock holdings count" | B6-Snapshot | `stock_holdings` |
| "top N managers" for issuer | B4-TopN | `topN_manager_names` |
| Pre-existing JSON template to fill | B8-Template | Preserve template keys/order exactly |

**CRITICAL: Use EXACTLY ONE schema. Wrong field names = verification failure.**

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

### Cross-Quarter Comparison - Array (B3-Array)
Use when task asks for "top 4 increased", "top 3 decreased", "top 2 new positions":
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
- **Field names are VERIFIER-CRITICAL** — do NOT use `largest_buy_cusip` here

### Cross-Quarter Comparison - Single (B3-Single)
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
- **Field names are VERIFIER-CRITICAL** — do NOT use `top4_increased_cusips` here

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

### Issuer Check - Top N Variant (B4-TopN)
Use when task specifies exact number of top managers (e.g., "top 2 managers"):
```json
{
  "issuer_query": "microsoft",
  "quarter": "2025-q3",
  "top2_manager_names": ["VANGUARD GROUP INC", "BlackRock, Inc."]
}
```
- Adjust field name to match requested count: `top2_manager_names`, `top3_manager_names`, etc.

### Manager-Issuer Grid (B5)
Use when task asks for holdings of specific issuers for specific managers (cross-product query):
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
   - Both matches must meet quality thresholds; if either fails, handle as partial/missing
   - May match same or different fund names across quarters

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

3. **Load holdings from both quarters**
   - Filter INFOTABLE for each quarter's accession number
   - Apply stock-like classification to both datasets
   - Build CUSIP → VALUE maps for each quarter

4. **Compute position changes**
   - For each CUSIP in current quarter:
     - Change = current_value - baseline_value (0 if absent in baseline)
   - Increased: positive changes, sort descending by change magnitude
   - Decreased: negative changes, sort ascending (most negative first)
   - New positions: CUSIPs in current but not in baseline, sort by current value descending

5. **Extract top N results**
   - For array output: Top 4 increased, Top 3 decreased, Top 2 new
   - For single-value output: Largest buy (max positive change), Largest sell (most negative change)

6. **Output JSON with appropriate B3 schema**
   - Look up schema variant in SCHEMA LOOKUP TABLE at skill top
   - Use EXACTLY the field names specified for that variant

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
   - Take top N (typically 5, or as specified by task)

4. **Map accession to manager**
   - Join top accession numbers with `COVERPAGE.tsv` on `ACCESSION_NUMBER`
   - Extract `FILINGMANAGER_NAME` for each

5. **Output JSON with B4 schema**
   - Include original `issuer_query`, `quarter`, canonical `cusip`
   - Use `topN_managers` and `topN_accessions` arrays matching requested count

### B5: Manager-Issuer Grid

Use when the task asks for specific issuer holdings for specific managers (cross-product of managers × issuers).

1. **Match all managers first**
   - Apply B1 matching workflow for each fund query
   - Collect accession numbers for all successfully matched managers
   - If a manager fails to match, include entry with null accession and zero values

2. **Find CUSIPs for all issuers**
   - Search `INFOTABLE.tsv` for each issuer name (case-insensitive on `NAMEOFISSUER`)
   - Extract canonical CUSIP for each issuer
   - Cache CUSIPs to avoid redundant lookups

3. **Query each manager-issuer pair**
   - For each (accession, CUSIP) pair:
     - Grep INFOTABLE for rows matching both accession and CUSIP
     - Sum VALUE column for matching rows
     - Multiply by 1000 (values are in thousands USD)

4. **Build grid output**
   - For each manager, create entry with all issuer values
   - Use `value: 0` for issuers not held by that manager

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

### B7: Multi-Alert Processing

1. **Parse & Deduplicate Alerts**
   - Read the alert list
   - Remove exact duplicates based on alert type and query parameters
   - Preserve first-seen order for output assembly
   - Filter out distractors (e.g., alerts with `ignore_me`, invalid CUSIPs)

2. **Route to Sub-Skills**
   - `issuer_top_holders` → Run B4 workflow (issuer rollup)
   - `fund_change` → Run B3 workflow (cross-quarter comparison)
   - Other types → Apply appropriate B1-B6 workflow

3. **Assemble Output**
   - Group results by alert type
   - Maintain original deduplicated order
   - Output as a single JSON object with keys matching alert types

### B8: Template-Based Report Filling

When the task provides a pre-existing JSON template, structure, or report format to fill in:

1. **Load the template first**
   - Read the template JSON before computing any values
   - Understand: required schema, section order, item order, key names
   - Identify which values need to be filled

2. **Compute values using scripts ONLY**
   - Use one of these scripts — do NOT write inline Python:
     - `scripts/match_manager.py` for fund matching
     - `scripts/classify_holdings.py` for stock classification/AUM
     - `scripts/compare_quarters.py` for cross-quarter comparison
     - `scripts/issuer_rollup.py` for issuer ownership rollup
     - `scripts/class_breakdown.py` for TITLEOFCLASS distribution
   - **WHY**: Scripts handle VALUE scaling, header-aware parsing, stock classification edge cases. Inline code misses these and causes verification failure.

3. **Fill template structure exactly**
   - Preserve: section order, item order, key names, nesting
   - Keep existing `notes` arrays and comment fields unchanged
   - Replace placeholder values with computed results only

4. **Verify structural match**
   - After writing output, compare keys/order/array lengths against template
   - All keys must match exactly (no added/removed/renamed keys)

5. **Verify value precision**
   - Numeric values must be raw floats (no `round()`, no `format()`)

## Composite Tasks

Some tasks combine multiple analysis types. Process each sub-task independently:

1. **Identify sub-tasks**: Parse task for multiple query types (e.g., issuer rollups + fund changes)
2. **Execute each sub-task**: Apply appropriate workflow (B1-B7) for each
3. **Deduplicate results**: If same query appears multiple times, keep first-seen result
4. **Combine outputs**: Structure as top-level object with arrays for each query type

Example composite output:
```json
{
  "issuer_top_holders": [...],
  "fund_change": [...]
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

- **MANDATORY: Do NOT accept a match with distance > 4**
  - Example: "Renaissance Technologies" ≠ "Headlands Technologies" (distance=7, wrong entity)
  - Example: "elliott associates" ≠ "jvl associates llc" (distance=6, wrong entity)
  - If distance > 4, output `matched_manager: null` and halt — do not proceed with holdings analysis
- **Do NOT skip semantic sanity-check**
  - If query contains "elliott" and matched name has no "elliott", reject even if distance is marginal
  - **Critical example**: "tiger global" matched "Voyager Global Management LP" at distance=4 — REJECT because "tiger" not in matched name (different entity entirely)
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
- **Do NOT assume 1:1 row mapping for grid lookups**: Managers frequently report multiple rows per CUSIP. Always SUM `VALUE` for the `(accession, cusip)` pair.
- **Do NOT output null for missing sell when baseline exists**: Use empty string `""` only when baseline is missing; if baseline exists but no sells, still output the CUSIP with most negative change
- **Do NOT write inline Python for data processing**: Use provided scripts. Inline code misses VALUE scaling, header shifts, classification edge cases.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Test fails despite correct-looking output | Used inline Python or awk instead of scripts | Re-run using `match_manager.py`, `classify_holdings.py`, `compare_quarters.py`, or `issuer_rollup.py` |
| VALUE sums are off by 1000x | Forgot to multiply by 1000 | Apply `* 1000` scaling to all VALUE aggregations |
| Wrong manager matched | Distance > 4 or semantic mismatch | Enforce distance ≤ 4; verify key words appear in matched name |
| Wrong B3 field names | Used wrong schema variant | Check SCHEMA LOOKUP TABLE; use `largest_buy_cusip` for single, `top4_increased_cusips` for array |
| Template structure mismatch | Modified section/item order or key names | Load template first; write values into existing structure without reordering |
| CUSIP lookup returns wrong results | Used awk with fixed column indices | Use `csv.DictReader` or Python scripts with header-aware parsing |
| Inline Python verification fails | Script not invoked correctly | Run `python3 scripts/<script>.py` with correct arguments per script docs |

## Known invariants (by sub-task)

### B1: 13F fund match + holdings
- VALUE column is in thousands USD — must multiply by 1000 for actual AUM
- CUSIPs are 9 characters; pad with leading zeros if needed
- If no acceptable match exists, output `matched_manager: null` and halt (do not force wrong match)

### B2: Class breakdown analysis
- Count stock-like rows only (same classification logic as standard analysis)
- Distinct CUSIPs: unique CUSIP values among stock-like rows
- Top 4 classes: by frequency, ties broken alphabetically by label (lowercase)

### B3: Cross-quarter comparison
- Only stock-like holdings are compared (apply classification to both quarters)
- New positions: CUSIPs present in current quarter but absent in baseline
- Position changes computed as: current_value - baseline_value
- VALUE scaling applies to both quarters (multiply by 1000)
- **Missing baseline**: If fund not found in baseline, all current positions are "new"; largest buy = largest current position; largest sell = empty string
- **Field names are VERIFIER-CRITICAL**: check SCHEMA LOOKUP TABLE

### B4: Issuer ownership rollup
- Issuer name search is fuzzy — use case-insensitive grep on NAMEOFISSUER
- CUSIP is the reliable identifier after discovery
- Aggregate VALUE by accession, then map to manager names
- VALUE scaling applies (multiply by 1000)

### B5: Manager-issuer grid
- This is a cross-product query: N managers × M issuers
- Each manager must be matched independently using B1 workflow
- Each issuer must be looked up independently to find CUSIP
- VALUE scaling applies (multiply by 1000)

### B6: Snapshot check
- Simple count of stock-like holdings for a matched fund
- Output 0 if fund not found (not an error condition)

### B8: Template-based report filling
- Template structure is authoritative — never modify keys/order/nesting
- Scripts handle edge cases; inline code does not

## Scripts

**IMPORTANT: Use these scripts instead of inline Python or awk. Scripts handle VALUE scaling, header-aware parsing, and stock classification edge cases correctly.**

- `scripts/match_manager.py <query> <coverpage.tsv>`: Manager matching with threshold validation
- `scripts/classify_holdings.py <infotable.tsv> <accession_number>`: Deterministic stock classification and AUM computation
- `scripts/class_breakdown.py <infotable.tsv> <accession_number>`: Class distribution analysis (TITLEOFCLASS frequency)
- `scripts/compare_quarters.py <infotable_q1.tsv> <accession_q1> <infotable_q2.tsv> <accession_q2>`: Cross-quarter holdings comparison
- `scripts/issuer_rollup.py <issuer_query> <infotable.tsv> <coverpage.tsv>`: Find all managers holding a specific issuer

## References

- `references/normalization-rules.md`: Name normalization suffix list, edge cases, and semantic sanity-check examples