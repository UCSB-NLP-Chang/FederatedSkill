---
name: recovery-tracker-generation
description: Create recovery planning workbooks from stock snapshots and recovery/transfer logs. Use when task involves reading Excel files with stock positions, recovery/inbound loads with status stages (Booked, Loaded, Tentative, Cancelled), and per-SKU pallet configurations; calculating days-on-hand, out-of-stock dates, and load requirements; and generating Coverage_Detail and Recovery_Loads outputs. Handles revision-based deduplication, stage filtering, and per-SKU pallet sizing. Trigger phrases: 'recovery tracker', 'load planning', 'stock recovery', 'replenishment plan', 'OOS date', 'days on hand', 'recovery loads', 'stage filtering', 'Booked/Loaded/Tentative'.
---

# Recovery Tracker Generation

Create recovery planning workbooks from stock snapshots and recovery/inbound logs with stage-based status filtering and per-SKU pallet sizing.

## Workflow

1. **Discover source structure with Python**
   - Use `openpyxl` or `pandas` - direct Read tool fails on binary .xlsx
   - List all sheet names and identify by content patterns:
     - Stock: Look for SKU, Units/Stock On Hand, Daily Rate/Demand
     - Recovery/Loads: Look for Load ID, SKU, Load Date/ETA, Units, Stage/Status, Revision
     - Pallet Guide: Look for SKU, Cases/Units Per Pallet (per-SKU sizing, not global)
   - Inspect first 5-10 rows to locate headers and metadata dates

2. **Extract planning parameters**
   - AsOfDate and HorizonEnd: Often in row 1-2 (cells B1, D1 or similar)
   - Header rows: Often row 2-3, not row 1
   - PlanningDays = (HorizonEnd - AsOfDate).days

3. **Handle per-SKU pallet sizing (critical)**
   - Look for Pallet Guide sheet with SKU → Cases/Units Per Pallet mapping
   - **NOT a single global value** - each SKU may have different pallet capacity
   - Build lookup dict: `pallet_size[sku] = cases_per_pallet`
   - Use per-SKU value for load calculations, not a default

4. **Parse stock data**
   - Extract SKU, Units On Hand, Daily Rate/Demand
   - Calculate: Current_Days_On_Hand = Units / Daily_Rate
   - Calculate: Projected_OOS_Date = AsOfDate + Current_Days_On_Hand days

5. **Handle recovery log deduplication by revision**
   - **Critical**: Recovery logs often have duplicate Load_IDs with different revisions
   - Deduplication rule: Keep row with **highest Revision** per Load_ID (not latest date)
   - Apply BEFORE status/stage filtering
   - After dedup, filter by Stage: **Only 'Booked', 'Loaded'** (exclude 'Tentative', 'Cancelled', 'Draft')

6. **Filter by horizon and calculate inbound units**
   - Filter to Load_Date <= HorizonEnd
   - Sum Units per SKU: Inbound_Units_By_Horizon

7. **Calculate per-SKU metrics**
   - Delivered_Days_On_Hand = (On_Hand + Inbound_Units) / Daily_Rate
   - Remaining_Demand = Daily_Rate * PlanningDays
   - Additional_Units_Needed = max(0, Remaining_Demand - On_Hand - Inbound_Units)
   - Loads_Required = ceil(Additional_Units_Needed / Pallet_Size[SKU])
   - Earlier_Delivery_Required = TRUE if no qualifying load arrives before Projected_OOS_Date

8. **Build output sheets**
   - **Coverage_Detail**: All SKUs with full calculated fields + metadata header (AsOfDate, HorizonEnd, PlanningDays)
   - **Recovery_Loads**: Filter to Loads_Required > 0

9. **Preserve sheet order and content**
   - Keep Instructions and Pallet Guide sheets unchanged
   - Clear and repopulate Coverage_Detail and Recovery_Loads only

## Stage Values Reference

| Stage | Include? | Notes |
|-------|----------|-------|
| Booked | ✓ | Firm commitment |
| Loaded | ✓ | Already staged/prepared |
| Tentative | ✗ | Not reliable |
| Cancelled | ✗ | Explicitly excluded |
| Draft | ✗ | Incomplete |

## Key Differences from Standard Load Planning

| Aspect | Recovery Tracker | Standard Load Planning |
|--------|---------------|------------------------|
| Pallet sizing | Per-SKU in Pallet Guide | Global Cases_Per_Pallet |
| Status column | Stage | Status/Booking State/Dock Status |
| Deduplication | By Revision (max) | By Transfer_Date (latest) |
| Terminology | Loads, Units | Pallets, Cases |
| Output names | Coverage_Detail, Recovery_Loads | Load_Detail, Load_Action_Summary |

## Data Quality Checks

- Skip rows with null/empty SKU
- Skip rows with null Revision (cannot deduplicate)
- Handle Load_Date parsing errors (skip malformed)
- Verify Pallet Guide contains all SKUs from stock sheet

## Anti-patterns

- **Do not** use a single global pallet size - always check for per-SKU Pallet Guide
- **Do not** deduplicate by date - use Revision for recovery logs
- **Do not** include Tentative or Cancelled stages in inbound sums
- **Do not** ignore Pallet Guide sheet - it's essential for correct load calculations

## Troubleshooting

- **Wrong load counts**: Verify per-SKU pallet sizing from Pallet Guide, not default
- **Missing expected loads**: Check stage filtering - may be including Tentative or not handling revision dedup
- **Dates off by one**: Verify datetime to date conversion consistency
- **Empty Recovery_Loads**: Check if Additional_Units_Needed threshold is too high or inbound sums wrong
