---
name: sec-13f-brief-refresh
description: Populate structured JSON briefs/templates with SEC 13F data by orchestrating existing analysis skills. Use when tasks require filling a multi-section report (fund snapshots, issuer leaders, quarter-over-quarter changes) from a provided JSON template.
---

# SEC 13F Brief/Report Template Filling

## Workflow
1. **Parse Template Structure**: Read the template JSON. Identify `section_id` values and required keys per item. Preserve all non-data fields (e.g., `notes`, `report_date` format, array structure).
2. **Route Sections to Existing Skills**:
   - `fund_snapshots` → Use `sec-13f-analysis` or `scripts/parse_13f.py`. Map `total_aum_thousands` → `aum`, `stock_holdings_count` → `stock_holdings`.
   - `issuer_leaders` → Use `sec-13f-issuer-rollup` or `scripts/issuer_rollup.py`. Map top manager name → `top_manager`.
   - `change_checks` → Use `sec-13f-quarter-comparison` or `scripts/compare_13f_quarters.py`. Compute largest positive/negative delta CUSIPs → `largest_buy_cusip`, `largest_sell_cusip`.
3. **VALUE Unit Verification**: Before populating `aum` or dollar amounts, verify the dataset's unit:
   - Sum `VALUE` for a known large fund. If total ~$10B–$100B, column is in **dollars**. If ~$10M–$100M, it's in **thousands**.
   - **Do not blindly multiply by 1,000**. Adjust based on magnitude check.
4. **Key Mapping & Validation**:
   - Copy exact key names from the template. Verifiers fail on key mismatches (e.g., `top_increased` vs `increased_cusips`).
   - Ensure numeric types match template expectations (int vs float).
   - Validate that `notes` and structural arrays are untouched.
5. **Output**: Write the filled JSON to the requested path. Validate with `python3 -c "import json; json.load(open('path'))"`.

## Anti-Patterns
- ❌ Blindly multiplying `VALUE` by 1,000 without magnitude verification.
- ❌ Changing template key names or removing placeholder fields.
- ❌ Using fuzzy matching for manager names in briefs; stick to exact normalized matches.
- ❌ Assuming all quarters exist; handle missing managers gracefully (0 holdings or empty strings).

## Scripts & References
- Run `scripts/fill_brief.py <template.json> <baseline_dir> <current_dir>` to automatically compute and populate standard brief sections. It handles unit detection, key mapping, and preserves template structure. Use when the template matches the standard `fund_snapshots`/`issuer_leaders`/`change_checks` layout.