---
name: sec-13f-fund-analysis
description: Analyze SEC 13F quarterly filings to match fund queries, extract holdings data, classify securities, compute AUM aggregates, compare holdings across quarters, or build manager-issuer grids. Use when processing COVERPAGE.tsv and INFOTABLE.tsv files, matching fund manager names with fuzzy logic, calculating stock holdings counts, extracting top CUSIPs by value, computing class breakdowns by TITLEOFCLASS, comparing position changes between quarters, or querying specific issuer holdings for specific managers.
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
    },
    {
      "fund_query": "third point",
      "quarter": "2025-q3",
      "issuer_queries": [
        {"issuer_query": "amazon", "cusip": "023135106", "value": 616991700},
        {"issuer_query": "palantir", "cusip": "69608A108", "value": 0}
      ]
    }
  ]
}
```
- Each entry in `manager_issuer_grid` contains one manager and their holdings for all queried issuers
- `value`: Total VALUE held by that manager for that issuer (in actual USD, not thousands)
- `value: 0` indicates the manager has no holdings for that issuer

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

3. **Query each manager-issuer pair with shell commands**
   - For each (accession, CUSIP) pair, use direct grep with awk for targeted queries:
   ```bash
   grep "^<accession>" INFOTABLE.tsv | grep "<cusip>" | awk -F'\t' '{sum += $7} END {print sum * 1000}'
   ```
   - Field positions: $1=ACCESSION_NUMBER, $5=CUSIP, $7=VALUE
   - Sum VALUE column for matching rows
   - Multiply by 1000 (values are in thousands USD)

4. **Build grid output**
   - For each manager, create entry with all issuer values
   - Use `value: 0` for issuers not held by that manager
   - Preserve original query strings for traceability

5. **Output JSON with B5 schema**
   - `manager_issuer_grid` array with one entry per manager
   - Each entry contains `fund_query`, `quarter`, and `issuer_queries` array

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, Excel, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
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

### B5: Manager-issuer grid
- This is a cross-product query: N managers × M issuers
- Each manager must be matched independently using B1 workflow
- Each issuer must be looked up independently to find CUSIP
- VALUE scaling applies (multiply by 1000)
- Zero value indicates manager has no holdings for that issuer
- Direct grep queries are efficient for targeted lookups (avoids loading full dataset)
- Each manager may have multiple INFOTABLE rows per CUSIP (different share classes, voting authority) — sum them

## Scripts

- `scripts/match_manager.py <query> <coverpage.tsv>`: Manager matching with threshold validation
- `scripts/classify_holdings.py <infotable.tsv> <accession_number>`: Deterministic stock classification and AUM computation
- `scripts/class_breakdown.py <infotable.tsv> <accession_number>`: Class distribution analysis (TITLEOFCLASS frequency)
- `scripts/compare_quarters.py <infotable_q1.tsv> <accession_q1> <infotable_q2.tsv> <accession_q2>`: Cross-quarter holdings comparison

## References

- `references/normalization-rules.md`: Name normalization suffix list, edge cases, and semantic sanity-check examples