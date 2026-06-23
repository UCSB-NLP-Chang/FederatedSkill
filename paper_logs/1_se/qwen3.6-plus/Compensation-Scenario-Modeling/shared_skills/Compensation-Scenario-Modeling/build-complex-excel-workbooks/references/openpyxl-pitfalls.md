# openpyxl Pitfalls & API Quirks

## Defined Names API
- `wb.defined_names` behaves like a dictionary.
- Iterating directly (`for dn in wb.defined_names`) yields string keys, not `DefinedName` objects.
- To inspect targets: `target = wb.defined_names[name].attr_text`
- Adding ranges: `wb.defined_names.add(DefinedName(name="MyRange", attr_text="Sheet1!$A$1"))`

## Sheet Management
- `wb.active` points to the first sheet by default. Renaming it and creating others can scramble indices.
- Always use `wb.create_sheet("Name", index)` to enforce exact ordering.
- Sheet names in formulas must match exactly, including spaces and case.

## Row/Column Iteration
- `iter_rows(min_row, max_row, min_col, max_col)` assumes dense data. Sparse rows may raise `IndexError` when accessing `row[col_idx]`.
- Mitigation: Check `len(row) > col_idx` before access, or use `ws.cell(row=r, column=c).value`.

## Formula Injection
- Formulas are stored as strings. openpyxl does not evaluate them.
- Cross-sheet references: `='Sheet Name'!A1`
- Named ranges in formulas: `=MyRange * 2`
- Always verify formula strings after writing to catch typos.
