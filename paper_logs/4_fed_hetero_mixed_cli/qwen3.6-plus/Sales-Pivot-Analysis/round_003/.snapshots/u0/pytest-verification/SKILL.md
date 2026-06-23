---
name: pytest-verification
description: Run pytest test suite and parse results. Invoke this skill AFTER generating output files to verify correctness. The test suite is the ONLY authority on pass/fail - manual inspection is never sufficient.
---

# Pytest Verification

## Purpose
This skill runs the test suite (`pytest test_output.py -v`) and guides you through interpreting results. Use this skill immediately after completing the `sales-pivot-report` workflow.

## Workflow

1. **Run the test suite:**
   ```bash
   pytest test_output.py -v
   ```

2. **Parse the output:**
   - **PASSED** (green): Test passed. Continue to next test or declare success.
   - **FAILED** (red): Test failed. Read the error message carefully.

3. **On failure, diagnose:**
   - `AssertionError: 'SheetName' not in [...]` → Sheet name mismatch
   - `KeyError: 'COLUMN_NAME'` → Missing or misnamed column
   - `AssertionError: 100 != 100.0001` → Precision issue (remove rounding)
   - `AssertionError: expected 3 sheets, found 2` → Missing sheet

4. **Fix and re-run:**
   - Modify your script to address the failure
   - Re-run `pytest test_output.py -v`
   - Repeat until all tests pass

5. **Only after all tests pass:**
   - You may write DONE.txt

## Critical Rules

- **Never declare success until pytest passes.** Manual file checks, row counts, and openpyxl inspection are NOT verification.
- **Do not skip this skill.** The test suite is the authoritative verifier.
- **Do not round numeric values.** The verifier has tolerance (often 1e-4); pass raw floats.

## Troubleshooting Quick Reference

| Failure Pattern | Likely Cause | Fix |
|---|---|---|
| Sheet name mismatch | Spelling/casing difference | Match exact test expectation |
| Column name mismatch | Extra spaces, wrong case | Verify header names exactly |
| Numeric precision | Used `round()` or format string | Remove all rounding |
| Missing sheet | Forgot to write in ExcelWriter | Add all required sheets |
| Row count mismatch | Join issue, whitespace in keys | Strip keys, check dtypes |

## Known Invariants (Test Suite)

The test file `test_output.py` encodes domain-specific expectations:

### pdf-catalog-transaction-merge
- Join key: `PRODUCT_ID`
- Sheets: `SourceData`, `PivotSummary`

### library-circulation-pivot
- Join key: `BOOK_ID`
- Sheets: `Loans by Genre`, `Avg Duration by Genre`, `Loans by Borrower Type`, `Genre Borrower Matrix`, `SourceData`
- Derived: `LOAN_DURATION`, `DECADE`, `RETURN_STATUS`, `WEEKDAY_BUCKET`

### student-performance-pivot
- Join key: `STUDENT_ID`
- Sheets: `Avg Score by Department`, `Students by Department`, `Credits by Semester`, `Department Semester Matrix`, `SourceData`
- Derived: `GRADE_BAND`, `WEIGHTED_SCORE`, `TERM_STATUS`, `RETAKE_FLAG`

Check `test_output.py` for the exact expectations for your task.
