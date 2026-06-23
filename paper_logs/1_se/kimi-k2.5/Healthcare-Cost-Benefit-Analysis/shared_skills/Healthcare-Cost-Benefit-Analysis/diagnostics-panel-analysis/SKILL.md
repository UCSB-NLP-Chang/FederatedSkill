---
name: diagnostics-panel-analysis
description: Analyze diagnostic testing panel financials comparing replenishment cadence scenarios with network-tier payment adjustments, holdout exclusions, and lab override workflows. Use when task involves panel_manifest.json with service_clusters/panels hierarchy, holdouts.json exclusions, network_adjustments.csv for payment modifiers, shipper_cost.csv by class, contract_terms.csv with alias matching and effective date filtering, and lab_capacity_overrides.csv with revision/approval workflow. Common in clinical diagnostics networks, lab consortium pricing, and regional testing policy decisions. Output uses 'adopt_X_day' recommendation enum.
---

# Diagnostics Panel Analysis

Compare replenishment cadence scenarios for diagnostic testing panels with network-adjusted payments.

## Workflow

1. **Identify input files** - Look for:
   - `*manifest*.json` - Hierarchical `service_clusters` → `panels` structure
   - `*holdouts*.json` - Exclusion list by `panel_code` with `holdout_state`
   - `*network_adjustments*.csv` - Payment modifiers by `network_tier`
   - `*shipper_cost*.csv` - Logistics costs by `shipper_class`
   - `*contract_terms*.csv` - Base payments with `status_flag`, `effective_week`
   - `*lab_capacity_overrides*.csv` - Lab counts with `rev`/`approval` workflow

2. **Parse manifest structure**
   ```json
   {
     "service_clusters": [{
       "cluster_name": "core|specialty|...",
       "panels": [{
         "panel_code": "DP-XXX",
         "panel_name": "Panel Name",
         "alias_labels": ["ALIAS", "Alias-Name"],
         "reagent_cost_per_1000_tests_usd": 118.4,
         "network_tier": "metro|regional|rural",
         "shipper_class": "ambient_lab|cold_lab|frozen_lab",
         "tests_per_lab_per_run_14_day": 34,
         "tests_per_lab_per_run_28_day": 68,
         "default_active_labs": 15,
         "analysis_mode": "review|archive"
       }]
     }]
   }
   ```

3. **Apply scope filters** (in order):
   - **Holdout exclusion**: If `holdouts.json` present, exclude any `panel_code` with `holdout_state: "exclude"`
   - **Analysis mode**: Only include panels with `"analysis_mode": "review"`
   - **Exclude**: `"archive"` mode or held-out panels

4. **Resolve lab overrides** (approval workflow with empty value handling)
   - Group by `panel_code`
   - Filter to `approval: "approved"` rows only
   - Select highest `rev` (revision) among approved rows
   - **CRITICAL**: If `active_labs` is blank/null/empty, fall back to `default_active_labs`
   - Fall back to `default_active_labs` if no approved override exists
   - **Discard**: `draft`, `rejected`, `pending` rows

5. **Match contract payments** (alias + date filtering)
   - `panel_ref` in contracts uses aliases from `alias_labels`, not `panel_code`
   - Match case-insensitively: `panel_name` or any `alias_labels` entry
   - For multiple entries with `status_flag: "current"`, use latest `effective_week`
   - Build lookup: normalized alias → base_payment

6. **Join network adjustments**
   - Lookup: `network_tier` → `network_adjustment_per_run_per_lab_usd`
   - **Missing tier**: Default to 0.0 if network_tier not found in adjustments table

7. **Join shipper costs**
   - Lookup: `shipper_class` → `shipper_cost_usd`

8. **Calculate total payment per run**
   ```
   total_payment_per_run = base_payment_per_run + network_adjustment_per_run
   ```

9. **Calculate financials per panel**

   Annual reagent cost (constant across cadences):
   ```
   annual_tests = tests_per_lab_per_run × runs_per_year × active_labs
   annual_reagent_cost = annual_tests × reagent_cost_per_1000 / 1000
   ```

   Scenario calculations (14-day vs 28-day):
   ```
   runs_per_year_14 = 26  # 365/14 ≈ 26
   runs_per_year_28 = 13  # 365/28 ≈ 13
   
   annual_shipper_cost_14 = shipper_cost × runs_per_year_14 × active_labs
   annual_shipper_cost_28 = shipper_cost × runs_per_year_28 × active_labs
   
   annual_revenue_14 = total_payment × runs_per_year_14 × active_labs
   annual_revenue_28 = total_payment × runs_per_year_28 × active_labs
   
   annual_margin_14 = annual_revenue_14 − annual_reagent_cost − annual_shipper_cost_14
   annual_margin_28 = annual_revenue_28 − annual_reagent_cost − annual_shipper_cost_28
   ```

