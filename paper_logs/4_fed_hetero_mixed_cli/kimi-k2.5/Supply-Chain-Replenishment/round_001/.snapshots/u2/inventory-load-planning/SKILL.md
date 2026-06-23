---
name: inventory-load-planning
description: Generate inventory load plans and replenishment schedules from Excel source data. Use for tasks involving days-on-hand calculations, projected stock-out dates, pallet requirements, or expedited delivery determination based on current inventory, sales velocity, and scheduled inbounds.
---

# Inventory Load Planning

## Workflow

1. **Prepare Environment**
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install pandas openpyxl
   ```

2. **Inspect Source Structure**
   - Source files often have metadata rows before headers (AsOfDate, HorizonEnd)
   - If `pd.read_excel()` returns wrong columns, use `header=None` and inspect raw rows
   - Data typically starts 2-3 rows down with actual headers in row 2

3. **Parse with Robust Pattern**
   - See `references/formulas.md` for calculation specifications
   - Use `scripts/load_calculator.py` for standard processing
   - Adjust row indices based on your specific file structure

## Critical Parsing Rule

When standard pandas reading fails (e.g., "ValueError: could not convert string to float"):

```python
# Read without headers first to inspect structure
raw = pd.read_excel(path, sheet_name='Stock Snapshot', header=None)

# Extract metadata from specific cells
as_of_date = pd.to_datetime(raw.iloc[0, 1])
horizon_end = pd.to_datetime(raw.iloc[0, 3])

# Skip to actual data (row 2=headers, row 3+=data)
data = raw.iloc[3:].copy()
data.columns = ['Item_Code', 'On_Floor_Cases', 'Daily_Sales', '_drop']
data = data.drop('_drop', axis=1).reset_index(drop=True)
```

## Core Calculation Sequence

1. **Days On Hand**: `On_Floor / Daily_Sales`
2. **Projected OOS**: `AsOfDate + floor(Days_On_Hand)`
3. **Planning Days**: `(HorizonEnd - AsOfDate).days`
4. **Remaining Demand**: `Daily_Sales * Planning_Days`
5. **Inbound by Horizon**: Filter inbounds where `Arrival_Date <= HorizonEnd`
6. **Additional Needed**: `max(0, Remaining_Demand - On_Floor - Inbound_By_Horizon)`
7. **Pallets**: `ceil(Additional_Needed / Cases_Per_Pallet)`
8. **Earlier Delivery Required**: `Required_Delivery < Earliest_Inbound_Date`

## Output Structure

- **Load_Detail**: All items with full calculation trace
- **Load_Action_Summary**: Filtered view where `Additional_Cases_Needed > 0`

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### excel-inventory-load-planning (B1)
- Source workbook structure: metadata rows precede headers in Stock Snapshot sheet
- AsOfDate typically in row 0 column B; HorizonEnd in row 0 column D
- Data headers at row index 2; data rows start at row index 3+
- Scheduled Inbounds sheet: headers at row 0, data starts row 1
- Load Config sheet: CasesPerPallet at cell A2 (or similar)
- Output must have exactly two sheets: Load_Detail (first), Load_Action_Summary (second)
- Load_Action_Summary includes only items where Additional_Cases_Needed > 0

## Anti-Patterns

- **Don't assume headers are in row 0**: The trace showed headers at index 2 with metadata above
- **Don't include header strings in calculations**: Filter out rows containing "On Floor" or "Item Code" before math operations
- **Don't allow negative Additional Needed**: Always apply `max(0, ...)`
- **Don't compare string dates**: Convert to datetime first
- **Don't use `date.timedelta`**: Import as `from datetime import timedelta`, not `date.timedelta`

## Validation Steps

- Verify Additional Cases Needed never negative
- Confirm pallet calculations use `math.ceil()`, not `round()`
- Check Earlier Delivery Required compares datetime objects
- Validate items with sufficient inbound coverage show Earlier Delivery Required = False

## References

- `references/formulas.md` - Complete formula specification with examples
- `scripts/load_calculator.py` - Reusable implementation template