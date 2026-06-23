---
name: run-pytest-verification
description: Execute pytest test suite and verify task completion. MUST be invoked after generating any output file. Handles test failures with structured diagnosis.
---

# Pytest Verification

## When to Use

Invoke this skill IMMEDIATELY after:
- Generating an Excel report
- Creating output files
- Completing any data transformation task

**This skill is MANDATORY.** Do NOT claim task success without running this skill.

## Workflow

1. **Check for test file** - Look for `test_output.py` in the workspace
2. **Run pytest** - Execute the full test suite:
   ```bash
   pytest test_output.py -v
   ```
3. **If tests pass**: Task is complete. You may proceed.
4. **If tests fail**: STOP. Follow the diagnosis workflow below.

## Test Failure Diagnosis

When pytest fails, use this decision tree:

| Failure type | Diagnostic message | Fix |
|--------------|-------------------|-----|
| Sheet name mismatch | `AssertionError: 'SheetName' not in [...]` | Check exact spelling/casing in `sheet_name=` arguments |
| Column name mismatch | `KeyError: 'COLUMN'` or column count mismatch | Header names must match test expectations exactly (case-sensitive) |
| Numeric precision | `AssertionError: 100.0 != 100.0001` | Remove rounding; pass raw float values |
| Missing sheet | `AssertionError: expected N sheets, found M` | All required sheets must be written |
| Wrong aggregation | Pivot totals don't match expected | Check `aggfunc` matches (sum/mean/count) |
| Row count mismatch | `len(df) != expected` | Re-check join logic, whitespace, dtype casting |

## Fix Loop

After identifying the issue:
1. Fix your script/code
2. Re-run the script to regenerate output
3. Invoke this skill again to re-run pytest
4. Repeat until ALL tests pass

## Common Fixes by Failure Type

### Sheet name mismatch
- Read `test_output.py` to find expected sheet names
- Match exact casing (e.g., "SourceData" not "source_data")

### Column name mismatch
- Strip whitespace from all column headers
- Check for hidden characters or extra spaces

### Numeric precision mismatch
- NEVER use `round()`, `format()`, or f-string formatting
- Pass raw float values directly to Excel cells

## Output Precision Reminder

Never round, truncate, or fixed-format numeric values:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: Pass raw float x directly

## Exit Condition

**Only proceed from this skill when:**
- `pytest test_output.py -v` shows ALL tests passing
- OR no `test_output.py` exists (document this in your response)
