# Load Planning Formula Reference

## Input Parameters

| Parameter | Description | Typical Source |
|-----------|-------------|----------------|
| AsOfDate | Planning baseline date | Row 0, Column B |
| HorizonEnd | End of planning period | Row 0, Column D |
| CasesPerPallet | Conversion factor | Load Config sheet |
| OnFloorCases | Current inventory | Stock Snapshot |
| DailySalesCases | Velocity rate | Stock Snapshot |
| ScheduledInbounds | Future arrivals | Scheduled Inbounds sheet |

## Calculation Specifications

### 1. Current Days On Hand
**Formula**: `OnFloorCases / DailySalesCases`

**Edge Cases**: 
- If DailySalesCases is 0, set to 999 to avoid division by zero
- Represents days until stock depletion at current velocity

### 2. Projected Stock-Out Date
**Formula**: `AsOfDate + floor(CurrentDaysOnHand)`

**Notes**:
- Use `math.floor()` to round down to whole days
- Add as `pd.DateOffset(days=floor_value)` if using pandas

### 3. Planning Days
**Formula**: `(HorizonEnd - AsOfDate).days`

### 4. Inbound Cases By Horizon
**Formula**: `Sum(CasesDue) where ArrivalDate <= HorizonEnd`

**Implementation**:
```python
item_inbounds = inbounds[inbounds['Item_Code'] == item]
inbound_by_horizon = item_inbounds[
    item_inbounds['Arrival_Date'] <= horizon_end
]['Cases_Due'].sum()
```

### 5. Remaining Demand Cases
**Formula**: `DailySalesCases * PlanningDays`

### 6. Additional Cases Needed
**Formula**: `max(0, RemainingDemand - OnFloorCases - InboundByHorizon)`

**Critical**: Never return negative values. Use `max(0, result)`.

### 7. Pallets Required
**Formula**: 
- If AdditionalCasesNeeded > 0: `ceil(AdditionalCasesNeeded / CasesPerPallet)`
- Else: 0

### 8. Earlier Delivery Required
**Formula**: `RequiredDeliveryDate < EarliestInboundDate`

**Where**:
- RequiredDeliveryDate = ProjectedOOSDate
- EarliestInboundDate = min(ArrivalDate) for the item (None if no inbounds)

**Logic**: TRUE if the stock-out happens before any scheduled inbound arrives.

## Example Walkthrough

**Given**:
- AsOfDate: 2025-08-01, HorizonEnd: 2025-08-31
- Item: SNK-101, OnFloor: 240, DailySales: 28.5
- CasesPerPallet: 80
- Inbound: 200 cases arriving 2025-08-10

**Step-by-step**:
1. Current DOH: 240 / 28.5 = 8.42 days
2. Projected OOS: 2025-08-01 + 8 = 2025-08-09
3. Planning Days: 30
4. Inbound by Horizon: 200 (arrives before 2025-08-31)
5. Remaining Demand: 28.5 × 30 = 855
6. Additional Needed: max(0, 855 - 240 - 200) = 415
7. Pallets: ceil(415 / 80) = 6
8. Earlier Delivery: 2025-08-09 < 2025-08-10 = TRUE