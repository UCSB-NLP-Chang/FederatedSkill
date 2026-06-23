# Finding Test Files When They're Not in Standard Locations

## Common Test File Locations

Test files for Excel formula tasks are often named:
- `test_output.py` (most common for single-file tasks)
- `test_*.py` (e.g., `test_formulas.py`)
- `*_test.py` (e.g., `excel_test.py`)

They can live in:
- `/root/tests/` (standard pytest directory)
- `/root/` (task root directory)
- `/root/output/` (alongside output files)
- Parent directory `../` (occasionally)

## Search Commands

If pre-flight check reports "No test files found":

```bash
# Search by name pattern
find /root -name "test*.py" 2>/dev/null
find /root -name "*_test.py" 2>/dev/null

# Search by content (files that import openpyxl or pytest)
grep -r "import openpyxl" /root/*.py 2>/dev/null
grep -r "def test_" /root/*.py 2>/dev/null

# Check specific locations
ls -la /root/test_output.py 2>/dev/null
ls -la /root/tests/test_*.py 2>/dev/null
```

## What To Do If Tests Are Missing

**Cannot find tests after searching:**
1. Assume the worst case: verifier uses `data_only=True`
2. Use external calculation (LibreOffice/xlwings) or manual calculation
3. Document that tests could not be located

**Found tests in unexpected location:**
1. Run pre-flight check on the correct path:
   ```bash
   python3 scripts/check_test_data_only.py /root/test_output.py
   ```
2. Run tests explicitly:
   ```bash
   pytest /root/test_output.py -v
   ```
3. Update your approach based on exit code

## Test Structure Clues

If you can read the test file, look for:

```python
# If you see this, verifier checks formula strings ( safer ):
assert ws['A1'].value == "=SUM(B1:B10)"

# If you see this, verifier checks calculated values ( needs external engine ):
wb = openpyxl.load_workbook('output.xlsx', data_only=True)
assert ws['A1'].value == 42.0  # Will be None if not calculated
```