# Debugging Test Failures

## The Golden Rule

**Read the test source code.** Tests check specific expectations that may not match your intuitive understanding of "correct."

Common test checks that cause failures:
- Exact row numbers (totals must be at row 79, not 80)
- Exact formula strings (whitespace, parentheses style matter)
- Named range names (case-sensitive, exact match)
- Sheet names (including spaces and punctuation)
- Cell number formats (0.03 vs 3% vs 0.0300)

## Decoding pytest Output

### Find the failing assertion
```bash
python3 -m pytest test_output.py -v --tb=short
```

Look for:
```
FAILED test_output.py::test_workbook - AssertionError: expected row 79, got row 80
```

### Get full context
```bash
python3 -m pytest test_output.py -v --tb=long
```

### Read the test
```bash
cat test_output.py | grep -A 20 "def test_"
```

## Common Failure Patterns

### Row Position Mismatch
**Test expects:** Totals at row 79  
**You generated:** Totals at row 80

**Fix:** Recalculate layout math
```python
header_rows = 4  # Including title, blank, headers
data_count = 75  # Actual faculty count
total_row = header_rows + data_count + 1  # 80, not 79

# Check: did test expect different header count?
```

### Formula String Mismatch
**Test checks:** `cell.value == "=SUM(A1:A10)"`  
**You generated:** `=SUM(A1:A10)` (equivalent but different whitespace)

**Fix:** Match test's exact string expectation, or use `data_only=True` and check calculated values.

### Named Range Missing
**Test expects:** `Sr15to19_Yr1`  
**You defined:** `Sr15to19_Yr2` only

**Cause:** Hardcoded row range missed some parameters.

**Fix:** Use `scripts/detect_boundaries.py` to ensure all parameters extracted.

### Cross-Sheet Reference Broken
**Symptom:** `#REF!` in Excel, test fails

**Causes:**
- Sheet renamed after formula created
- Sheet order changed (some Excel versions sensitive)
- Named range defined after formula referencing it

**Fix:** Define named ranges before formulas; verify sheet names match exactly.

## When Tests Pass Locally But Fail Remotely

1. **openpyxl version differences** - Pin version: `pip install openpyxl==3.1.2`
2. **File encoding** - Use `utf-8` explicitly
3. **Path separators** - Use `pathlib.Path` not string concatenation
4. **Timezone/date handling** - Be explicit about naive vs aware datetimes

## Escalation Path

If you cannot determine why tests fail:

1. Generate minimal workbook with just the failing component
2. Compare byte-by-byte with expected (if reference provided)
3. Check if test uses `data_only=True` (requires Excel calculation)
4. Ask for test source clarification if ambiguous

## Prevention

- Run tests early and often during development
- Don't batch all generation then test - test incrementally
- When test exists, read it before writing generation code
