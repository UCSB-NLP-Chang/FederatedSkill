# Pytest Failure Patterns

This document describes common pytest failure modes and how to interpret them.

## test_legacy_pytest_suite Failures

The `test_legacy_pytest_suite` is a compound test that runs multiple validation checks. When it fails, the output typically shows multiple sub-failures.

### Interpreting the Output

Example failure output:
```
FAILED test_output.py::test_legacy_pytest_suite - AssertionError: 
  Sheet order mismatch: expected ['Summary', 'Assumptions', ...]
  Aggregation row missing at row 107
  Named range count: 45 != 50
```

### Common Sub-Failures

1. **Sheet order mismatch**
   - **Symptom**: `Sheet order mismatch: expected X, got Y`
   - **Cause**: Sheets created in wrong order, extra sheets present, or case mismatch
   - **Fix**: Check `wb.sheetnames` against expected list; delete forbidden sheets

2. **Aggregation row position error**
   - **Symptom**: `Aggregation row missing at row N` or wrong cell reference
   - **Cause**: Row count off by one (header vs data rows), or wrong sum range
   - **Fix**: For N employees starting at row S, aggregation is at S+N

3. **Named range count mismatch**
   - **Symptom**: `Named range count: X != Y`
   - **Cause**: Created all items in list instead of stated count, or missed some
   - **Fix**: Trust the stated count N in requirements, not list length M

4. **Formula vs value error**
   - **Symptom**: `Cell must contain formula` or `value.startswith('=')` failure
   - **Cause**: Hardcoded value where formula expected, or formula overwritten
   - **Fix**: Ensure `ws['A1'] = "=..."` not `ws['A1'] = value`

5. **Cell reference error**
   - **Symptom**: `Expected '=Sheet!A1', got '=Sheet!B1'`
   - **Cause**: Formula references wrong row/column
   - **Fix**: Check column mapping and row indices in formula generation

6. **Formula named range mismatch**
   - **Symptom**: Formula contains `BaseSal__Current` but defined name is `BaseSal_Current`
   - **Cause**: String concatenation bug in formula construction (e.g., `suffix = "_Current"` + `f'=BaseSal_{suffix}'`)
   - **Fix**: Print sample formula before writing; verify no doubled delimiters

### Debugging Strategy

1. Read the full assertion output - multiple issues may be listed
2. Fix structural issues first (sheet order, row counts)
3. Then fix formula content issues
4. Re-run after each fix - one error can cascade to others

## Specific Assertion Patterns

### `assert cell.value.startswith('=')`
Cell must contain a formula but contains a static value or None.

**Check**:
```python
wb = openpyxl.load_workbook(path, data_only=False)
cell = wb['Sheet']['A1']
print(cell.value)  # Should start with '='
```

### `assert sheet_name in wb.sheetnames`
Sheet missing or wrong name.

**Check**:
```python
print(wb.sheetnames)  # Case-sensitive comparison
```

### `assert abs(cell.value - expected) < tolerance`
Value precision error or wrong calculation.

**Check**:
- Formula references correct cells?
- No rounding applied to output?
- Named ranges point to correct values?

### `assert len(wb.defined_names) == expected`
Named range count mismatch.

**Check**:
```python
print(f"Count: {len(wb.defined_names)}")
for name in wb.defined_names:
    print(f"  {name}")
```

## Debugging Workflow

1. **Run with verbose flag**: `pytest test_output.py -v`
2. **Identify first failure**: Focus on the first assertion that fails
3. **Inspect the workbook**:
   ```python
   import openpyxl
   wb = openpyxl.load_workbook('output.xlsx', data_only=False)
   # Check specific cell mentioned in error
   print(wb['Sheet']['A1'].value)
   ```
4. **Check named ranges**:
   ```python
   for name in wb.defined_names:
       dn = wb.defined_names[name]
       attr = dn.attr_text if hasattr(dn, 'attr_text') else dn
       print(f"{name}: {attr}")
   ```
5. **Verify aggregation rows**:
   ```python
   ws = wb['EE Calcs']
   print(f"Max row: {ws.max_row}")
   print(f"Row 91: {ws['A91'].value}")  # Should be 'TOTAL' or similar
   print(f"Row 91 formula: {ws['B91'].value}")  # Should be =SUM(...)
   ```

## When Tests Pass Partially

Some test suites have multiple independent tests. If some pass and others fail:
- Fix the failing tests one at a time
- Don't rely on "most tests pass" - all must pass
- `test_legacy_pytest_suite` is a single test that checks multiple things; it must pass completely

## The "Silent Failure" Pattern

Sometimes pytest shows:
```
FAILED test_output.py::test_legacy_pytest_suite
```
With no details. This usually means an exception was raised during test execution.

**Fix**: Run with more verbose output and capture traceback:
```bash
pytest test_output.py::test_legacy_pytest_suite -v --tb=long
```

## Preventing Regressions

After fixing a test failure:
1. Run the full test suite again
2. Verify your fix didn't break other tests
3. Check that custom verification still passes (as secondary check)