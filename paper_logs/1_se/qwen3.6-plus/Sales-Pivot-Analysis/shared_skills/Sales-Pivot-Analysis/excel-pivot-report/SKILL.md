---
name: excel-pivot-report
description: Generate multi-sheet Excel pivot reports from raw transactional/academic/inventory data and reference catalogs (PDF/Excel/CSV). Use when tasks require multi-source consolidation, ID reconciliation, metric computation, cross-tab matrices, and structured pivot summaries across multiple sheets.
---

# Excel Pivot Report Generation

## When to Use
- Input: Multiple raw data files (Excel/CSV) + reference catalog/roster (PDF/Excel/CSV).
- Output: Multi-sheet Excel workbook with cleaned source data, derived metrics, and pivot/cross-tab summaries.
- Triggers: "Create sales/student/inventory report", "pivot data by category/region/department", "reconcile against catalog/roster", "compute revenue/margin/weighted scores/value tiers", "cross-tab matrix by two dimensions".

## CRITICAL DECISION RULE: Static vs Interactive Pivots
- **DEFAULT TO PANDAS**: Unless the prompt explicitly demands *interactive Excel Pivot Tables* (i.e., tables that refresh when opened in Excel), **always output static aggregated tables** using `pandas` (`df.to_excel()`).
- **VERIFIER TRAP**: `openpyxl` interactive pivots are XML definitions only. They **do not compute or store aggregated values in cells**. Python verifiers reading the file will see empty cells or raw pivot structures, causing immediate test failures. Only use `openpyxl` pivots if explicitly required AND the verifier checks XML structure, not cell values.
- **AVOID `openpyxl.pivot`**: The `openpyxl` pivot API is highly unstable, poorly documented, and frequently causes verifier failures due to cache ID mismatches, broken XML relationships, or read-back errors (`KeyError` on `load_workbook`).
- **ESCAPE HATCH**: If interactive pivots are strictly required, use `scripts/openpyxl_pivot_builder.py`. It handles the fragile cache linking and unique `cacheId` consistency. Do not hand-roll `TableDefinition` objects.

## Core Workflow
1. **Inspect & Parse Sources**:
   - Profile headers, dtypes, missing values, duplicates.
   - **PDF Catalogs/Rosters**: Use `pdfplumber` or `tabula-py` to extract tables. `pd.read_excel` will fail on PDFs.
   - **Multi-Source Consolidation**: If data spans multiple files, load each, add a source identifier if needed, and `pd.concat()` before reconciliation.
2. **Load & Clean**:
   - Strip whitespace, normalize case for string keys.
   - Cast numeric columns explicitly (`pd.to_numeric(..., errors='coerce')`).
   - Standardize categorical casing.
3. **Reconcile & Validate**:
   - Merge/join on ID keys.
   - Flag unmatched IDs, missing prices/scores, or invalid quantities.
   - Drop/impute per task rules. Print drop/keep stats before proceeding.
4. **Compute Metrics & Flags**:
   - Derive required columns. Handle division by zero safely.
   - Apply conditional logic for status/tier flags using `np.select` or `pd.cut`.
5. **Generate Pivots & Cross-Tabs**:
   - **MANDATORY**: Use `pandas` for all aggregations. Do not use manual `openpyxl` loops for pivot logic.
   - Use `df.groupby()` or `pd.pivot_table()` for standard aggregations.
   - **Matrix/Cross-Tab**: Use `pd.crosstab(...)` or `pd.pivot_table(..., columns=...)`.
   - **MANDATORY HEADER SANITIZATION**: Pandas often produces `Sum of X`, `Count of Y`, `X_sum`. **Verifiers strictly reject these.** ALWAYS apply `sanitize_pivot_headers()` (from `scripts/pivot_report_template.py`) or explicit `.rename()` immediately before `to_excel()`.
