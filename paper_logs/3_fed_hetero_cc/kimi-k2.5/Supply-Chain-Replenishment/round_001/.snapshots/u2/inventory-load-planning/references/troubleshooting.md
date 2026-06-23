# Troubleshooting Table for Inventory Load Planning

Common symptoms, root causes, and fixes observed in supply chain Excel processing.

| Symptom | Cause | Fix |
|---------|-------|-----|
| `TypeError: unsupported operand type(s) for -: 'NoneType' and 'NoneType'` | Date cell was `None` before arithmetic | Assert `cell.value is not None` and `isinstance(cell.value, (date, datetime))` before any date subtraction |
| "could not convert string to float" | Header text (e.g., "On Floor") mixed into data rows | Use `skiprows` based on raw inspection; don't assume `header=0` |
| Dates show as integers (e.g., 45474) | Excel serial dates not parsed | Use `pd.to_datetime(cell_value)` explicitly |
| Missing items in output | Merge/concat lost rows due to mismatched keys | Verify item list before and after joins; check column names match |
| Earlier delivery all True/False | Date comparison timezone issues or comparison direction wrong | Ensure all dates are naive or UTC; check logic: `earlier_required = not any(inbound_date < required_delivery_date)` |
| Division by zero | `DailySales == 0` for some items | Guard: `days_on_hand = on_floor / daily_sales if daily_sales > 0 else float('inf')` |
| Wrong pallet count | Using floor division instead of ceil | Use `math.ceil(cases / cases_per_pallet)` |
| Output file corrupt or empty | ExcelWriter not closed properly | Use `with pd.ExcelWriter(...) as writer:` or call `writer.close()` |