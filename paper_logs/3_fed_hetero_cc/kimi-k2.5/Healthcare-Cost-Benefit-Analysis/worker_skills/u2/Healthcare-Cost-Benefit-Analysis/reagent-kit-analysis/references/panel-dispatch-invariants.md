# Panel Dispatch Invariants (B7)

This reference documents the diagnostic panel dispatch policy analysis variant.

## Known Sub-Task: harbor_diagpanel_14v28

### Decision Output
- Decision strings: `keep_14_day`, `switch_to_28_day`
- Margin difference field: `annual_margin_difference_28_minus_14_usd`

### Formula Parameters
- **Days per year**: UNRESOLVED — R8 tested both 364 (u0) and 365.0 (u1/u2), both failed (reward=0.6)
- **Runs per year**: `days_per_year / cycle_days` (exact float, NOT integer)
- **Reagent cost**: identical between cycles (same total annual tests)
- **Shipper cost scaling**: UNRESOLVED — R8 tested both ×runs (u0) and ×runs×labs (u1/u2), both failed

### Data Filtering Rules
1. **In-scope filter**: `analysis_mode == "review"` in panel manifest
2. **Holdout exclusion**: panels with `holdout_state == "exclude"` removed entirely
3. **Lab override rule**: highest approved `rev` with non-empty `active_labs` per `panel_code`
4. **Contract rule**: latest `effective_week` among `status_flag == "current"` per panel

### Entity Matching
- Match `panel_ref` in contracts CSV against `panel_name` OR `alias_labels[]`
- Case-sensitive exact match (verify per variant)

### Payment Calculation
- Total payment per run per lab = `base_payment + network_adjustment`
- Network adjustment: lookup by `network_tier`, default 0.0 if tier missing

### Output Files
- `diagpanel_policy_report.json`
- `diagpanel_policy_summary.md`

## Unresolved Issues from R8

1. **days_per_year**: Both 364 and 365.0 failed. Need to verify from task specification or try 360 (matching B4 cooler dispatch pattern).

2. **shipper cost scaling**: Both ×runs and ×runs×labs failed. Need to verify correct formula. Note that B4 (cooler dispatch) uses `cooler_cost × dispatches/year × sites` while B6 (vaxcrate dispatch) uses `crate_cost × dispatches/year` (NOT × clinics). This suggests shipper cost may follow B6 pattern (×runs only, NOT ×labs).

3. **Possible root cause**: The failure may not be in these formula parameters at all — could be in contract matching, network adjustment lookup, or output field names.

## Recommended Testing for R9

1. Test variant A: 365.0 days/year, shipper ×runs×labs (u2's approach)
2. Test variant B: 365.0 days/year, shipper ×runs only (u0's shipper formula with u2's days)
3. Test variant C: 360 days/year, shipper ×runs×labs (matching B4 cooler dispatch)
4. Verify contract matching logic against task spec field names
