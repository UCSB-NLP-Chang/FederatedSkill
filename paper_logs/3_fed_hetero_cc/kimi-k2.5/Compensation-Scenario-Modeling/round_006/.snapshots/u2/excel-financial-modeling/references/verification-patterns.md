# Verification Patterns for Excel Workbooks

## Common Test Assertions
- `assert wb.sheetnames == expected_order`
- `assert "Exact Label" in [cell.value for cell in ws['A']]`
- `assert len(wb.defined_names.definedName) == expected_count`
- `assert "=SUM(" in ws.cell(row=107, column=col).value`

## Formula Construction Tips
- Cross-sheet: `f"='{sheet_name}'!{cell_ref}"`
- Conditional: `f"=IF({ref}=0,0,({ref2}-{ref})/{ref})"`
- Always quote sheet names if they contain spaces, hyphens, or parentheses.

## Data Migration Checks
- `assert len(roster_rows) == source_count`
- `assert len(set(ids)) == len(ids)` (no duplicates)
- Verify YOS projection logic: `Yr+1 = YOS + 1`, `Yr+2 = YOS + 2`
