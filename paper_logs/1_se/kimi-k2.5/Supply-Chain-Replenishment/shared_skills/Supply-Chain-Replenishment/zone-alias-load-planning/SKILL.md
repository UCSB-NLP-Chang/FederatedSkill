---
name: zone-alias-load-planning
description: Create zone-based or route-based load planning workbooks when source data uses location/route aliases requiring mapping to canonical zones/routes. Use when task involves external alias-to-zone/route lookup tables, composite (Zone, SKU) or (Route, SKU) matching, revision-based deduplication of delivery/transfer records, record type filtering (e.g., DELIVERY/DISPATCH vs MESSAGE/COMMENT), per-location pallet sizing matrices, and multi-location stock coverage with gap identification. Trigger phrases: 'zone coverage', 'route coverage', 'location alias', 'canonical zone', 'canonical route', 'dispatch gap', 'zone/SKU', 'route/SKU', 'alias mapping', 'multi-zone planning', 'multi-route planning', 'location mapping', 'route alias map', 'pack matrix'.
---

# Zone/Route Alias Load Planning

Create zone-based or route-based planning workbooks when source data uses aliases requiring external canonical mapping and composite key matching.

## Workflow

1. **Discover source structure with Python**
   - Use `openpyxl` or `pandas` - direct Read tool fails on binary .xlsx
   - Identify four required data sources:
     - **Stock/Inventory**: Zone/Route, SKU, On Hand, Daily Demand
     - **Feed/Deliveries/Dispatch Queue**: Record Type, Dispatch/Queue ID, Revision, Zone/Route Alias, SKU Code, ETA/Ship Date, Units/Cases, State/Status
     - **Alias Key**: Alias → Canonical Zone/Route mapping table
     - **Pack Matrix** (route/zone variants): Route/Zone, SKU → Cases/Units Per Load/Pallet
   - Inspect first 5-10 rows of each to locate headers

2. **Extract planning parameters**
   - AsOfDate, HorizonEnd: Often in row 1 metadata (B1, D1 pattern) or stock sheet headers
   - PlanningDays = (HorizonEnd - AsOfDate).days

3. **Build alias mapping dictionary**
   - Load Alias Key/Route Alias Map sheet: columns 'Alias', 'Canonical Zone/Route'
   - Create lookup: `alias_map[alias] = canonical_zone`
   - **Critical**: Validate all feed aliases exist in map - skip unknowns with warning

4. **Build per-location pallet sizing (if Pack Matrix present)**
   - Load Pack Matrix: Route/Zone, SKU, Cases/Units Per Load
   - Create lookup: `pallet_size[(route, sku)] = cases_per_load`
   - Fall back to global default only if Pack Matrix absent

5. **Process feed data with filtering chain**
   Apply in strict order:
   1. **Record Type filter**: Keep only 'DELIVERY', 'DISPATCH', 'TRANSFER' rows; drop 'COMMENT', 'NOTE', 'MESSAGE'
   2. **Data quality**: Skip rows with null Dispatch/Queue ID, Revision, or Ship Date
   3. **Invalid date handling**: Skip rows where date parses as string (e.g., 'bad-date') or raises exception
   4. **Revision deduplication**: Keep row with **max Revision** per Dispatch/Queue ID
   5. **Status/State filter**: Keep only confirmed states ('Released', 'Approved', 'Confirmed', 'Staged'), exclude 'Pending', 'Hold', 'Tentative', 'Draft', 'Cancelled'
   6. **Alias resolution**: Map Zone/Route Alias → Canonical Zone/Route, skip unmapped
   7. **Horizon filter**: Keep Ship Date <= HorizonEnd
   8. **Null SKU filter**: Skip rows with null/empty SKU after alias resolution

6. **Build composite (Zone/Route, SKU) keys**
   - Stock: (Canonical Zone/Route, SKU)
   - Feed: (Mapped Canonical Zone/Route, SKU Code)
   - Match inbounds to stock using tuple keys, not individual fields

7. **Calculate per-location-SKU metrics**
   - Current_DOH = On_Hand / Daily_Demand (handle zero: use 1 or skip)
   - Projected_OOS_Date = AsOfDate + Current_DOH days
   - Inbound_Units = sum(Units where composite key matches and filters passed)
   - Delivered_DOH = (On_Hand + Inbound) / Daily_Demand
   - Remaining_Demand = Daily_Demand * PlanningDays
   - Additional_Needed = max(0, Remaining_Demand - On_Hand - Inbound)
   - Loads_Required = ceil(Additional_Needed / Pallet_Size[(Zone/Route, SKU)])
   - Earlier_Delivery_Required = TRUE if no inbound Ship Date < Projected_OOS_Date

