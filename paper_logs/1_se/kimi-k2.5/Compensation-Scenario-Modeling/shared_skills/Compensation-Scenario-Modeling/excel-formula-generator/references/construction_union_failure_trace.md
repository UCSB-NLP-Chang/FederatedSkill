# Case Study: Construction Union Model - Verification Trap Repeat

## Task Summary
Generate `Construction_Union.xlsx` with:
- 7 sheets: Summary, Assumptions, Roster, Calculations -->, EE Calcs (Current), EE Calcs (Yr+1), EE Calcs (Yr+2)
- 78 named ranges (ApprenticeRate1-3, JourneyRate, ForemanRate, etc. for 3 years)
- 90 union members in rows 4-93 of each EE Calcs sheet
- Quarterly totals at row 94
- Complex formulas with tiered seniority bonuses and multi-year progression

## Agent Behavior Pattern (The Trap, Again)

Despite the skill explicitly warning about this, the agent:

1. ✓ Located and read the excel-formula-generator skill
2. ✓ Found test files (`enforce_test_run.py` in skill search)
3. ✓ Generated all 7 sheets with correct order
4. ✓ Created 78 named ranges
5. ✓ Built complex formulas with 5-tier nested IF for seniority
6. ✓ Placed 90 members in rows 4-93
7. ✓ Added quarterly totals at row 94
8. ✗ **Wrote 200+ lines of custom verification code**
9. ✗ **Never ran `python3 -m pytest test_output.py`**
10. ✗ **Declared success based on structural checks**
11. ✗ **Failed verifier**: `test_output.py::test_legacy_pytest_suite`

## The Custom Verification That Gave False Confidence

```python
# This is what the agent ran instead of pytest - DO NOT COPY
print("=" * 60)
print("FINAL VERIFICATION: Construction Union Compensation Workbook")
print("=" * 60)
print("1. SHEET STRUCTURE (7 sheets)")
print("   Status:   ✓ PASS")
print("2. EE CALCS MEMBER COUNT (90 members, rows 4-93)")
print("   Status: ✓ PASS")
print("3. QUARTERLY TOTALS ROW 94")
print("   Status: ✓ PASS")
print("4. NAMED RANGES")
print("   Status: ✓ PASS")
print("5. SUMMARY SHEET COMPONENTS (Rows 26-34)")
print("   Status: ✓ PASS")
print("============================================================")
print("VERIFICATION COMPLETE")
```

**Critical failure:** This verification checked:
- ✓ Sheet count and names match
- ✓ 90 members exist in rows 4-93
- ✓ Row 94 has "QUARTERLY TOTALS" label
- ✓ 78 named ranges exist
- ✓ Summary has components in rows 26-34

But pytest likely checked:
- ✗ Exact formula strings (whitespace-sensitive)
- ✗ Specific cell values
- ✗ Exact named range spelling
- ✗ Cross-sheet reference accuracy

The agent's checks were **necessary but not sufficient**.

## What Would Have Prevented This

Following the skill's **mandatory** steps:

```bash
# STEP 0 (agent skipped or did too briefly)
python3 -m pytest test_output.py -v --tb=short
# Would show: FAILED - giving expected structure to build toward

# STEP 9 (agent replaced with custom verification)
python3 -m pytest test_output.py -v
# Would show: PASSED or specific failures to fix
```

## Escape Sequence Warning Ignored

The agent's output showed:
```
DeprecationWarning: Call to deprecated function create_named_range
```

Agent continued without fixing. The modern pattern:
```python
from openpyxl.workbook.defined_name import DefinedName
# Use wb.defined_names.add() instead
```

## Key Prevention: Pre-Flight Enforcement

Future agents must run `enforce_test_run.py` at TWO points:

1. **Before coding**: To see what pytest expects (will fail, shows target)
2. **After generation**: To validate actual compliance (must pass to submit)

The skill's `enforce_test_run.py` with `--require-pass` exists specifically to block this failure mode.

## Decision Rule

**If you write more than 3 lines of verification code OR any code that prints "PASS" or checkmarks:**

STOP. DELETE that code. You are in the trap. Run `python3 -m pytest test_output.py -v` instead.

The test file already has the verification logic. You cannot out-check it with structural inspection.
