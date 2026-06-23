---
name: run-pytest-verification
description: Execute pytest test suite and create marker file for task completion. MUST be invoked after generating any output file. Creates `.pytest_passed` marker as proof of verification.
---

# Pytest Verification

## Purpose

This skill runs the test suite and creates a marker file. The marker file is the ONLY proof of successful verification - manual inspection is never sufficient.

## Workflow

1. **Locate test file**:
   - Check workspace root: `ls test_output.py`
   - Check subdirectories: `find . -name "test_*.py" -o -name "*_test.py"`
   - If not found, try pytest discovery: `pytest --collect-only`

2. **Run pytest**:
   ```bash
   pytest test_output.py -v
   ```

3. **If tests pass**:
   - Create marker file: `touch .pytest_passed`
   - You may now write DONE.txt

4. **If tests fail**:
   - Read the failure message
   - Identify the issue from the diagnosis table below
   - Fix the script
   - Re-run pytest
   - Repeat until ALL tests pass

5. **Only after creating `.pytest_passed`**:
   - You may proceed to write DONE.txt

## Test Failure Diagnosis

| Failure type | Diagnostic message | Fix |
|--------------|-------------------|-----|
| Sheet name mismatch | `AssertionError: 'SheetName' not in [...]` | Check exact spelling/casing in `sheet_name=` arguments |
| Column name mismatch | `KeyError: 'COLUMN'` or column count mismatch | Header names must match test expectations exactly (case-sensitive) |
| Numeric precision | `AssertionError: 100.0 != 100.0001` | Remove rounding; pass raw float values |
| Missing sheet | `AssertionError: expected N sheets, found M` | All required sheets must be written |
| Wrong aggregation | Pivot totals don't match expected | Check `aggfunc` matches (sum/mean/count) |
| Row count mismatch | `len(df) != expected` | Re-check join logic, whitespace, dtype casting |

## Critical Rules

- **The marker file is mandatory.** You may NOT write DONE.txt unless `.pytest_passed` exists.
- **Manual checks are NOT verification.** Checking file existence, row counts, or dataframes manually does not count.
- **No rounding.** Pass raw float values to Excel cells - the verifier has tolerance (often 1e-4).

## Exit Condition

**Only proceed when `.pytest_passed` exists in the workspace.**

If no test file exists anywhere after exhaustive search, document this in your response before proceeding.