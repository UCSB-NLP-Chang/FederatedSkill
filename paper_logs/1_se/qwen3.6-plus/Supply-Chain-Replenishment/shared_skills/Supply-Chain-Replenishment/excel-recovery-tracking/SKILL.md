---
name: excel-recovery-tracking
description: Processes frozen meal or similar recovery/load tracking workbooks from template files, stock snapshots, and recovery logs. Use when tasked with generating coverage detail and recovery action sheets while preserving template structure, deduplicating loads by revision, filtering by stage (Booked/Loaded), and computing per-SKU load requirements with SKU-specific pallet configs. Handles template sheet preservation, revision-based deduplication, stage filtering, and metadata header rows in output sheets.
---

# Excel Recovery Tracking & Load Coverage

## Overview
Transforms a template workbook, stock snapshot, and recovery log into a populated recovery tracker. Preserves unmodified template sheets, deduplicates loads by keeping highest revision per Load ID, filters to valid stages, computes coverage metrics, and writes SKU-specific load requirements.

## Workflow
1. **Read Template Structure**: Load the template workbook first. Record sheet names and order. Identify which sheets are metadata/instructions (e.g., `Instructions`, `Pallet Guide`) vs calculation sheets (e.g., `Coverage_Detail`, `Recovery_Loads`).
2. **Read Source Data**:
   - **Stock Sheet**: Scan for `AsOfDate`, `HorizonEnd`, and data rows with `SKU`, `Units`/`OnHand`, `Daily Rate`/`Consumption`.
   - **Recovery Log**: Read columns `Load ID`, `Revision`, `SKU`, `Load Date`, `Units`, `Stage`/`Status`.
   - **Pallet Guide**: Read SKU-to-cases-per-pallet mapping (may be per-SKU, not global).
3. **Deduplicate Loads by Revision**:
   - Group recovery log entries by `Load ID`.
   - For each Load ID, keep only the row with the **highest Revision number**.
   - Discard lower-revision duplicates entirely.
4. **Filter by Stage**:
   - **Valid Stages**: `Booked`, `Loaded`, `Confirmed`, `Committed`, `Firm`.
   - **Invalid Stages**: `Tentative`, `Pending`, `Cancelled`, `Hold`, `Draft`, `Rejected`.
   - Only count loads with valid stages toward inbound coverage.
5. **Compute Per-SKU Metrics**:
   - `planning_days = (horizon_end - asof_date).days`
   - `days_oh = units_on_hand / daily_rate` (handle `daily_rate == 0` → set to `inf` or horizon+1)
   - `oos_date = asof_date + timedelta(days=days_oh)`
   - `inbound_units = sum(units for qualifying loads within horizon)`
   - `delivered_doh = (units_on_hand + inbound_units) / daily_rate` (if `daily_rate > 0`)
   - `remaining_demand = daily_rate * planning_days`
   - `additional_needed = max(0, remaining_demand - (units_on_hand + inbound_units))`
   - `loads_required = ceil(additional_needed / cases_per_pallet)` (use SKU-specific pallet config)
   - `earlier_delivery = True` if `inbound_units == 0` or earliest qualifying load date > `oos_date`
6. **Write Output Workbook**:
   - **Preserve sheet order** from template.
   - **Copy unmodified sheets** (Instructions, Pallet Guide) exactly as-is.
   - **Coverage_Detail**: Write metadata header rows first (`AsOfDate`, `HorizonEnd`, `PlanningDays`), then a blank row, then column headers, then data rows.
   - **Recovery_Loads**: Filter to `loads_required > 0`. Write column headers then data rows.
   - Ensure dates are formatted as `YYYY-MM-DD` strings or Excel date objects consistently.
   - Ensure booleans are explicit (`TRUE`/`FALSE` or Python `True`/`False`).

## Anti-Patterns & Pitfalls
- **Overwriting Template Sheets**: Never delete or reorder sheets from the template. Copy them first, then overwrite only calculation sheets.
- **Ignoring Revision Dedup**: Multiple rows with same Load ID but different revisions represent updates. Always keep highest revision; summing all rows double-counts.
- **Treating Stage as Status**: Recovery logs use `Stage` (Booked/Loaded/Tentative/Cancelled) not generic `Status`. Map accordingly.
- **Global Pallet Config**: Pallet cases may vary by SKU (read from Pallet Guide sheet), not a single workbook-wide value.
- **Metadata Header Rows**: Coverage_Detail often has 3-4 metadata rows before the actual table headers. Write these explicitly; do not start data at row 1.
- **Date Arithmetic**: Always use `timedelta(days=int)` when adding to dates. Never add raw integers.

## Helper Script
Use `scripts/calculate_recovery_tracker.py` for deterministic processing. It handles template preservation, revision dedup, stage filtering, SKU-specific pallet configs, and metadata header rows.
Run: `python3 scripts/calculate_recovery_tracker.py <template.xlsx> <stock.xlsx> <recovery_log.xlsx> <output.xlsx>`
⚠️ If column names deviate, adapt the `map_headers` targets or write inline following the workflow above.