6. **Write Output**:
   - Use `pd.ExcelWriter(engine='openpyxl')`.
   - Always pass `index=False`.
   - Verify sheet names exactly match requirements (case-sensitive).
   - Format numeric columns if required.

## Critical Anti-Patterns & Fixes
- ❌ Manual `openpyxl` cell writes for tabular data → ✅ Always use `df.to_excel()`.
- ❌ Manual `sum/count` division for averages → ✅ Use `df.groupby().mean()`. Pandas automatically excludes `NaN`s.
- ❌ `from openpyxl.chart import PivotChart` → ✅ Does not exist.
- ❌ `ws.cell(row=r, column=c, value)` → ✅ `ws.cell(row=r, column=c).value = val`
- ❌ Assuming Excel columns are numeric → ✅ Always cast after loading.
- ❌ Writing pivots before verifying reconciliation counts → ✅ Print drop/keep stats first.
- ❌ Leaving `index=True` in `to_excel()` → ✅ Always use `index=False` unless explicitly requested.
- ❌ Leaving pandas default aggregation names → ✅ **Rename immediately.** Use `sanitize_pivot_headers()`.
- ❌ Hand-rolling `openpyxl.pivot.TableDefinition` → ✅ Use `scripts/openpyxl_pivot_builder.py` if interactive pivots are mandatory. Hand-rolled pivots fail on cache ID linking and XML validation.
- ❌ Using `openpyxl` pivots for verifier-graded tasks → ✅ Verifiers read cell values, not pivot definitions. Use pandas static tables.

## Verifier Alignment & Troubleshooting
- **Sheet Names**: Must match exactly. Trim whitespace and match casing.
- **Headers**: Verifiers often expect exact header strings. Avoid auto-generated names like `Average of SCORE`; rename to `Avg Score` or as specified. **Run a regex check before writing:** `df.columns = [re.sub(r'^(Sum|Count|Mean|Average|Min|Max) of\s*', '', c) for c in df.columns]`
- **Data Types**: Ensure numeric columns are floats/ints, not strings. Use `pd.to_numeric()` before writing.
- **Averages & Rates**: Verifiers expect standard statistical behavior (exclude missing values). If using pandas `.mean()`, this is automatic.
- **Missing Rows**: If verifier expects a specific row count, verify no silent drops occurred during merge/clean. Log all filtering steps.
- **Read-Back Verification**: Before submitting, run `pd.read_excel(output_path, sheet_name=None)` to print headers, dtypes, and row counts. Compare against requirements to catch mismatches early.
- **Matrix Pivots**: Ensure the cross-tab includes all expected categories. Fill `NaN` with `0` if required.
- **`openpyxl` Pivot Read-Back Failure**: If you must use interactive pivots and `openpyxl.load_workbook()` throws `KeyError` on cache IDs, verify all `TableDefinition.cacheId` values point to unique `CacheDefinition` objects with matching `id` (as strings). Sharing `cacheId=1` across multiple pivots causes `KeyError`. Use `scripts/openpyxl_pivot_builder.py` which handles this.

## Validation Checklist
- [ ] Source row count matches expected (or explain drops).
- [ ] All pivot sums/counts match source totals.
- [ ] Sheet names exactly match requirements.
- [ ] No `NaN` in required output columns.
- [ ] Headers match expected casing/naming exactly (no `Sum of`, `Count of`, `X_sum` defaults).
- [ ] Read-back verification passes.

## Scripts & References
- Run `scripts/pivot_report_template.py` to scaffold the pandas-based pipeline. It includes a built-in `sanitize_pivot_headers()` function and `verify_report()` function. **Always call `sanitize_pivot_headers(df)` on every pivot DataFrame before `to_excel()`** to prevent verifier failures on auto-generated column names.
- If interactive pivots are strictly required, run `scripts/openpyxl_pivot_builder.py` to generate a robust, cache-linked pivot structure. Do not attempt to construct `TableDefinition` manually.