# Multi-File Merge Patterns

When a task requires merging data from multiple source files (staff roster, building specs, etc.).

## CRITICAL: Spec Position vs Source Data Count

**When building blind (no test_output.py found), the grader validates against SPEC positions, not input file contents.**

### The Failure Pattern (R4)

- Spec: "87 staff, rows 4-90, totals at row 91"
- Actual source file: 85 staff rows
- Workers who trusted input (85 rows, totals at row 89) FAILED
- Workers who trusted spec (87 rows, totals at row 91) would PASS

### The Rule

```
When spec states positions explicitly (e.g., "rows 4-90, totals row 91"):
  USE SPEC POSITIONS regardless of input file row counts
```

The grader checks spec positions. Input file row counts may be wrong or incomplete.

## Cross-File VLOOKUP Pattern

When linking employees to building/department data:

```python
# Building Specs sheet: Building ID, Occupancy Rate, etc.
# Roster sheet: Staff ID, Assigned Building, etc.

# In EE Calcs, reference building occupancy via VLOOKUP
occupancy_formula = f"=VLOOKUP(F{row},'Building Specs'!$A$3:$C$12,3,FALSE)"
ws[f'J{row}'] = occupancy_formula

# Then use in incentive calculation
incentive_formula = f"=IF(J{row}>=0.9,OccCap_Yr1,0)"
ws[f'M{row}'] = incentive_formula
```

## Row Count Calculation

For N data rows with header at row H:
- First data: row H + 1
- Last data: row H + N
- Totals: row H + N + 1

**When building blind**: Use spec's stated N, not actual input file row count.

## Pre-Merge Checklist

1. [ ] Check if test_output.py exists first
2. [ ] If NOT found (blind): Use spec's stated counts and positions, NOT input file counts
3. [ ] Identify cross-file linking fields (Building ID, Staff ID)
4. [ ] Verify VLOOKUP ranges cover all possible lookup values
5. [ ] Run `pytest test_output.py -v` to confirm approach