---
name: excel-workbook-generation
description: Build or update multi-sheet Excel workbooks from CSV/JSON data using openpyxl, with cross-sheet formulas, control rows, and automated verification. Use when generating financial reports, schedules, or structured spreadsheets that require precise sheet ordering, formula validation, data type checks, or patching existing templates.
---

# Excel Workbook Generation & Template Updates with openpyxl

## Critical First Step: Read & Run the Verifier
**Before writing any generation code, read `test_output.py` or the provided test suite.** Extract:
- Exact sheet names and order
- Formula strings (including `=` prefix, spacing, and quote style)
- Number formats (`'#,##0.00'` vs `'0.00'`)
- Header labels and cell positions
- Output file path
- Expected control row labels and positions

**Do not guess structure from source data alone.** Tests often expect specific formatting or formula variants that differ from intuitive implementations.
**Run the test suite immediately after the first successful save.** Do not rely on ad-hoc inline checks. If tests fail, dump exact cell values/formats and diff against test assertions.

## Workflow
1. **Read Verifier & Plan**: Extract exact expectations. Decide if generating from scratch or updating a template.
2. **Load & Merge Data**: Read source CSV/JSON. Filter inactive/superseded records (`status=open` or `active_flag=true`). Apply CSV overrides to JSON items. Join with metadata (e.g., GL balances). Sort in memory before writing. Never modify source files.
3. **Initialize Workbook**:
   - **Fresh**: `wb = openpyxl.Workbook()`. **Immediately delete the default sheet**: `del wb[wb.sheetnames[0]]`.
   - **Template Update**: `wb = openpyxl.load_workbook(template_path)`. Clear stale data rows (usually below headers) while preserving headers/formatting. Use `ws.delete_rows()` or overwrite with `None`.
4. **Create/Populate Sheets**: Use `wb.create_sheet("ExactName")` in exact test order (fresh). Write data using 1-based integer indices: `ws.cell(row=r, column=c, value=v)`. Apply `cell.number_format = '#,##0.00'` for currency.
5. **Insert Formulas**: Prefix with `=`. For cross-sheet refs, use `'SheetName'!CellRef`. Match test expectations exactly. Place control rows (Totals, Ending Balance, Variance, GL Balance) immediately after data rows.
6. **Save & Verify**: `wb.save(path)`. **Run the official test suite immediately.** Fix structural/type errors before submission.

## Bridge CSV & Action-Based Overrides
When a reconciliation or "bridge" CSV contains an `action` column (`override`, `insert`, `delete`):
- **`override`**: Match on `contract_key` or `row_id`. Apply only non-empty columns. Inspect headers first to avoid mapping `dec_adds` to `term_months`.
- **`insert`**: Create a new record dict. Fill missing fields with defaults (e.g., `0` for amounts, `""` for notes). Append to the active list before sorting.
- **`delete`**: Remove matching records from the active list.
- **Decision rule**: Always run `scripts/inspect_csv_mapping.py <path>` before writing override logic. CSV columns often use abbreviated or shifted names.

## CSV Override Mapping Verification
**Before applying CSV overrides, verify column-to-field alignment:**
```python
import csv
with open('adjustments.csv') as f:
    reader = csv.DictReader(f)
    print("Headers:", reader.fieldnames)
    for row in reader:
        print("Row values:", dict(row))
        break  # Inspect first row only
```
- CSV columns may not match your expected field names (e.g., `nov_adds` vs `term_months`).
- Empty strings in CSV become `''`, not `None`. Use `.strip()` and check truthiness.
- Numeric CSV values arrive as strings. Convert explicitly: `int(val)` or `float(val)`.
- **Decision rule**: If a CSV override appears to target the wrong field, dump the full row dict and compare column positions against the header list before assuming the mapping.

## Multi-Source Data Merging & Patching Pattern
When combining JSON items, CSV overrides, and reference data:
```python
# 1. Load base items from JSON, filter active=True
# 2. Deduplicate by row_id keeping highest revision (or active=True)
# 3. Load CSV overrides into dict keyed by row_id
# 4. Apply overrides: if row_id in overrides, update adds/release/ending/notes
# 5. Load reference data (e.g., GL balances) into dict
# 6. Sort items by partner_name before writing
```

