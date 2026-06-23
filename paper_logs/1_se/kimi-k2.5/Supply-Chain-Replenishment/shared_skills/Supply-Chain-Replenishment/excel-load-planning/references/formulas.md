# Load Planning Calculation Reference

## Core Formulas

| Metric | Formula | Notes |
|--------|---------|-------|
| Current_Days_On_Hand | `On_Floor / Daily_Sales` | Round to 1-2 decimal places for display |
| Projected_OOS_Date | `AsOfDate + Current_Days_On_Hand days` | Stock-out date if no replenishment |
| Inbound_Cases_By_Horizon | `SUM(Cases_Due WHERE Arrival_Date <= HorizonEnd)` | Per item; filter by date |
| Delivered_Days_On_Hand | `(On_Floor + Inbound_Cases) / Daily_Sales` | DOH after receiving scheduled inbound |
| Remaining_Demand_Cases | `Daily_Sales * PlanningDays` | Total demand through horizon |
| Additional_Cases_Needed | `MAX(0, Remaining_Demand - On_Floor - Inbound_Cases_By_Horizon)` | Gap to fill |
| Pallets_Required | `CEILING(Additional_Cases_Needed / Cases_Per_Pallet)` | Always round up |
| Required_Delivery_Date | `Projected_OOS_Date` | Must arrive by this date |
| Earlier_Delivery_Required | `TRUE if NOT EXISTS(Inbound WHERE Arrival_Date < OOS_Date)` | FALSE only when replenishment precedes stock-out |

## Sheet Layouts

### Expected Source Sheets
- **Stock Snapshot**: Headers in row 3; AsOfDate in B1, HorizonEnd in D1
- **Scheduled Inbounds**: Headers row 1; Item, Arrival_Date, Cases_Due
- **Load Config**: Cases_Per_Pallet typically in A2

### Output Sheets
- **Load_Detail**: All calculated fields for analysis
- **Load_Action_Summary**: Filtered to Pallets_Required > 0; action-oriented columns

## Edge Cases
- Zero daily sales: Handle as 1 or exclude from planning (division by zero)
- Negative additional needed: Clamp to 0 (surplus scenario)
- Inbound exactly on OOS date: Consider "arrives same day" logic per business rules; typically requires Earlier_Required=TRUE if same-day doesn't prevent stock-out
