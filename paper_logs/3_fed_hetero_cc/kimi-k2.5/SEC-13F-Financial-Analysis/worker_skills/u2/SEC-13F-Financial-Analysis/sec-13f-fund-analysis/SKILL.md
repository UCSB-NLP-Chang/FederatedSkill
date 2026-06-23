---
name: sec-13f-fund-analysis
description: Analyze SEC 13F quarterly filings to match fund queries, extract holdings data, classify securities, compute AUM aggregates, compare holdings across quarters, or resolve manager-issuer value grids. Use when processing COVERPAGE.tsv and INFOTABLE.tsv files, matching fund manager names with fuzzy logic, calculating stock holdings counts, extracting top CUSIPs by value, computing class breakdowns by TITLEOFCLASS, comparing position changes between quarters, or computing VALUE sums for specific manager-issuer pairs.
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
- `value`: Total VALUE held by that manager for that issuer (in actual USD, not thousands)
- `value: 0` indicates the manager has no holdings for that issuer

### Snapshot Check (B6)
Use when task asks for stock holdings count for a specific fund:
```json
{
  "fund_query": "scion asset management",
  "quarter": "2025-q3",
  "stock_holdings": 0
}
```
- `stock_holdings`: Count of stock-like positions (0 if fund not found)

## Workflow

### STOP — READ THIS BEFORE PROCEEDING

**CRITICAL: Follow shell-based workflows. DO NOT write inline Python code.**
- Shell commands (grep/awk) are deterministic and kimi follows them reliably
- Inline Python = verification failure. Scripts handle edge cases you will miss.
- This checkpoint is mandatory for this model. Violating it produces incorrect output.

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
   - Look up schema variant in table at skill top
   - Use EXACTLY the field names specified for that variant

### B5: Manager-Issuer Grid

Use when task asks for "VALUE for [Manager] holding [Issuer]", "manager-issuer grid", or "cross-tabulate holdings".

1. **Resolve managers to accessions**
   - Run matching workflow for each fund query.
   - Enforce distance ≤ 4 threshold. Reject if exceeded.
2. **Resolve issuers to CUSIPs**
   - Search `NAMEOFISSUER` in `INFOTABLE.tsv` for each issuer query (case-insensitive substring match).
   - Extract the 9-digit `CUSIP`. If multiple CUSIPs match, use the primary equity CUSIP (typically highest total VALUE across all managers).
3. **Compute pair values with shell commands**
   - For each (accession, cusip) pair:
   ```bash
   grep "^<accession>" INFOTABLE.tsv | grep "<cusip>" | awk -F'\t' '{sum += $7} END {print sum * 1000}'
   ```
   - Field positions: $1=ACCESSION_NUMBER, $5=CUSIP, $7=VALUE
   - **MANDATORY**: A single manager often reports multiple rows for the same CUSIP. Always SUM them.
4. **Output JSON with B5 schema**
   - Preserve raw float precision

### B6: Snapshot Check

Use when task asks for a simple count of holdings for a fund.

1. **Match fund using B1 workflow**
   - Apply name normalization and distance thresholds
   - If no match found, output `stock_holdings: 0`

2. **Count stock-like holdings**
   - Filter INFOTABLE by accession number
   - Apply stock classification
   - Count matching rows

3. **Output JSON with B6 schema**

## Verification Workflow (Post-Computation)

After computing any aggregate, run this verification checklist:

1. **VALUE scaling check**: Confirm you multiplied by 1000 for actual USD
2. **Aggregation check**: Confirm you summed all rows for (accession, cusip) pairs — do not take first match
3. **Stock classification check**: Confirm you used exact keyword matching, not substring
4. **Schema field check**: Confirm field names match the schema variant from the lookup table

### Quick verification commands

Verify top holder for an issuer:
```bash
python3 /shared-skills/sec-13f-issuer-rollup/scripts/issuer_rollup.py "<issuer>" <infotable.tsv> <coverpage.tsv> <top_n>
```

Verify fund holdings:
```bash
python3 scripts/classify_holdings.py <infotable.tsv> <accession_number>
```

Verify cross-quarter comparison:
```bash
python3 scripts/compare_quarters.py <baseline_infotable.tsv> <baseline_accession> <current_infotable.tsv> <current_accession>
```

