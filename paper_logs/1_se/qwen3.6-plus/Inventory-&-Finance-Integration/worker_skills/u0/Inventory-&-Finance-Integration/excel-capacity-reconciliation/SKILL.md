---
name: excel-capacity-reconciliation
description: Builds Excel workbooks for datacenter/cloud capacity reconciliation, vendor rollforwards, and financial control blocks. Use when tasks require multi-sheet workbooks with beginning balance + adds - amortization rollforwards, monthly control blocks (Totals, Ending Balance, Variance, GL Balance), cross-sheet summary aggregation, and strict legacy node/verifier checks.
---

# Excel Capacity Reconciliation & Rollforward

## Workflow
1. **Initialize Workbook**: 
   - `wb = openpyxl.Workbook()`
   - `wb.remove(wb.active)` (Remove default sheet immediately)
   - Create **Summary sheet first**, then detail sheets. Do not use `wb.move_sheet()`.
2. **Parse Inputs**: Extract vendor lists, beginning balances, monthly adds/amortization, and GL ledger balances.
3. **Build Detail Sheets**: One sheet per pool/account.
   - **Header Row**: Typically Row 5. Define column layout explicitly.
     - *Interleaved Pattern*: `Vendor | Beg Bal | Jan Adds | Jan Amort | Jan End | Feb Adds | ...`
     - *Grouped Pattern*: `Vendor | Beg Bal | Jan Adds | Feb Adds | ... | Jan Amort | ...`
     - Calculate column indices dynamically: `col_idx = base + (month_idx * stride) + offset`.
   - **Data Rows**: Start at Row 6. Store all monetary values as Python `float`.
   - **Control Rows**: Place immediately after last vendor row (`ctrl_start = 6 + num_vendors`).
     - `Month Totals`: `=SUM(Adds_Col_First:Adds_Col_Last)`
     - `Ending Balance`: `=SUM(End_Col_First:End_Col_Last)` (or chain monthly if required)
     - `Variance`: `=Ending_Balance - GL_Balance`
     - `GL Balance`: Hardcoded ledger values.
   - **Total Column**: Often the last column (e.g., Col O). Reference the final month's control row: `=N13`.
4. **Build Summary Sheet**:
   - Aggregate control rows from detail sheets using cross-sheet references.
   - Formula syntax: `='Detail Sheet Name'!CellRef`. **Always quote sheet names containing spaces or `#`**.
   - Maintain exact row spacing (often one blank row between blocks).
5. **Formatting**: Apply `#,##0.00` to currency columns. Ensure all numeric values are Python `float`.
6. **Save & Verify**: `wb.save(path)`. Run `scripts/verify_rollforward.py <path>` immediately after saving.

## Critical Rules for Legacy Node Checks
- **Exact Row/Column Alignment**: Verifiers check specific row indices. Do not shift rows. Use dynamic calculation for control rows but verify final indices.
- **Formula Syntax**: Always prefix formulas with `=`. Never write cell references as plain strings (e.g., write `'=N13'`, not `'N13'`).
- **Cross-Sheet References**: Must match exact sheet names: `='Compute Pool #8100'!D12`. Include single quotes if sheet names contain spaces or `#`.
- **Data Types**: All monetary values must be `float`. Booleans must be `True`/`False`. Dates as `datetime.date` or `YYYY-MM-DD` strings.
- **Blank Rows**: Control blocks are often separated by exactly one blank row. Explicitly write `None` or `""` to prevent `openpyxl` from miscounting `max_row`.
- **No `data_only=True` for generation**: Write formulas as strings. `data_only=True` is only for reading pre-calculated files.

## Troubleshooting & Anti-Patterns
- **Sheet Order**: Always create Summary first. `wb.move_sheet()` is brittle and often leaves artifacts or fails legacy checks.
- **Default Sheet Leftover**: Failing to remove `wb.active` immediately causes structural verifier failures.
- **Column Layout Mismatch**: Verify if the task requires *interleaved* (Adds/Amort/End per month) or *grouped* (all Adds, then all Amort) columns. Mismatched layouts break `SUM` ranges and verifier checks.
- **Verifier fails on structure**: Check `ws.max_row` and `ws.max_column`. Ensure no trailing empty rows/columns are counted as data. Run `scripts/verify_rollforward.py` to dump structure.
- **Formula mismatch**: Open generated file in Excel/LibreOffice to verify formulas resolve. Check for missing `$` in absolute references if required.
- **Type errors**: `openpyxl` may coerce strings to numbers if formatted, but explicitly cast to `float` before assignment.
- **Environment**: Install `openpyxl`: `pip install openpyxl --break-system-packages -q`. Use `openpyxl.styles.NumberFormat` for currency.