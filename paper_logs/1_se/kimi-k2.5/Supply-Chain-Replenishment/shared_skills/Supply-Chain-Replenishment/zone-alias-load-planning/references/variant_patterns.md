# Zone/Route Alias Variant Patterns

## Pattern A: Zone-Based with Global Pallet Size
| Element | Location | Notes |
|---------|----------|-------|
| Stock | 'Zone Snapshot' | Zone, SKU, On Hand, Daily Demand |
| Feed | 'Delivery Feed' | Record Type, Dispatch Ref, Revision, Zone Alias, ETA, Units, Status |
| Alias Key | 'Zone Alias Map' | Alias → Canonical Zone |
| Pallet Size | Global default | Single Cases_Per_Pallet value |
| Composite key | (Zone, SKU) | Match stock to mapped feed |

## Pattern B: Route-Based with Per-Route-SKU Pack Matrix
| Element | Location | Notes |
|---------|----------|-------|
| Stock | 'Route Snapshot' | Route, SKU, On Hand Cases, Daily Demand |
| Feed | 'Dispatch Queue' | Row Type, Queue ID, Revision, Route Alias, SKU, Ship Date, Cases, Queue State |
| Alias Key | 'Route Alias Map' | Alias → Canonical Route |
| Pack Matrix | 'Pack Matrix' | Route, SKU, Cases Per Load (per-route-SKU sizing) |
| Composite key | (Route, SKU) | Match stock to mapped feed |
| Status values | Released, Approved, Pending, Draft, Cancelled | Released/Approved = include; Pending/Draft/Cancelled = exclude |

## Terminology Mapping

| Generic Term | Route Variant | Zone Variant |
|--------------|---------------|--------------|
| Location | Route | Zone |
| Alias | Route Alias | Zone Alias |
| Feed | Dispatch Queue | Delivery Feed |
| Record ID | Queue ID | Dispatch Ref |
| Date | Ship Date | ETA |
| Status | Queue State | Status/State |
| Pallet Sizing | Cases Per Load | Cases Per Pallet |
| Coverage Sheet | Coverage_Detail | Zone_Coverage |
| Action Sheet | Dispatch_Plan | Zone_Action_List |

## Status Value Equivalents

| Include? | Logistics | Route/Dispatch | Retail/Bakery |
|----------|-----------|----------------|---------------|
| ✓ | Committed | Released | Firm |
| ✓ | Arranged | Approved | Locked |
| ✓ | Confirmed | Confirmed | Booked |
| ✗ | Pending | Pending | Tentative |
| ✗ | Hold | Hold | Hold |
| ✗ | Draft | Draft | Draft |
| ✗ | Cancelled | Cancelled | Cancelled |

## Data Quality Checks by Variant

### Route/Dispatch Variant
- Row Type column: Filter to 'DISPATCH' only, exclude 'COMMENT'
- Queue State: Include 'Released', 'Approved'; exclude 'Pending', 'Draft', 'Cancelled'
- Ship Date: Check for 'bad-date' strings
- Route Alias: Map via Route Alias Map, skip unknowns
- Revision: Deduplicate to max revision per Queue ID

### Zone/Delivery Variant
- Record Type: Filter to 'DELIVERY', exclude 'NOTE', 'MESSAGE'
- Status: Include 'Released', 'Staged', 'Confirmed'
- ETA: Check for invalid date strings
- Zone Alias: Map via Zone Alias Map
- Revision: Deduplicate to max revision per Dispatch Ref
