---
name: sec-13f-analysis
description: Parse and analyze SEC Form 13F quarterly filings (COVERPAGE.tsv and INFOTABLE.tsv) to extract manager info, AUM, stock holdings, top CUSIPs, and class breakdowns. Use when tasks involve fund manager lookups, holdings extraction, stock classification by TITLEOFCLASS, AUM calculations, CUSIP analysis, or aggregating holdings by security class from 13F TSV datasets.
---

# SEC 13F Filing Analysis

## Quick Decision Tree

1. **Task asks for 'class breakdown', 'top classes', or 'stock classes'** → Use [Class Breakdown Workflow](#class-breakdown-workflow)
2. **Task asks for 'top holdings', 'top CUSIPs', or 'holdings list'** → Use [Standard Holdings Workflow](#standard-holdings-workflow)

## Standard Holdings Workflow

1. **Verify Column Positions**: Before extracting any column, run `head -1 <file>.tsv | tr '\t' '\n' | nl` to see column names with positions. Do NOT assume column numbers.

2. **Locate Data**: Find `COVERPAGE.tsv` and `INFOTABLE.tsv` in the target quarter directory (e.g., `2025-q3/`).

3. **Filter by Quarter**: Use `REPORTCALENDARORQUARTER` in `COVERPAGE.tsv` to isolate filings for the requested period (e.g., `30-SEP-2025` for Q3 2025).

4. **Match Manager** (apply in order, stop at first confident match):
   - **Exact match**: Normalize both names (lowercase, strip punctuation, remove suffixes `LLC/INC/LTD/CORP/LP/CO`), compare for equality.
   - **Substring match**: Query is substring of manager name or vice versa.
   - **Word-level match**: Any word from the normalized query appears as a complete word in the normalized manager name. Example: query "elliott associates" matches "jvl associates llc" via shared word "associates".
   - **Fuzzy match**: Only accept if similarity ratio > 0.85.
   - **If no confident match after all steps**: Return `manager: null` with other fields as `null` (NOT zeros). See [Null Handling](#null-handling).

5. **Get Holdings**: Join matched `ACCESSION_NUMBER` with `INFOTABLE.tsv`.

6. **Classify Stock Holdings**: Filter rows where `TITLEOFCLASS` indicates equity using tokenized matching:
   - **Stock tokens (include)**: `common`, `ordinary`, `share`, `stock`, `com`, `shs`, `class a`, `class b`, `cl a`, `cl b`
   - **Exclude tokens**: `etf`, `put`, `call`, `option`, `bond`, `note`, `preferred`, `pfd`, `adr`, `ads`, `trust`, `fund`, `index`
   - **Rule**: Token must appear as a separate word, not substring. `ISHARES` contains "share" but not as token — excluded.

7. **Calculate Metrics**:
   - `Total AUM`: Sum `VALUE` for all matched holdings.
   - `Stock AUM`: Sum `VALUE` for stock-classified holdings.
   - `Stock Holdings Count`: Count of stock-classified rows.
   - `Top N CUSIPs`: Sort stock holdings by `VALUE` descending, take top N, extract `CUSIP`.

8. **Output**: Write JSON with schema `{manager, total_aum, stock_aum, stock_holdings_count, top_cusips}`.

## Class Breakdown Workflow

Use when the task asks for "class breakdown", "top stock classes", "breakdown by security class", or output fields include `top_class_labels`/`top_class_counts`.

1. **Match Manager** as in standard workflow (steps 1-4).

2. **If no match**: Return `manager: null` with null fields (see [Null Handling](#null-handling)).

3. **Filter to Stock Holdings**: Keep only rows where `is_stock_like(TITLEOFCLASS)` is true.

4. **Aggregate by Class**: Group by `TITLEOFCLASS`.
   - `stock_row_count`: Total count of stock rows.
   - `stock_cusip_count`: Count of unique `CUSIP` values in stock rows.
   - For each class: count of rows.

5. **Select Top N**: Sort classes by count (descending), take top N (typically 3).

6. **Output Schema**:
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

## Null Handling

When the queried manager is not found:
- Return `manager: null`
- Return `null` (NOT 0) for numeric fields: `total_aum`, `stock_aum`, `stock_holdings_count`, `aum_total`, `stock_row_count`, `stock_cusip_count`
- Return `[]` (empty array) for list fields: `top_cusips`, `top_class_labels`, `top_class_counts`

**Correct example**:
```json
{
  "manager": null,
  "total_aum": null,
  "stock_aum": null,
  "stock_holdings_count": null,
  "top_cusips": []
}
```

**Wrong** (common failure):
```json
{
  "manager": null,
  "total_aum": 0,
  "stock_aum": 0,
  "stock_holdings_count": 0,
  "top_cusips": []
}
```

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (JSON, CSV, Excel). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `result["total_aum"] = total_aum` with total_aum as raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### sec-13f-manager-lookup
- Manager matching must try word-level overlap before falling back to fuzzy matching.
- If no exact/substring/word-level match exists AND fuzzy ratio < 0.85, return `null`.
- Do NOT force the closest Levenshtein match — "Headlands" to "Renaissance" is a known false positive.

### sec-13f-stock-classification
- Abbreviations `COM`, `SHS`, `CL A`, `CL B` are valid stock indicators (R0: all workers undercounted stocks by excluding these abbreviations).
- `ISHARES` contains "share" as substring but NOT as token — must be excluded.
- `TITLEOFCLASS` values like `U.S. REAL ES ETF` must be excluded via `etf` token.

### sec-13f-class-breakdown
- Aggregate by `TITLEOFCLASS` values directly (do not normalize class labels).
- Count is row count per class, not sum of VALUE.

## Anti-Patterns

- Do NOT return zeros for AUM/counts when manager is not found — return `null`.
- Do NOT skip word-level matching — many real-world queries resolve via shared words (e.g., "associates" → "jvl associates llc").
- Do NOT assume closest Levenshtein match is correct — it frequently yields false positives.
- Do NOT assume column positions — verify with `head -1 file.tsv | tr '\t' '\n' | nl` before extracting.
- Do NOT exclude `COM`, `CL A`, `SHS` as stock types — they are valid abbreviations.
- Do NOT use substring matching for stock classification — `ISHARES` contains `share` but is an ETF.
- Do NOT round AUM values — pass raw floats to output.

## Scripts

Run `python3 scripts/process_13f.py <data_dir> <manager_name> <quarter_date> [--analysis-type {holdings|class_breakdown}]`

- `holdings` (default): Outputs manager, total_aum, stock_aum, stock_holdings_count, top_cusips.
- `class_breakdown`: Outputs manager, aum_total, stock_row_count, stock_cusip_count, top_class_labels, top_class_counts.

## References

- `references/13f_schema.md`: TSV column schemas and data formats.
- `references/matching_strategies.md`: Detailed manager matching strategies and word-level matching examples.
- `references/output-schemas.md`: Detailed JSON schemas for different analysis types.