8. **Build output sheets**
   - **Coverage_Detail/Zone_Coverage/Location_Coverage**: All zone/route-SKU pairs with metadata header
   - **Dispatch_Plan/Zone_Action_List/Dispatch_Gap_List**: Filter to Loads_Required > 0

9. **Preserve non-output sheets**
   - Keep Overview, Instructions, Pack Matrix, Route Alias Map unchanged
   - Clear and repopulate only calculation output sheets

## Alias Mapping Patterns

| Source Pattern | Detection | Handling |
|---------------|-----------|----------|
| Simple two-column | 'Alias', 'Canonical Zone/Route' headers | Direct dictionary load |
| Multi-alias per zone | Multiple rows, same canonical | All map to same zone/route |
| Case sensitivity | FRONT-A vs front-a | Normalize or match exactly per source |
| Unknown aliases in feed | Alias not in key table | Skip with warning, don't crash |
| Route-specific aliases | 'R100-A', 'NORTH-100' both → R-100 | Standard alias mapping |

## Record Type Filtering

Common feed structures include mixed record types:

| Record Type | Typical Meaning | Action |
|-------------|-----------------|--------|
| DELIVERY | Actual shipment | Keep and process |
| DISPATCH | Dispatch/shipment | Keep and process |
| TRANSFER | Inter-location move | Keep if relevant |
| COMMENT | Commentary | Exclude |
| MESSAGE | System messages | Exclude |
| NOTE | Metadata | Exclude |

## Status/State Values

| State | Include? | Notes |
|-------|----------|-------|
| Released | ✓ | Committed, firm |
| Approved | ✓ | Alternative firm state |
| Confirmed | ✓ | Alternative term |
| Staged | ✓ | Prepared for dispatch |
| Pending | ✗ | Not yet committed |
| Hold | ✗ | Suspended |
| Tentative | ✗ | Not reliable |
| Draft | ✗ | Incomplete |
| Cancelled | ✗ | Explicitly excluded |

## Per-Location Pallet Sizing

When Pack Matrix present:
- Use `pallet_size[(route, sku)]` lookup, not global default
- Common structure: Route, SKU, Cases Per Load
- Validate all stock (Route, SKU) pairs exist in matrix
- Fall back to global default only for missing pairs with warning

## Data Quality Patterns

| Issue | Detection | Handling |
|-------|-----------|----------|
| Invalid date string | `isinstance(date, str)` or parse error | Skip row |
| Null alias | `pd.isna(zone_alias)` | Skip row |
| Unknown alias | `alias not in alias_map` | Skip with warning |
| Null revision | `pd.isna(revision)` | Skip (can't dedupe) |
| Null SKU | `pd.isna(sku)` or empty string | Skip row |
| Duplicate IDs | Same ID, different revisions | Keep max revision |
| Zero units | Units = 0 | Include (confirms zero inbound) |

## Anti-patterns
- **Do not** assume zone/route names in feed match stock - always map via alias table
- **Do not** skip record type filtering - mixed feeds contain non-delivery rows
- **Do not** deduplicate by date - use Revision for delivery logs
- **Do not** ignore invalid ETA values - string dates cause parse exceptions
- **Do not** match on SKU alone - composite (Zone/Route, SKU) key required
- **Do not** apply status filter before revision deduplication
- **Do not** use global pallet size when Pack Matrix present
- **Do not** assume all aliases are known - handle unknowns gracefully

## Troubleshooting
- **All items showing Earlier_Delivery_Required=False unexpectedly**: Check if Pending/Hold states being included
- **Missing expected gaps**: Verify alias mapping - stock names may not match canonical
- **Wrong inbound totals**: Confirm revision deduplication order (max revision, not latest date)
- **Unknown alias warnings**: Expected if feed contains legacy/test aliases
- **Zero loads calculated**: Check Pack Matrix lookup vs global default
- **Date parsing errors**: Check for 'bad-date' strings or other invalid date formats

## Fallback Strategy
If zone/route matching fails:
1. Verify alias map loaded correctly (print dict sample)
2. Check for case sensitivity issues in names
3. Confirm composite key tuples match between stock and mapped deliveries
4. If alias table missing, try direct name matching as emergency fallback

## References
- See `references/variant_patterns.md` for tested route/zone configurations and terminology mapping
