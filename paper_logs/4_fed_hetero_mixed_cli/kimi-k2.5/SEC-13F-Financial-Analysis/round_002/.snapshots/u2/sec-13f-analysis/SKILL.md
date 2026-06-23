---
name: sec-13f-analysis
description: Parse and analyze SEC Form 13F quarterly filings (COVERPAGE.tsv and INFOTABLE.tsv) to extract manager info, AUM, stock holdings, top CUSIPs, and class breakdowns. Use when tasks involve fund manager lookups, holdings extraction, stock classification by TITLEOFCLASS, AUM calculations, CUSIP analysis, or aggregating holdings by security class from 13F TSV datasets.
---

# SEC 13F Filing Analysis

## Quick Decision Tree

1. **Task asks for 'class breakdown', 'top classes', or 'stock classes'** → Use [Class Breakdown Workflow](#class-breakdown-workflow)
2. **Task asks for 'top holdings', 'top CUSIPs', or 'holdings list'** → Use [Standard Holdings Workflow](#standard-holdings-workflow)
3. **Manager name not found** → Try [Word-Overlap Matching](#manager-name-matching) before declaring null

## Standard Holdings Workflow

1. **Verify Column Positions**: Before extracting any column, run `head -1 <file>.tsv | tr '\t' '\n' | nl` to see column names with positions. Do NOT assume column numbers.
2. **Locate Data**: Find `COVERPAGE.tsv` and `INFOTABLE.tsv` in the target quarter directory (e.g., `2025-q3/`).
3. **Filter by Quarter**: Use `REPORTCALENDARORQUARTER` in `COVERPAGE.tsv` (e.g., `30-SEP-2025` for Q3 2025).
4. **Match Manager**: See [Manager Name Matching](#manager-name-matching) below.
5. **Join Holdings**: Use matched `ACCESSION_NUMBER` to filter `INFOTABLE.tsv`.
6. **Classify Stocks**: Use tokenized matching on `TITLEOFCLASS` (see references/stock-classification.md).
7. **Calculate Metrics**:
   - `total_aum`: Sum of `VALUE` for all holdings.
   - `stock_holdings_count`: Count of rows classified as stock-like.
   - `stock_aum`: Sum of `VALUE` for stock-classified rows.
   - `top_cusips`: Sort stock holdings by `VALUE` descending, extract `CUSIP`.
8. **Output**: JSON with matched manager name and metrics. If no match, `manager: null` and `error: "No match found"`.

## Class Breakdown Workflow

Use when the task asks for "class breakdown", "top stock classes", "breakdown by security class", or output fields include `top_class_labels`/`top_class_counts`.

1. **Verify Column Positions**: `head -1 <file>.tsv | tr '\t' '\n' | nl` before extracting.
2. **Match Manager** as in standard workflow.
3. **If no match**: Return `manager: null`, `aum_total: null`, `top_class_labels: []`, `top_class_counts: []`.
4. **Filter to Stock Holdings**: Keep only rows where `is_stock_like(TITLEOFCLASS)` is true.
5. **Aggregate by Class**: Group by `TITLEOFCLASS`.
   - `stock_row_count`: Total count of stock rows.
   - `stock_cusip_count`: Count of unique `CUSIP` values in stock rows.
   - For each class: count of rows and sum of `VALUE`.
6. **Select Top N**: Sort classes by count (descending), take top N (typically 3).
7. **Output Schema**:
   ```json
   {
     "manager": "FILINGMANAGER_NAME",
     "aum_total": 12345678.0,
     "stock_row_count": 45,
     "stock_cusip_count": 40,
     "top_class_labels": ["COM", "CLASS A", "SHS"],
     "top_class_counts": [20, 15, 10]
   }
   ```

## Manager Name Matching

Normalization: lowercase, strip punctuation, remove suffixes (`LLC`, `INC`, `LTD`, `CORP`, `LP`, `CO`, `ADVISORY`, `MANAGEMENT`).

Matching priority (stop at first success):
1. **Exact normalized match**: `norm(query) == norm(candidate)`
2. **Substring match**: `norm(query) in norm(candidate)` OR `norm(candidate) in norm(query)`
3. **Word overlap**: Significant word intersection. Use Jaccard > 0.3 or at least one significant shared word not in stoplist (`the`, `and`, `of`, `associates`, `group`, `capital`, `partners`).
4. **Fuzzy**: Only if similarity > 0.85 AND no false positive risk (avoid matching "Headlands" to "Renaissance").

**No match handling**: If steps 1-4 fail, return `manager: null`. Do not force a match. Do not return zeros for AUM - return `null` or omit the field.

## Output Precision

Never round numeric values. Pass raw floats. The verifier's tolerance (often 1e-4) decides precision.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: Raw float values in JSON/Excel

## Known Invariants (by sub-task)

### sec-13f-manager-lookup
- Manager matching must try word-level overlap before falling back to fuzzy matching.
- If task expects a resolved manager and no exact/substring match exists, use word-level matching (shared words between query and manager name).
- Only return `null` if word-level matching also yields no overlap AND fuzzy ratio < 0.85.

### sec-13f-stock-classification
- Abbreviations `COM`, `SHS`, `CL A`, `CL B` are valid stock indicators.
- `ISHARES` contains "share" as substring but NOT as token — must be excluded.
- `TITLEOFCLASS` values like `U.S. REAL ES ETF` must be excluded via `etf` token.

### sec-13f-class-breakdown
- Output schema differs from standard holdings: uses `top_class_labels`/`top_class_counts` instead of `top_cusips`.
- `stock_row_count` counts rows; `stock_cusip_count` counts unique CUSIPs.

## Anti-Patterns

- **Do NOT** return zeros for AUM/counts when manager is not found. Return `null` or empty arrays.
- **Do NOT** use pure Levenshtein without word-token validation — yields false positives.
- **Do NOT** exclude abbreviations like `COM`, `CL A`, `SHS` from stock classification.
- **Do NOT** include ETFs/bonds in stock counts. Check `TITLEOFCLASS` tokens.
- **Do NOT** use substring matching for stock classification (`ISHARES` contains `SHARE` but is not stock). Use tokenized matching.
- **Do NOT** assume column positions — verify with `head -1 file.tsv | tr '\t' '\n' | nl` before extracting.

## Scripts

Run `python3 scripts/process_13f.py <data_dir> <manager_name> <quarter_date> [--analysis-type {holdings|class_breakdown}]`

- `holdings` (default): Outputs manager, total_aum, stock_aum, stock_holdings_count, top_cusips.
- `class_breakdown`: Outputs manager, aum_total, stock_row_count, stock_cusip_count, top_class_labels, top_class_counts.

## References

- `references/13f_schema.md`: Column definitions and join patterns.
- `references/stock-classification.md`: Token rules for stock-like identification.
- `references/matching_strategies.md`: Detailed manager matching strategies and examples.
- `references/output-schemas.md`: JSON schemas for different analysis types.
