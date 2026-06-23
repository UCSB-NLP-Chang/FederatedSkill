# Known Invariants by Sub-Task

## harbor_diagpanel_14v28 (14-day vs 28-day diagnostic panel cadence)

### Decision Strings
- `keep_14_day` — when 14-day margin is higher OR difference below threshold
- `switch_to_28_day` — when 28-day margin is higher AND difference exceeds threshold

### Field Names
- Margin difference: `annual_margin_difference_28_minus_14_usd`
- Total margin 14-day: `total_annual_margin_14_day_usd`
- Total margin 28-day: `total_annual_margin_28_day_usd`

### Runs Per Year
- 14-day: `365.0 / 14 = 26.071428571428573` (exact float, NOT integer 26)
- 28-day: `365.0 / 28 = 13.035714285714286` (exact float, NOT integer 13)

### Override Resolution Rules
- Column names: `panel_code`, `rev`, `approval`, `active_labs`
- Filter: `approval == "approved"`
- Skip: blank `rev` OR blank `active_labs`
- Select: highest numeric `rev` per panel_code
- Fallback: `default_active_labs` from manifest

### Contract Resolution Rules
- Match: `panel_ref` against `alias_labels[]` or `panel_name` (case-insensitive)
- Filter: `status_flag == "current"`
- Select: latest `effective_week` (descending lexicographic sort, e.g., 2026-W22 > 2026-W10)
- Do NOT sum multiple records

### Network Adjustment Rules
- Join: `network_tier` from manifest to network_adjustments CSV
- Total payment: `base_payment_per_run_per_lab_usd + network_adjustment_per_run_per_lab_usd`
- Default: 0.0 if network_tier not found

### Holdout Filtering
- Exclude panels where `holdout_state: "exclude"` in holdouts JSON
- Include panels where `holdout_state: "clear"` or not in holdouts

### In-Scope Filter
- `analysis_mode: "review"` in panel manifest
- Exclude `analysis_mode: "archive"` and other values

### Output Files
- JSON: `diagpanel_policy_report.json`
- Markdown: `diagpanel_policy_summary.md`

## Common Errors

### Override Resolution Errors
- Using highest `rev` overall instead of highest approved `rev`
- Not skipping blank `rev` rows
- Not skipping blank `active_labs` rows
- Forgetting fallback to `default_active_labs`

### Contract Resolution Errors
- Case-sensitive matching when aliases are case-insensitive
- Summing multiple contract records instead of picking latest
- Using earliest `effective_week` instead of latest
- Not filtering for `status_flag == "current"`
- Matching by `panel_code` instead of `alias_labels[]`

### Calculation Errors
- Forgetting to add network_adjustment to base_payment
- Using integer runs/year (`26`, `13`) instead of exact float division
- Incorrect shipper cost scaling (formula unresolved)

### Precision Errors
- Rounding values before JSON output
- Using integer division instead of float division
- Fixed-format output (e.g., `.2f`) instead of raw floats

## Formula Uncertainty (R8)

### Unresolved Issues
Both u0 and u1/u2 approaches failed with reward=0.6:
1. **Days per year**: 364 (u0) vs 365 (u1/u2) — neither verified
2. **Shipper cost formula**: × runs only (u0) vs × runs × labs (u1/u2) — neither verified

### Recommendation for R9
Test both variants in R9 to determine correct formula:
- Variant A: 364 days/year, shipper × runs only
- Variant B: 365 days/year, shipper × runs × labs

The skill uses 365 days/year and shipper × runs × labs as the default approach.
If R9 fails, consider switching to the alternative formula.
