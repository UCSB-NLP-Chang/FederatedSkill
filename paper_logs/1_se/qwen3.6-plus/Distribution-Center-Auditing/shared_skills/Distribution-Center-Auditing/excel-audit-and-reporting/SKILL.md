---
name: excel-audit-and-reporting
description: Process Excel workbooks to compute derived columns, aggregate data, and generate formatted multi-sheet Excel audits and Word executive briefs. Use when tasked with data validation, exception auditing, cross-file joins, alias normalization, or generating structured reports from tabular data.
---

# Excel Audit & Reporting Workflow

## Overview
Transform raw Excel data into audited workbooks (with computed columns and summary sheets) and executive Word briefs. Follow this workflow to avoid common `openpyxl`, `pandas`, and `python-docx` pitfalls and pass strict verifiers.

## Environment Setup
- **Library Availability**: Base environments often lack `pandas` or `python-docx`. Check imports first. If missing, install via `pip install --break-system-packages pandas openpyxl python-docx` (common in Docker/root) or use a venv.
- **Tool Choice**: Use `pandas` for fast data manipulation/joins, but switch to `openpyxl` for final output writing to preserve formatting and control exact cell types.

## Step-by-Step Workflow
1. **Inspect Source Data & Templates**
   - **Do not use generic file readers** for `.xlsx` files; they will fail on binary format. Use `openpyxl` or `pandas`.
   - Load workbooks with `openpyxl.load_workbook(path, data_only=True)` or `pd.read_excel()`.
   - Print sheet names, row count, column headers, and first 3 rows.
   - **Crucial:** Check Python types of each column. `openpyxl` preserves native types (`int`, `float`, `str`, `datetime`, `None`). `pandas` converts to `float64`/`object` and uses `NaN` for missing.
   - **Template Handling:** If an audit template is provided, load it first. Preserve pre-formatted sheets (e.g., `Overview`) exactly by copying them to the output workbook or writing directly into the template file. Do not recreate complex formatting manually.
   - **Rule Sheets & Auxiliary Files:** If the task provides multiple files (e.g., `AliasMap`, `Thresholds`, `EventLog`), load them into Python dictionaries keyed by the relevant dimension *before* processing main data. Normalize keys (`.strip().lower()`) to avoid join mismatches.

2. **Handle Data Types & Missing Values**
   - Never assume numeric or date columns are clean. Import and use `scripts/safe_excel_utils.py` (`safe_int`, `safe_float`) when sanitizing numeric columns before arithmetic.
   - **NaN/None Sanitization (Critical for Verifiers):** When using `pandas` to read and `openpyxl` to write, `NaN` values will serialize as `float('nan')` or strings like `"nan"`/`"None"`. **Always sanitize before writing:** `val = None if pd.isna(val) else val`. Verifiers strictly check for empty cells or `None`, not string literals.
   - **Date Handling:** Excel dates are often `datetime` objects. When comparing or writing back, explicitly format to `YYYY-MM-DD` strings if the verifier expects strings, or keep as `datetime` if it expects dates.
   - **Null Handling:** Empty cells in Excel are `None`, not `""`. Explicitly check `if val is None:` before string operations.

3. **Compute Derived Columns & Cross-File Joins**
   - Append new columns to the right of existing data.
   - **Indexing Rule:** `openpyxl` uses 1-based indexing for cells, but `ws.iter_rows(values_only=True)` yields 0-based tuples. Track indices carefully.
   - **Composite Key Joins:** When joining across files, build lookup dictionaries using composite keys (e.g., `f"{shipment_id}||{carton_id}"`) to prevent collisions. Always strip and lowercase keys before lookup.
   - **Rule-Driven Flagging:** Apply loaded thresholds row-by-row. Explicitly compute comparisons and string status checks. Combine boolean flags into a human-readable summary column.
   - Validate computed columns by printing a sample row before writing.

4. **Safe Aggregation & Summary Generation**
   - **Type Casting Before Math:** When aggregating counts or sums, explicitly cast values to `int` or `float` first. Excel cells or dict lookups may return strings, causing `TypeError`.
   - Group by key dimensions using `collections.defaultdict(list)` or `pandas.groupby()`.
   - Compute totals per group, then append a "Grand Total" row if required.
   - Sort summary rows explicitly if the task specifies an order.

5. **Generate Output Workbook**
   - Create sheets: `RawData` (exact copy), `Formatted Data` (original + computed), `Summary` (aggregated by key dimensions).
   - **Default Sheet Warning:** `openpyxl.Workbook()` automatically creates a default sheet named `"Sheet"`. Delete it immediately (`del wb["Sheet"]`) if it is not part of the required output.
   - Apply formatting (headers bold, borders, number formats) *after* writing data.
   - Save to a new path.

6. **Generate Word Executive Brief**
   - Use `python-docx`. Add headings, paragraphs, and bullet points.
   - Pull aggregated totals and high-priority flags from the computed data.
   - Keep recommendations actionable and tied to specific data findings.

7. **Verification (Mandatory)**
   - **Reload both output files** immediately after saving. Do not rely on in-memory state.
   - **Checklist:**
     1. Exact sheet names & sheet count match spec.
     2. Headers exactly match expected spec (case-sensitive, no extra spaces).
     3. Row counts match source data.
     4. Cross-check aggregated totals in `Summary` against sums of computed flags in `Formatted Data`.
     5. Verify template sheets (if any) are untouched.
     6. **Sanity Check Cell Values:** Ensure no `"None"`, `"nan"`, or `"-"` strings exist unless explicitly requested. Use `None` or `""` for empty/missing data.
   - Spot-check 2-3 computed values against manual calculation.
   - Print Word doc paragraphs to confirm structure and totals.

## Anti-Patterns & Troubleshooting
- **`TypeError: '>' not supported between instances of 'str' and 'int'`**: Caused by mixing types during threshold comparisons. Always sanitize inputs to numeric before math.
- **`TypeError: unsupported operand type(s) for +=: 'int' and 'str'`**: Occurs during aggregation when a value pulled from Excel or a dictionary is a string. Always wrap accumulators with `int()` or `safe_int()`.
- **`ValueError: invalid literal for int() with base 10: 'None'`**: Empty cells in Excel are `None`. Handle explicitly.
- **Off-by-one column errors**: When appending columns, remember `values_only=True` yields tuples starting at index 0. Map carefully to 1-based `openpyxl` columns.
- **Date Format Mismatch**: Verifiers often fail if dates are written as `datetime` objects when strings are expected, or vice versa. Explicitly format dates during write.
- **Default Sheet Leftover**: `openpyxl` auto-creates a `"Sheet"` on `Workbook()`. Failing to delete it causes sheet-count mismatches in strict verifiers.
- **Do not rely on `data_only=False` for computed Excel formulas**: Use `data_only=True` to read cached values, or compute everything in Python.
- **Avoid single massive scripts**: Break into: (1) read & sanitize, (2) compute & aggregate, (3) write Excel, (4) write Word, (5) verify. Isolate failures quickly.
- **Stringified Missing Values**: Writing `"None"` or `"nan"` instead of `None`/`""` is a top cause of verifier failures. Always sanitize `pandas` outputs before `openpyxl` writes.

## Fallback
If `openpyxl` struggles with complex formatting or large files, switch to `pandas` for computation and `openpyxl`/`xlsxwriter` for export. For Word, `python-docx` is standard; if template-heavy, use `docxtpl`.