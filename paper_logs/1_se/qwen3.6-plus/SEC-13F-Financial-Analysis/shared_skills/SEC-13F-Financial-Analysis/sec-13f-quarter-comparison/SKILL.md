---
name: sec-13f-quarter-comparison
description: Compare SEC 13F holdings across two quarters to identify increased, decreased, new, and exited positions. Use when tasks ask for fund shifts, portfolio changes, quarter-over-quarter deltas, or top movers between filing periods.
---

# SEC 13F Quarter-over-Quarter Comparison

## Workflow
1. **Match Manager in Both Quarters**: Locate the target manager in each quarter's `COVERPAGE.tsv`. Use exact normalized name matching (see `sec-13f-analysis` for normalization rules and distinctive-word matching). Record the `ACCESSION_NUMBER` for each quarter.
   - **Critical**: If the manager is not found in one quarter, do NOT force a fuzzy match. Treat the missing quarter as having zero holdings for that manager.
2. **Extract & Aggregate Holdings**:
   - Filter each quarter's `INFOTABLE.tsv` by its matched accession number.
   - **Sum `VALUE` by `CUSIP` per quarter**. Funds often report multiple rows for the same CUSIP (e.g., different share classes or sub-managers). Comparing raw rows will produce incorrect deltas.
   - Handle column variants: `VALUE`/`VALUEUSD`, `CUSIP`/`CUSIP_CODE`.
3. **Compute Deltas**:
   - `delta = Q_current_value - Q_baseline_value`
   - Classify positions: `increased` (delta > 0), `decreased` (delta < 0), `new` (in current, absent in baseline), `exited` (in baseline, absent in current).
   - If manager is missing from baseline: all current positions are `new`, no `exited` or `decreased`.
   - If manager is missing from current: all baseline positions are `exited`, no `new` or `increased`.
4. **Rank & Format Output**:
   - Sort by `delta` (or `abs(delta)` if requested).
   - Extract top N CUSIPs as specified.
   - **Match exact JSON keys** requested in the prompt. Verifiers often fail on key name mismatches (e.g., `top_increased` vs `increased_cusips`).
   - If reporting dollar amounts, multiply `VALUE` by 1,000 (SEC reports in thousands).

## CUSIP Resolution Note
When an issuer has multiple CUSIP variants (e.g., different share classes, ADRs, or legacy codes), resolve to the primary common stock CUSIP by picking the variant with the highest aggregate `VALUE` or row count across the quarter. Verify with `NAMEOFISSUER` substring matches to avoid cross-issuer collisions.

## Anti-Patterns
- ❌ Comparing raw row counts instead of summing `VALUE` by CUSIP.
- ❌ Ignoring `VALUE` unit (thousands) when calculating absolute dollar changes.
- ❌ Failing to match the manager in *both* quarters before comparing.
- ❌ Using fuzzy matching for manager names; stick to exact normalized matches or distinctive-word matching.
- ❌ Assuming output keys are generic; always copy the exact keys from the task prompt.
- ❌ Forcing a match when a manager is absent from one quarter → produces false buys/sells.

## Scripts & References
- Run `scripts/compare_13f_quarters.py` to automate aggregation, delta calculation, and JSON output. It handles CUSIP summation, column variants, and **gracefully handles missing quarters** by treating them as empty holdings.
- Refer to `sec-13f-analysis` for manager normalization, distinctive-word matching, and title classification rules.