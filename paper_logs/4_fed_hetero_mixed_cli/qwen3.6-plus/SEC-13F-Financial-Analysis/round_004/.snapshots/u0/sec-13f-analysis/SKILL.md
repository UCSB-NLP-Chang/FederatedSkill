---
name: sec-13f-analysis
description: Parse and analyze SEC Form 13F quarterly filings (COVERPAGE.tsv and INFOTABLE.tsv) to extract manager info, AUM, stock holdings, top CUSIPs, class breakdowns, issuer ownership rollups, and cross-quarter holding shifts. Use when tasks involve fund manager lookups, holdings extraction, stock classification by TITLEOFCLASS, AUM calculations, CUSIP analysis, aggregating holdings by security class, finding top holders for a specific issuer, or comparing portfolio changes between two quarters.
---

# SEC 13F Filing Analysis

## Quick Decision Tree

1. **Task asks for 'class breakdown', 'top classes', or 'stock classes'** → Use [Class Breakdown Workflow](#class-breakdown-workflow)
2. **Task asks for 'top holdings', 'top CUSIPs', or 'holdings list'** → Use [Standard Holdings Workflow](#standard-holdings-workflow)
3. **Task asks for 'quarterly shift', 'portfolio changes', 'increased/decreased', 'new positions', or 'cross-quarter'** → Use [Cross-Quarter Comparison Workflow](#cross-quarter-comparison-workflow)
4. **Task asks for 'top holders', 'issuer ownership', 'who owns [Company]', or 'CUSIP rollup'** → Use [Issuer Ownership Rollup Workflow](#issuer-ownership-rollup-workflow)

## Critical Date Format Rule

**Always use the exact `REPORTCALENDARORQUARTER` value from the TSV (e.g., `30-JUN-2025`, `30-SEP-2025`).**
Do NOT pass quarter labels like `2025-q2` or `Q3 2025` to scripts or filters. If unsure, run:
`awk -F'\t' 'NR>1{print $2}' <dir>/COVERPAGE.tsv | sort -u` to find the exact string.

## Standard Holdings Workflow

1. **Verify Column Positions**: Before extracting any column, run `head -1 <file>.tsv | tr '\t' '\n' | nl` to see column names with positions. Do NOT assume column numbers.
2. **Locate Data**: Find `COVERPAGE.tsv` and `INFOTABLE.tsv` in the target quarter directory.
3. **Filter by Quarter**: Use `REPORTCALENDARORQUARTER` in `COVERPAGE.tsv` to isolate filings.
4. **Match Manager** (apply in order, stop at first confident match):
   - **Exact match**: Normalize both names (lowercase, strip punctuation, remove suffixes `LLC/INC/LTD/CORP/LP/CO`), compare for equality.
   - **Substring match**: Query is substring of manager name or vice versa.
   - **Word-level match**: Any word from the normalized query appears as a complete word in the normalized manager name.
   - **Fuzzy match**: Only accept if similarity ratio > 0.85.
   - **If no confident match**: Return `manager: null` with other fields as `null` (NOT zeros).
5. **Get Holdings**: Join matched `ACCESSION_NUMBER` with `INFOTABLE.tsv`.
6. **Classify Stock Holdings**: Filter rows where `TITLEOFCLASS` indicates equity using tokenized matching:
   - **Include tokens**: `common`, `ordinary`, `share`, `stock`, `com`, `shs`, `class a`, `class b`, `cl a`, `cl b`
   - **Exclude tokens**: `etf`, `put`, `call`, `option`, `bond`, `note`, `preferred`, `pfd`, `adr`, `ads`, `trust`, `fund`, `index`
   - **Rule**: Token must appear as a separate word, not substring. `ISHARES` contains "share" but not as token — excluded.
7. **Calculate Metrics**: `Total AUM`, `Stock AUM`, `Stock Holdings Count`, `Top N CUSIPs`.
8. **Output**: Write JSON with schema `{manager, total_aum, stock_aum, stock_holdings_count, top_cusips}`.

## Class Breakdown Workflow

1. **Match Manager** as in standard workflow.
2. **Filter to Stock Holdings**: Keep only rows where `is_stock_like(TITLEOFCLASS)` is true.
3. **Aggregate by Class**: Group by `TITLEOFCLASS`. Count rows per class.
4. **Select Top N**: Sort classes by count (descending), take top N.
5. **Output Schema**: `{manager, aum_total, stock_row_count, stock_cusip_count, top_class_labels, top_class_counts}`

## Cross-Quarter Comparison Workflow

Use when comparing a manager's portfolio between two quarters to find increased/decreased positions, new entries, or dropped holdings.

1. **Identify Exact Dates**: Use the Critical Date Format Rule to find `REPORTCALENDARORQUARTER` for both quarters.
2. **Match Manager Independently in Each Quarter**: Manager names may vary slightly between filings (e.g., "LLC" vs "LP"). Run matching logic separately for each quarter.
3. **Extract Stock Holdings for Both Quarters**: Use same `is_stock_like()` classification logic.
4. **Build CUSIP-to-Value Maps**: Create dictionaries mapping `CUSIP` → `VALUE` for each quarter. **Preserve CUSIP case (do NOT lowercase).**
5. **Calculate Changes**:
   - **Increased**: CUSIPs present in BOTH quarters where current_value > baseline_value. Sort by (current - baseline) descending.
   - **Decreased**: CUSIPs present in BOTH quarters where current_value < baseline_value. Sort by (baseline - current) descending.
   - **New**: CUSIPs in current ONLY (not found in baseline). Sort by current_value descending.
   - **Exited**: CUSIPs in baseline ONLY (not found in current). Sort by baseline_value descending.
6. **Run Comparison Script**:
   `python3 scripts/shift_screen.py <current_dir> <baseline_dir> <manager_name> <current_date> <baseline_date>`
7. **Output Schema**: See references/output-schemas.md for exact field names (e.g., `top4_increased_cusips`, `top3_decreased_cusips`).

**Critical Logic Separation**:
- **"Increased"** = existing position that grew (CUSIP in both quarters, value increased)
- **"New"** = position didn't exist before (CUSIP only in current quarter)
- Do NOT include new positions in the increased list

## Issuer Ownership Rollup Workflow

Use when finding which managers hold the most of a specific issuer or CUSIP (reverse lookup).

1. **Resolve CUSIP**: If not provided, search `INFOTABLE.tsv` for the issuer name:
   `awk -F'\t' 'NR>1 && tolower($3) ~ /<issuer>/ {print $5}' <dir>/INFOTABLE.tsv | sort -u`
   Verify the returned CUSIP matches the expected company.
2. **Aggregate by Manager**: Filter `INFOTABLE.tsv` for the CUSIP and sum `VALUE` grouped by `ACCESSION_NUMBER`.
   `awk -F'\t' 'NR>1 && $5 == "<CUSIP>" {val[$1]+=$7} END {for (a in val) printf "%s\t%.0f\n", a, val[a]}' <dir>/INFOTABLE.tsv | sort -t$'\t' -k2 -rn`
3. **Map to Managers**: Take top N `ACCESSION_NUMBER`s and join with `COVERPAGE.tsv` to get `FILINGMANAGER_NAME`.
   **CRITICAL**: Always verify `COVERPAGE.tsv` column positions with `head -1 <dir>/COVERPAGE.tsv | tr '\t' '\n' | nl` before extracting. `FILINGMANAGER_NAME` is typically column 10, but schema variations occur. Do NOT hardcode column indices.
4. **Output**: Construct JSON with `{issuer, cusip, topN_holders: [{manager, accession, aggregated_value}]}`.

## Null Handling

When the queried manager is not found:
- Return `manager: null`
- Return `null` (NOT 0) for numeric fields.
- Return `[]` (empty array) for list fields.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f"`
- DO: Pass raw float values in JSON/Excel

## Known invariants (by sub-task)

### sec-13f-manager-lookup
- Manager matching must try word-level overlap before falling back to fuzzy matching.
- Do NOT force the closest Levenshtein match — it frequently yields false positives.

### sec-13f-stock-classification
- Abbreviations `COM`, `SHS`, `CL A`, `CL B` are valid stock indicators.
- `ISHARES` contains "share" as substring but NOT as token — must be excluded.
- `TITLEOFCLASS` values like `U.S. REAL ES ETF` must be excluded via `etf` token.

### sec-13f-class-breakdown
- Aggregate by `TITLEOFCLASS` values directly (do not normalize class labels).
- Count is row count per class, not sum of VALUE.

### sec-13f-cross-quarter-shift
- CUSIP matching is case-sensitive (do NOT lowercase CUSIPs before comparison).
- Manager names may vary between quarters — match independently in each quarter.
- "Increased" and "New" are mutually exclusive categories.

### sec-13f-issuer-rollup
- CUSIP lookup via issuer name uses `NAMEOFISSUER` column (column 4 in 1-indexed, column 3 in 0-indexed).
- VALUE column is column 7 (1-indexed) or column 6 (0-indexed).
- Same manager may have multiple accessions (amendments, separate filings) — aggregate if needed.

## Anti-Patterns

- Do NOT return zeros for AUM/counts when manager is not found — return `null`.
- Do NOT skip word-level matching.
- Do NOT assume column positions — verify with `head -1`.
- Do NOT exclude `COM`, `CL A`, `SHS` as stock types.
- Do NOT use substring matching for stock classification.
- Do NOT round AUM values.
- Do NOT pass `YYYY-qN` formats to scripts; always use `DD-MON-YYYY`.
- Do NOT lowercase CUSIPs — case matters for matching.
- Do NOT conflate "increased positions" with "new positions".
- Do NOT hardcode COVERPAGE column indices for manager names — always verify header layout first.

## Scripts

- `scripts/process_13f.py`: Single-quarter analysis. Run `python3 scripts/process_13f.py <data_dir> <manager_name> <quarter_date> [--analysis-type {holdings|class_breakdown}]`
- `scripts/shift_screen.py`: Cross-quarter delta analysis. Run `python3 scripts/shift_screen.py <current_dir> <baseline_dir> <manager_name> <current_date> <baseline_date>`
- `scripts/issuer_rollup.py`: Issuer-centric analysis (optional helper). Run `python3 scripts/issuer_rollup.py <data_dir> <issuer_name_or_cusip> <quarter_date>`

## References

- `references/13f_schema.md`: TSV column schemas and data formats.
- `references/matching_strategies.md`: Detailed manager matching strategies and word-level matching examples.
- `references/output-schemas.md`: Detailed JSON schemas for different analysis types including shift screening.