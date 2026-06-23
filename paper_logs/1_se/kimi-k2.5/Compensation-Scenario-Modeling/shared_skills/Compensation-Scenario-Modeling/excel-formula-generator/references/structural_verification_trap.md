# Case Study: The Structural Verification Trap

## The Failure

**Task**: Generate `Property_Management.xlsx` with 8 sheets, 45 named ranges, and specific formulas.

**What the agent did:**
1. ✓ Read source Excel files with openpyxl
2. ✓ Generated workbook with all required sheets
3. ✓ Created 45 named ranges
4. ✓ Added formulas to all expected locations
5. ✗ **Wrote `verify_workbook.py` instead of running `test_output.py`**
6. ✗ **Declared success based on structural checks**
7. ✗ **Failed verifier**: `test_output.py::test_legacy_pytest_suite`

## The Trap

The agent's verification checked:
```python
# verify_workbook.py (ANTI-PATTERN - DO NOT COPY)
print(f"Sheet order matches: {actual == expected}")  # ✓
print(f"Named ranges: {len(ranges)} defined")        # ✓
print(f"Formulas in row 91: {has_formulas}")         # ✓
print(f"Buildings found: {count}")                   # ✓
```

**Why this passes but pytest fails:**

| Check | Agent's Verify | pytest | Why Mismatch |
|-------|---------------|--------|--------------|
| Sheet order | `==` compares lists | Same | ✓ Usually safe |
| Named range count | `len(ranges) == 45` | Exact name matching | ✗ Names may differ |
| Formula presence | `is not None` | Exact string `==` | ✗ `"=SUM(A1:A10)" != "=SUM(A1:A10) "` |
| Row positions | Calculated `header + data + 1` | Hardcoded `79` | ✗ Off-by-one common |
| Calculated values | Not checked | `data_only=True` compares | ✗ Formula may ref wrong cell |

## Specific Mismatches in This Trace

The agent never discovered these potential issues:

1. **Row 91 vs expected row?**: Agent calculated totals at row 91 (headers + 85 staff + 1), but test may expect different.

2. **Named range typos**: Agent created `Sr15to19_Yr1` style names, but test may check `Sr15To19_Yr1` (case) or `Sr15_19_Yr1` (format).

3. **Formula equivalence**: Agent's occupancy formula `=0.94*OccCap_Yr1/4` might be equivalent to but string-different from test's expected `=OccCap_Yr1*0.94/4` or `=OccCap_Yr1/4*0.94`.

4. **Sheet name punctuation**: `Calculations --->` vs `Calculations --→` or `Calculations` (different arrow chars).

## The Correct Pattern

```bash
# INSTEAD OF writing verify_*.py:

# 1. Find and read the test
cat test_output.py | grep -A 5 "def test_"

# 2. Run it (will likely fail first time)
python3 -m pytest test_output.py -v --tb=short

# 3. Read exact failure message
#    "expected row 79, got 80" → fix calculation
#    "assert '=SUM(A1:A10)' == '=SUM( A1:A10)'" →match whitespace

# 4. Regenerate from scratch with fixes
#    (Never patch the .xlsx - always regenerate)

# 5. Run again until PASSED
python3 -m pytest test_output.py -v
```

## Prevention Checklist

Before claiming success, verify you haven't fallen into the trap:

- [ ] Did you run `find . -name "*test*.py"` and get a result?
- [ ] Did you run `pytest` on that file?
- [ ] Did you see "PASSED" or "FAILED" (not just your own ✓ marks)?
- [ ] Did you write any file with `verify` in the name? DELETE IT.
- [ ] Can you delete your verification script and still confirm success? (pytest is the only validation needed)

## When You Really Need Custom Verification

Rare cases where custom scripts help:
- **No test file exists** - use `quick_verifier.py` then manual Excel check
- **Debugging specific formula** - isolate in minimal test case, not full workbook
- **Performance testing** - after pytest already passes

**Rule**: Custom verification NEVER replaces pytest when tests exist.

## Real-World Example: 06_property_portfolio_refresh

In this trace, the agent:
- Generated `Portfolio_Services_Compensation.xlsx` with 8 sheets
- Created 21 named ranges (BaseSal_Yr1, etc.)
- Added formulas at row 91 for quarterly totals
- Wrote custom verification showing all ✓ marks
- **Never ran `test_output.py`**
- **Failed** with `test_output.py::test_legacy_pytest_suite`

The test likely checked:
- Exact sheet order (did agent include "Packet Notes"?)
- Exact named range names (case sensitivity)
- Exact formula strings in specific cells
- Hardcoded row numbers different from 91

**Lesson**: The agent's verification script gave false confidence. Only pytest reveals the truth.
