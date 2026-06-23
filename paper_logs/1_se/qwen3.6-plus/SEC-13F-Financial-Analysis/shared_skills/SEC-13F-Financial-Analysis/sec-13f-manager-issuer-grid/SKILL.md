---
name: sec-13f-manager-issuer-grid
description: Compute holding values for a grid of manager-issuer pairs in a single SEC 13F quarter. Use when tasks ask for cross-tabulating fund positions, building a matrix of manager holdings across multiple stocks, or querying specific dollar amounts for multiple (manager, issuer) combinations.
---

# SEC 13F Manager-Issuer Grid Lookup

## Workflow
1. **Resolve Managers**: For each manager query, find the exact `ACCESSION_NUMBER` in `COVERPAGE.tsv`. Use normalized exact matching (lowercase, strip punctuation/suffixes like `LLC`, `INC`, `LP`). If multiple matches exist, pick the primary filing.
2. **Resolve Issuers**: For each issuer query, find the canonical `CUSIP` in `INFOTABLE.tsv`. Match `NAMEOFISSUER` case-insensitively. If multiple CUSIPs exist, pick the one with the highest total `VALUE` across all filings (typically the common stock).
3. **Aggregate Values**: For each (manager, issuer) pair, filter `INFOTABLE.tsv` by the manager's `ACCESSION_NUMBER` and the issuer's `CUSIP`. Sum the `VALUE` column.
   - **Note**: `VALUE` is reported in **thousands of USD**. Multiply by 1,000 if the task requires full dollar amounts.
   - Always sum across multiple rows for the same CUSIP per manager (e.g., different share classes or options).
4. **Format Output**: Return results as a grid, table, or JSON array matching the exact keys requested. Include `0` for missing pairs.

## Anti-Patterns
- ❌ Assuming `NAMEOFISSUER` matches exactly. Use substring/normalized matching.
- ❌ Picking the first CUSIP found for an issuer. Always verify it's the primary common stock CUSIP (highest aggregate value).
- ❌ Forgetting to sum `VALUE` across multiple rows for the same CUSIP.
- ❌ Treating `VALUE` as raw dollars without checking task requirements.
- ❌ Using fuzzy matching for manager names; stick to exact normalized matches to avoid false positives.

## Scripts & References
- Run `scripts/grid_lookup.py <infotable.tsv> <coverpage.tsv> <pairs.json>` to automate the entire grid computation. `pairs.json` should be an array of `{"manager": "...", "issuer": "..."}`. The script handles normalization, CUSIP resolution, aggregation, and outputs a JSON grid with values in thousands.