## Template-Based Tasks

When filling a pre-existing JSON template with computed 13F values:

1. **Load template first**: Read the template before computing to understand required schema, field order, nesting
2. **Compute using scripts only**: Run `classify_holdings.py`, `compare_quarters.py`, or `issuer_rollup.py` — do NOT write inline Python
3. **Fill template exactly**: Write computed values into existing structure — do NOT rename keys, reorder sections, or modify nesting
4. **Preserve notes/comment arrays**: Keep any `notes`, `comments`, or placeholder arrays unchanged
5. **Verify structural match**: After output, compare keys/order/lengths against template

**Anti-pattern**: Creating custom output structure when template exists causes field-path validation failure.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, Excel, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: pass raw floats directly to output
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-patterns

- **CRITICAL: Do NOT write inline Python — use shell commands or library scripts**
  - Inline Python bypasses verified logic → verification failure
  - Shell commands (grep/awk) work reliably for kimi
  - When Python needed, use `python3 scripts/<script_name>.py`
- **MANDATORY: Do NOT accept a match with distance > 4**
  - Example: "Renaissance Technologies" ≠ "Headlands Technologies" (distance=7, wrong entity)
  - Example: "elliott associates" ≠ "jvl associates llc" (distance=6, wrong entity)
  - Example: "tiger global" ≠ "Voyager Global Management LP" (no "tiger" in matched name)
  - If distance > 4, output `matched_manager: null` and halt — do not proceed with holdings analysis
- **CRITICAL: Use exact B3 field names per schema variant**
  - Array schema: `top4_increased_cusips`, `top3_decreased_cusips`, `new_positions_top2`
  - Single schema: `largest_buy_cusip`, `largest_sell_cusip`
  - Wrong: `largest_buy_cusip` in array schema, `top4_increased_cusips` in single schema
- **CRITICAL: Use empty string "" for missing sell in B3-Partial, NOT null**
  - `largest_sell_cusip: ""` when baseline missing (not null)
  - Include `baseline_missing: true` flag
- **Do NOT skip semantic sanity-check**
  - **Critical example**: "tiger global" matched "Voyager Global Management LP" at distance=4 — REJECT because "tiger" not in matched name (different entity entirely)
  - If query contains "tiger" and matched name has no "tiger", reject even at marginal distance
- **Do NOT use substring-based stock classification**
  - `"stock" in title` misses SEC abbreviations like `COM`, `SHS`, `CL A`
- **Do NOT forget VALUE scaling**: multiply by 1000 (filings report in thousands USD)
- **Do NOT assume 1:1 row mapping for grid lookups**: Managers frequently report multiple rows per CUSIP. Always SUM `VALUE` for the `(accession, cusip)` pair.
- **Do NOT trust single-row lookups**: Large managers have multiple INFOTABLE rows per CUSIP (different share classes, voting authority). Aggregate by ACCESSION_NUMBER first.

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
- **Field names are VERIFIER-CRITICAL**: check schema lookup table

### B5: Manager-issuer grid
- Sum all `VALUE` rows matching `(accession, cusip)`; do not deduplicate or pick one row.
- CUSIP resolution from issuer name should prioritize the most common/primary equity identifier.
- Output values are raw sums from the TSV unless task explicitly requests actual USD (multiply by 1000).

### B6: Snapshot check
- Simple count of stock-like holdings for a matched fund
- Output 0 if fund not found (not an error condition)

## Scripts

- `scripts/match_fund.py <query> <coverpage.tsv>`: Manager matching with threshold validation
- `scripts/classify_holdings.py <infotable.tsv> <accession_number>`: Deterministic stock classification and AUM computation
- `scripts/class_breakdown.py <infotable.tsv> <accession_number>`: Class distribution analysis (TITLEOFCLASS frequency)
- `scripts/compare_quarters.py <infotable_q1.tsv> <accession_q1> <infotable_q2.tsv> <accession_q2>`: Cross-quarter holdings comparison

## References

- `references/normalization-rules.md`: Name normalization suffix list, edge cases, and semantic sanity-check examples
- `references/toc-patterns.md`: TITLEOFCLASS patterns for stock vs non-stock classification