10. **Aggregate and recommend** (CRITICAL LOGIC)
    - Sum margins across all in-scope panels
    - **CRITICAL**: Recommendation must favor the BETTER scenario (higher margin), not just check threshold
    - Compare |margin_28 − margin_14| against threshold
    - **Recommendation enum**: This domain uses **`adopt_X_day`** not `keep_X_day`/`switch_to_X_day`
    - If margin_28 > margin_14 AND difference ≥ threshold: `adopt_28_day`
    - Else if margin_14 > margin_28 AND difference ≥ threshold: `adopt_14_day`
    - Else: `adopt_{current_better_scenario}_day` or per task specification

## Critical: Recommendation Logic

**The threshold determines IF to switch, but the sign determines WHICH direction.**

```python
# WRONG - only checks threshold
if abs_diff >= threshold:
    recommendation = 'adopt_28_day'  # Always adopts 28-day!

# CORRECT - checks both direction and threshold
if margin_28 > margin_14 and abs_diff >= threshold:
    recommendation = 'adopt_28_day'
elif margin_14 > margin_28 and abs_diff >= threshold:
    recommendation = 'adopt_14_day'
else:
    recommendation = 'adopt_14_day' if margin_14 > margin_28 else 'adopt_28_day'
```

## Critical Differences from Related Skills

| Aspect | Diagnostics Panel | Lab Reagent Kit | Logistics Dispatch |
|--------|-------------------|-----------------|-------------------|
| Input structure | `service_clusters` → `panels` | `regions` → `assays` | `service_groups` → `programs` |
| Exclusion file | `holdouts.json` | None | `suspensions.csv` |
| Scope filter | `analysis_mode: "review"` | `in_scope: true` | `review_flag: "review"` |
| Payment adjustment | `network_tier` addition | None | None |
| Payment formula | base + network_adjustment | direct match | direct match |
| Date filtering | `effective_week` | `effective_month` | `cycle_tag` |
| Recommendation | `adopt_X_day` | `keep_X`/`adopt_Y` | `keep_X`/`switch_to_Y` |
| Override empty handling | Fallback to default | Fallback to default | Fallback to default |

## Anti-Patterns

- **Don't recommend worse scenario** - If 28-day margin is negative and 14-day is positive, NEVER recommend adopt_28_day
- **Don't ignore holdouts.json** - Check for exclusion file before processing
- **Don't use panel_code for contract matching** - Use `alias_labels` and `panel_name`
- **Don't forget network adjustments** - Add to base payment for total payment
- **Don't assume missing network_tier means error** - Default adjustment to 0.0
- **Don't use first contract row** - Filter to `status_flag: "current"` and latest `effective_week`
- **Don't ignore empty active_labs** - Empty string in override means use default

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Negative margins for all panels | Forgot to add network adjustment to payment | Verify total_payment = base + network_adjustment |
| Wrong panel count | Holdout exclusions not applied | Check holdouts.json for `holdout_state: exclude` |
| Lab counts wrong | Empty override values not handled | Fall back to `default_active_labs` when active_labs is blank |
| Payment matching fails | Using panel_code instead of aliases | Match against `panel_name` and `alias_labels` |
| Recommendation rejects | Wrong enum format | Use `adopt_14_day`/`adopt_28_day`, not `keep_14_day` |
| Recommending worse scenario | Logic ignores which margin is higher | Check margin comparison, not just threshold |

## Verification Checklist

- [ ] Holdout exclusions applied (if holdouts.json exists)
- [ ] Only panels with `analysis_mode: "review"` are in scope
- [ ] Lab overrides: `approval=approved`, highest `rev`, fallback to default if empty
- [ ] Contract payments matched by alias, filtered to `current` status, latest `effective_week`
- [ ] Network adjustments added to base payment (default 0.0 if tier missing)
- [ ] Annual reagent cost identical across scenarios (sanity check)
- [ ] Recommendation favors higher margin scenario, not just checks threshold
- [ ] Recommendation enum uses `adopt_X_day` format
- [ ] All 4 required top-level keys present: `assumptions`, `panels`, `totals`, `recommendation`

## References

- See `references/panel-schemas.md` for variant manifest structures
- See `scripts/calculate_panel_margins.py` for reference implementation
