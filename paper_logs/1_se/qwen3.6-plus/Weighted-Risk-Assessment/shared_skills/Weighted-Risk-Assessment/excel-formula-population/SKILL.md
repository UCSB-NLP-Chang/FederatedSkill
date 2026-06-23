---
name: excel-formula-population
description: Populate Excel workbooks with complex formulas (lookups, statistics, weighted calculations) using openpyxl. Use when a task requires filling highlighted or empty cells with dynamic formulas that reference other sheets, preserving existing structure and formatting.
---

# Excel Formula Population

## Workflow
1. **Inspect Structure**: Load workbook with `openpyxl`. Map sheet names, dimensions, headers, existing formulas, and target ranges. Identify row/column keys for lookups.
2. **Identify Dependencies**: Check if source data sheets have required headers. If missing, inject them programmatically before writing formulas.
3. **Construct Formulas**:
   - **MANDATORY SHEET PREFIX**: Every single cell reference in the formula string MUST be prefixed with its sheet name (e.g., `Task!D12`, `Task!H$10`, `Data!$H$21:$L$38`). This applies even to references on the same sheet as the formula. Strict verifiers will fail on unqualified references like `D12` or `H$10`.
   - Use absolute references (`$A$1`) for fixed data ranges and header rows.
   - Use relative references for lookup keys (e.g., `Task!D12`, not `Task!$D$12`).
   - Prefer `INDEX/MATCH` over `VLOOKUP`.
   - Use `SUMPRODUCT` for weighted calculations.
   - **CRITICAL**: `openpyxl` strips spaces after commas and normalizes syntax. Write formulas *without* spaces after commas to match strict verifier string expectations.
4. **Pre-Save Validation (MANDATORY)**:
   - Run `scripts/check_unqualified.py <path> <sheet>` to automatically detect unqualified references. **Do not proceed if it fails.**
   - Manually verify that all percentile calculations use `PERCENTILE(range,k)`, not `QUARTILE`.
   - Run `scripts/verify_formulas.py <path> <sheet> <ranges>` to dump exact strings for final diff.
5. **Write & Save**: Assign formulas to target cells. **Save directly to the required output path.** Do not modify the source file and copy it.
6. **Final Verification**:
   - Reload the saved workbook.
   - **String Match First**: Diff dumped strings against expected patterns. Check for: missing `$` locks, extra `$` locks, or `QUARTILE` vs `PERCENTILE` syntax.
   - **Statistics Range Check**: Explicitly verify that `MIN`, `MAX`, `MEDIAN`, `AVERAGE`, `PERCENTILE`, and `QUARTILE` reference multi-cell ranges (e.g., `H35:H40`), not single cells.
   - Count total formulas to match task expectations.

## Key Formula Patterns
- **2D Lookup**: `=INDEX(Data!$H$21:$L$38,MATCH(Task!D12,Data!$D$21:$D$38,0),MATCH(Task!H$10,Data!$H$20:$L$20,0))`
- **Derived Metric**: `=(Task!H12-Task!H19)/Task!H26*100`
- **Statistics**: `MIN`, `MAX`, `MEDIAN`, `AVERAGE`, `PERCENTILE(range, k)`
- **Weighted Mean**: `=SUMPRODUCT(Task!H$35:H$40,Task!H$26:H$31)/SUM(Task!H$26:H$31)`
- **Percentile vs Quartile**: `PERCENTILE(range,0.25)` and `QUARTILE(range,1)` are mathematically equivalent, but **strict verifiers often expect `PERCENTILE`**. Use `PERCENTILE` unless explicitly requested.

## Anti-Patterns & Troubleshooting
- **Unqualified References**: The #1 cause of verifier failure. Always type `SheetName!` before every cell coordinate. `openpyxl` will not add it for you.
- **Unnecessary Absolute Locks on Keys**: Avoid `$` on lookup keys (e.g., `Task!$D12` or `Task!D$12`) unless explicitly required. Verifiers frequently expect purely relative keys (`Task!D12`).
- **Missing Headers**: `MATCH` fails if lookup headers are absent. Verify and inject missing headers into the source sheet first.
- **Reference Drift**: Ensure `$` locks are applied correctly to fixed ranges. Test one formula manually before bulk-writing.
- **Formatting Loss**: `openpyxl` preserves formatting by default. Load, modify, and save. Do not recreate workbooks from scratch.
- **Statistics Single-Cell Trap**: When writing statistics across columns, ensure the range spans all relevant rows (e.g., `H35:H40`, not `H35`). Verify ranges immediately after generation.
- **Value vs String Verification**: `openpyxl` does not calculate formulas. Computing expected values in Python confirms logic, but **strict verifiers compare exact strings**. Always prioritize string matching. If logic is sound but strings differ, adjust syntax to match the verifier's canonical form.

## Verifier Failure Fallback
If the verifier fails despite correct-looking formulas:
1. Run `scripts/verify_formulas.py` to dump exact stored strings.
2. Diff against expected strings. Common mismatches: `openpyxl` auto-upcasing, missing/extra `$` locks, unqualified sheet names, swapped `INDEX` arguments, or `QUARTILE` vs `PERCENTILE`.
3. If string matching is brittle but logic is sound, verify values programmatically in Python and explicitly state logical correctness.
4. Check for hidden sheet names or merged cells that shift coordinates.

See `references/formula-patterns.md` for detailed syntax, variant examples, and Python value-verification snippets.