## Floating-Point Precision in Financial Data
**GL balances and amortization calculations often produce floating-point drift (e.g., 5.8e-11 differences).**
- Tests may use exact equality (`==`) or `math.isclose()` with specific tolerances.
- **Decision rule**: If a test fails on a numeric comparison with a tiny difference (<1e-9), check whether the test expects `round(value, 2)` or `math.isclose(actual, expected, rel_tol=1e-9)`.
- When writing GL balance values from JSON, preserve full precision. Do not round unless the test explicitly requires it.
- If your inline check passes but the test fails, the test likely uses a different comparison method. Run the test directly and inspect the assertion.

## Critical Anti-Patterns
- **Skipping Verifier**: Writing code before reading `test_output.py` guarantees formula/format mismatches.
- **`ws.cell()` Column Type**: `column` must be an integer. Passing `'A'` raises `TypeError`. Use integers or `openpyxl.utils.column_index_from_string('A')`.
- **Default Sheet**: Always `del wb["Sheet"]` before creating custom sheets, or sheet-order assertions will fail.
- **Variable Shadowing**: Do not name loop variables `row` or `column`. Use `r_idx`, `c_idx`.
- **Inline Verifiers**: Ad-hoc inline checks often pass while hidden tests fail due to exact string/format mismatches. **Always run the official test suite first**, then use inline checks only for debugging specific failures.
- **Formula Storage**: `openpyxl` stores formulas as strings starting with `=`. Tests check `cell.value == "=FORMULA"`. Ensure no extra spaces.
- **Inline Bash Heredocs**: Writing large generation scripts via `cat << 'EOF' > /tmp/script.py` in a single bash call makes debugging difficult. Write the script to a `.py` file first, run it, inspect errors, then fix.
- **Template Stale Data**: When updating a template, failing to clear old data rows below the new dataset causes duplicate rows or broken control row references. Always clear rows from `header_row + 1` down to the old max row before writing new data.
- **CSV Column Assumptions**: Never assume CSV column names map directly to your target fields. Always inspect `DictReader.fieldnames` and print a sample row before applying overrides.
- **Python Interpreter**: Use `python3`, not `python`. Many environments lack a `python` symlink.
- **Dismissing Precision Errors**: A 5.8e-11 difference in GL balance is NOT a "test assertion issue" — it's the actual failure. Fix the comparison or rounding logic before assuming the test is wrong.

## Troubleshooting
- **`test_legacy_pytest_suite` or `test_legacy_node_checks` fails**: Usually caused by exact formula string mismatch, missing `=` prefix in test assertions, number format string mismatch (`'#,##0.00'` vs `'0.00'`), or floating-point precision drift. Dump exact cell values/formats and diff against test expectations. **Run the test directly with `pytest -v` to see the exact assertion failure.**
- **Cross-sheet ref errors**: Verify target sheet name matches exactly. Use single quotes if names contain spaces.
- **Sheet order mismatch**: Check for leftover default sheet or incorrect creation order.
- **Override application errors**: Verify CSV keys match JSON row_ids exactly. Check for trailing whitespace or case mismatches. **Dump the full CSV row dict to verify column alignment.**
- **Control row formula breaks**: Ensure control rows reference the correct dynamic range (e.g., `=SUM(B6:B8)` not `=SUM(B6:B100)`).
- **Self-validation passes but tests fail**: Your inline checks likely miss exact string/format expectations. Run the official test suite and inspect the first failure's assertion.
- **Floating-point mismatch in GL balance**: Check if the test expects `round(value, 2)` or uses `math.isclose()`. Preserve full precision from JSON unless the test explicitly requires rounding.

## Helper Scripts
- `scripts/verify_workbook.py <path> <expected_sheets_json>`: Validates sheet order, formula presence, and numeric types. **Run after every save, before submitting.**
- `scripts/inspect_csv_mapping.py <path>`: Dumps CSV headers and first row as a dict for override verification. **Run before writing override logic.**