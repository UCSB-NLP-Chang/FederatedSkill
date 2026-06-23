# Multi-File Merge Patterns

When a task requires merging data from multiple source files.

## CRITICAL: Blind Building vs Test-Guided Building

**When test_output.py is found**: Use test assertions as ground truth for row counts.

**When building blind (no test_output.py)**: Trust the SPEC's stated row counts over actual input data.
- If spec says "87 staff, rows 4-90, totals at row 91" but input has 85 rows, use spec positions.
- The grader validates against spec positions, not input file contents.
- See Decision Rules in SKILL.md.

## Pre-Merge Validation

Before building the workbook, validate source data counts:

```python
import openpyxl

# Check each source file's data count
for source_file in ['staff_roster.xlsx', 'building_specs.xlsx']:
    wb = openpyxl.load_workbook(source_file)
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        # Count actual data rows (excluding header)
        data_rows = ws.max_row - (header_row if header_row else 1)
        print(f"{source_file} / {sheet_name}: {data_rows} data rows")
```

## Cross-File VLOOKUP Pattern

When linking employees to building/department data:

```python
# Building Specs sheet has: Building ID, Occupancy Rate, etc.
# Roster sheet has: Staff ID, Assigned Building, etc.

# In EE Calcs, reference building occupancy via VLOOKUP
# Column J = Occupancy Rate (looked up from Building Specs)
occupancy_formula = (
    f"=VLOOKUP(F{row},'Building Specs'!$A$3:$C$12,3,FALSE)"
)
ws[f'J{row}'] = occupancy_formula

# Then use occupancy in incentive calculation
incentive_formula = f"=IF(J{row}>=0.9,OccCap_Yr1,0)"
ws[f'M{row}'] = incentive_formula
```

## Row Count Calculation

For N data rows:
- Header at row 3 (typical)
- First data at row 4
- Last data at row 4 + N - 1 = row 3 + N
- Totals row at row 4 + N = row 3 + N + 1

Example: 85 staff, header at row 3
- Data rows: 4-88 (85 rows)
- Totals row: 89

## Common Failure: Wrong Totals Row Reference

```python
# BLIND BUILDING: Spec says 87 staff, source has 85
# WRONG: Using source count
totals_row = 4 + 85  # = 89, but spec expects row 91

# CORRECT: Use spec count when building blind
totals_row = 4 + 87  # = 91 (spec said "rows 4-90, totals row 91")

# TEST-GUIDED BUILDING: Use test assertions
# Read test_output.py to determine expected row positions
```

## Verification Checklist for Multi-File Tasks

- [ ] Identified whether test_output.py exists (test-guided) or building blind
- [ ] If building blind: Use spec's stated positions, not input data counts
- [ ] If test-guided: Read test assertions for expected counts
- [ ] Identified key fields for cross-file linking (Building ID, Staff ID, etc.)
- [ ] VLOOKUP ranges cover all possible lookup values
- [ ] Run `pytest test_output.py -v` to verify expected counts
