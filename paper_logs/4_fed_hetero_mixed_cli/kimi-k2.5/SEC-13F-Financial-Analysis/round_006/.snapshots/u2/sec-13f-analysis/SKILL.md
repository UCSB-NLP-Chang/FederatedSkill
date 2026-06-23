---
name: sec-13f-analysis
description: Parse and analyze SEC Form 13F quarterly filings (COVERPAGE.tsv and INFOTABLE.tsv) for manager lookups, holdings extraction, AUM calculations, CUSIP analysis, cross-quarter shift screening, issuer ownership rollups, and manager-issuer grids. Use for tasks involving fund manager identification, quarterly holdings comparison, top holder analysis for specific securities, or multi-dimensional reconciliation across quarters.
---

# SEC 13F Filing Analysis

## Quick Decision Tree

1. **Multi-query task requiring comparisons + issuer checks + snapshot in single output** → Use [Cross-Quarter Reconciliation Workflow](#cross-quarter-reconciliation-workflow)
2. **Single quarter, needs top holdings/CUSIPs or AUM** → Use [Standard Holdings Workflow](#standard-holdings-workflow) + `scripts/process_13f.py`
3. **Compare same manager across two quarters** → Use [Shift Screening Workflow](#shift-screening-workflow) + `scripts/shift_screen.py`
4. **Find who owns a specific issuer/CUSIP** → Use [Issuer Ownership Rollup Workflow](#issuer-ownership-rollup-workflow) + `scripts/issuer_rollup.py`
5. **Grid of multiple managers vs multiple issuers** → Use [Manager-Issuer Grid Workflow](#manager-issuer-grid-workflow)

## Critical: Use Provided Scripts

For standard operations, **always use the provided scripts** rather than writing new analysis code:
- `python3 scripts/process_13f.py <dir> <manager> <date>` - Single quarter holdings
- `python3 scripts/shift_screen.py <curr_dir> <base_dir> <manager> <curr_date> <base_date>` - Cross-quarter comparison
- `python3 scripts/issuer_rollup.py <dir> <issuer/cusip> <date>` - Find managers holding a security

**Only write custom code** when the task requires combining multiple analysis types (e.g., comparison pairs + issuer checks + snapshot in one output).

## Critical Date Format Rule

**Always use the exact `REPORTCALENDARORQUARTER` value from the TSV (e.g., `30-JUN-2025`, `30-SEP-2025`).**
Do NOT pass quarter labels like `2025-q2` or `Q3 2025` to scripts or filters. Verify with:
`awk -F'\t' 'NR>1{print $2}' <dir>/COVERPAGE.tsv | sort -u`

## Critical Null Handling Rule

**When a manager is NOT FOUND, return `null` for all numeric fields, NOT empty strings or zeros.**

| Field Type | Manager Found | Manager NOT Found |
|------------|---------------|-------------------|
| CUSIP lists | `['037833100', ...]` | `[]` (empty array) |
| Numeric AUM/counts | `12345678.9` | `null` |
| String CUSIP (single) | `'037833100'` | `null` or omit field |
| Manager name | `'Manager LLC'` | `null` |

**Why this matters**: Empty strings (`""`) and zeros (`0`) imply the manager exists but has no data. `null` correctly signals the manager was not located in the dataset. Verifiers may reject outputs with wrong null semantics.

## Standard Holdings Workflow

1. **Run the script**: `python3 scripts/process_13f.py <data_dir> <manager_name> <quarter_date>`
2. **Validate output**: Check that `manager` field is not null and matches expected fund name
3. **If null returned**: Manager truly not present or name variation too extreme. Do NOT force a match.

## Shift Screening Workflow (Cross-Quarter Comparison)

1. **Run the script**: `python3 scripts/shift_screen.py <current_dir> <baseline_dir> <manager> <curr_date> <base_date>`
2. **Validate both quarters found**: If error field present, manager missing from that quarter
3. **Interpret results**:
   - `top4_increased_cusips`: Existing positions that grew (present in both quarters)
   - `new_positions_top2`: Positions not in baseline quarter
   - **Never** combine new and increased into same list

## Issuer Ownership Rollup Workflow

1. **Run the script**: `python3 scripts/issuer_rollup.py <data_dir> <issuer_name_or_cusip> <quarter_date>`
2. **Verify CUSIP resolution**: If queried by name, confirm `cusip` field matches expected security
3. **Check manager diversity**: If `top_managers` contains duplicates or seems thin, verify against raw INFOTABLE

## Cross-Quarter Reconciliation Workflow

Use when task requires multiple operation types in single output:
- Comparison pairs (fund Q-over-Q holdings changes)
- Issuer checks (top holders for specific securities)
- Snapshot checks (fund metadata/status for a quarter)

**Step-by-step**:
1. **Extract quarter dates**: Get exact `REPORTCALENDARORQUARTER` strings for each quarter
2. **Validate manager presence**: Check COVERPAGE for each fund in both quarters using conservative matching (see [False Positives to Avoid](#false-positives-to-avoid))
3. **Foreach comparison pair**:
   - If manager exists in both quarters: Run `scripts/shift_screen.py` and extract increased/decreased CUSIPs
   - If manager missing in either quarter: Set `largest_buy_cusip: null`, `largest_sell_cusip: null` (do not force match)
4. **For issuer checks**: Run `scripts/issuer_rollup.py` for each issuer
5. **For snapshot check**: Run `scripts/process_13f.py` and extract `stock_holdings_count`

**Output format**:
```json
{
  "comparison_pairs": [
    {"fund_query": "...", "largest_buy_cusip": "...", "largest_sell_cusip": "..."}
  ],
  "issuer_checks": [
    {"issuer_query": "...", "top_managers": [...], "top_accessions": [...]}
  ],
  "snapshot_check": {"fund_query": "...", "q3_stock_positions": N}
}
```

## Manager Name Matching

**Normalization**: lowercase, strip punctuation, remove suffixes.

**Extended stop words** (treat as noise for word-overlap matching):
- Original: `the`, `and`, `of`, `associates`, `group`, `capital`, `partners`, `management`, `advisory`, `investment`
- **Critical additions**: `global`, `asset`, `assets`, `wealth`, `financial`, `services`, `solutions`, `llc`, `inc`, `lp`

**Matching priority** (stop at first success):
1. **Exact normalized match**: `norm(query) == norm(candidate)`
2. **Substring match**: `norm(query) in norm(candidate)` OR `norm(candidate) in norm(query)`
3. **Significant word overlap**: Jaccard > 0.3 **AND** at least one non-stop word shared
4. **Fuzzy**: Only if ratio > 0.9 (raised from 0.85) AND no high-risk terms involved

**False Positives to Avoid** (observed in traces):
- `Sycomore Asset Management` ≠ `Scion Asset Management` (different firms, don't match on "Asset Management")
- `Voyager Global Management` ≠ `Tiger Global Management` (different firms, don't match on "Global Management")
- `Kinetic Partners Management` ≠ `Tiger Global Management` (different firms)

If candidate shares only generic words (global, asset, management, financial) with query, **reject match** unless stronger signal exists.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Known Invariants (by sub-task)

### sec-13f-manager-lookup
- Manager matching must try word-level overlap before falling back to fuzzy matching.
- Only return `null` if word-level matching also yields no overlap AND fuzzy ratio < 0.9.

### sec-13f-shift-screening
- CUSIPs are case-sensitive — do NOT lowercase for comparison.
- "Increased" and "New" are mutually exclusive categories.
- Manager names may vary slightly between quarters — match independently.
- **Null handling**: If manager not found in either quarter, return `null` for CUSIP fields, not empty strings.

### sec-13f-issuer-rollup
- CUSIP lookup via issuer name uses `NAMEOFISSUER` column.
- Same manager may have multiple accessions (amendments, separate filings).

### sec-13f-manager-issuer-grid
- VALUE is 0 (not null) when manager exists but doesn't hold the issuer.

## Anti-Patterns

- **Do NOT use `grep -i` for manager matching**: `grep -i "tiger"` matches "Tigertail Avenue" or "Voyager Global". Always normalize and tokenize as described in `references/matching_strategies.md`.
- **Do NOT match on shared generic words alone**: Two funds containing "Global" or "Asset Management" are not necessarily the same fund.
- **Do NOT return zeros for missing managers**: Return `null` to distinguish "not found" from "found but zero holdings".
- **Do NOT return empty strings (`""`) for CUSIP fields when manager not found**: Return `null` or omit the field.
- **Do NOT conflate increased and new positions**: Existing positions that grew vs positions that didn't exist in baseline are separate categories.
- **Do NOT pass `YYYY-qN` to scripts**: Always use exact `DD-MON-YYYY` date strings from COVERPAGE.
- **Do NOT force cross-quarter comparisons**: If manager only appears in one quarter, report `null` for comparison fields rather than guessing or using closest match.
- **Do NOT improvise output schemas**: If task specifies field names, use them; otherwise use canonical schemas from `references/output-schemas.md`.

## Scripts

`python3 scripts/process_13f.py <data_dir> <manager_name> <quarter_date> [--analysis-type {holdings|class_breakdown}]`
- Standard holdings extraction or class breakdown for single quarter.
- Returns null for all fields if manager not found.

`python3 scripts/shift_screen.py <current_dir> <baseline_dir> <manager_name> <current_quarter_date> <baseline_quarter_date>`
- Cross-quarter comparison with increased, decreased, and new position detection.
- Validates manager presence independently in each quarter (name may vary slightly).

`python3 scripts/issuer_rollup.py <data_dir> <issuer_name_or_cusip> <quarter_date>`
- Inverse lookup: managers holding a specific security.
- Accepts issuer name (case-insensitive grep on NAMEOFISSUER) or exact CUSIP.

`python3 scripts/compare_quarters.py <dir_baseline> <date_baseline> <dir_current> <date_current> <manager> [--top-n N]`
- Legacy comparison script. Prefer `shift_screen.py` for new tasks.

## References

- `references/13f_schema.md`: Column definitions, join patterns, data types.
- `references/matching_strategies.md`: Detailed matching algorithm, stop words list, threshold tuning, false positive examples.
- `references/output-schemas.md`: JSON schemas for all analysis types.
- `references/stock-classification.md`: TITLEOFCLASS token rules for stock vs ETF/bond differentiation.
