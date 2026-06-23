---
name: build-complex-excel-workbooks
description: Guide for programmatically constructing multi-sheet, formula-heavy Excel workbooks using openpyxl. Use when tasks require generating workbooks with named ranges, cross-sheet formulas, data migration from source files, and strict structural validation.
---

# Build Complex Excel Workbooks with openpyxl

## Workflow
1. **Inspect Sources**: Read all input Excel/CSV files to map columns, data types, and row counts.
2. **Plan Structure**: Define sheet order, named ranges, and formula dependencies before coding.
3. **Write Builder Script**:
   - Create sheets in exact order using `wb.create_sheet(name, index)`.
   - Populate data rows first, then write formulas that reference them.
   - Define named ranges using `wb.defined_names.add()` or `DefinedName`.
   - Save only after all structures are finalized.
4. **Validate**: Run `scripts/validate_workbook.py` to verify sheet order, named range counts, formula presence, and row counts.

## Critical openpyxl Patterns
- **Sheet Creation**: Do not rename `wb.active` to build multiple sheets. Use `wb.create_sheet("Name", index)` to guarantee order.
- **Named Ranges API**: `wb.defined_names` is a dict-like object. Iterate safely with `list(wb.defined_names)`. Access details via `wb.defined_names[name]`. Do not use `.definedName` or assume iteration yields objects.
- **Row Iteration**: `iter_rows` may raise `IndexError` if `max_col` exceeds sparse row lengths. Wrap cell access in bounds checks or use `values_only=True` when possible.
- **Formula Syntax**: Use Excel A1 notation. Cross-sheet references require exact sheet names: `='Sheet Name'!A1`. Named ranges in formulas do not need sheet prefixes if globally scoped.

## Validation Checklist
- [ ] Sheets exist in required order.
- [ ] Named range count meets minimum threshold.
- [ ] Key formulas contain expected references (e.g., `SUM`, cross-sheet links).
- [ ] Data rows match source counts.
- [ ] Hyperlinks and formatting are applied.

## Troubleshooting
- **`KeyError: Worksheet X does not exist`**: Caused by renaming `wb.active` or creating sheets out of order. Always use `create_sheet` with explicit indices.
- **`AttributeError` on `defined_names`**: openpyxl's API changed. Use `list(wb.defined_names)` to get names, then `wb.defined_names[name].attr_text` for targets.
- **Missing Named Ranges**: Ensure names are unique and globally scoped. Add them after sheet creation but before `wb.save()`.

## Fallback
If formula validation or complex formatting becomes unmanageable, generate data with `pandas` and inject formulas via `openpyxl` post-save, or use `xlwings` for Excel-native execution.

## Reusable Assets
- Run `scripts/validate_workbook.py <path_to_workbook.xlsx>` after generation to catch structural defects early.
- See `references/openpyxl-pitfalls.md` for detailed API behavior notes and version-specific quirks.
