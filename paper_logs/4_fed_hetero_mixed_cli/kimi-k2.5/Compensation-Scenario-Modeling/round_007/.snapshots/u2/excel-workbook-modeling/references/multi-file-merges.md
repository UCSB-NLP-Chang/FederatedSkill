# Multi-File Merge Patterns

When a task requires merging data from multiple source files.

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

## Source Count vs Specification Mismatch

When the specification states N items but source file has M:

1. **Count actual source data first** - Don't assume spec is accurate
2. **Use actual source counts** for row calculations:
   - If source has 85 staff starting at row 5, data ends at row 89
   - Totals row = last_data_row + 1 = row 90 (if totals label in same row) or row 89
3. **Document the discrepancy** in your output
4. **Run pytest to verify** - The test may expect spec count OR actual count

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
# WRONG: Using spec count (87) when source has 85
totals_row = 4 + 87  # = 91, but data ends at 88

# CORRECT: Calculate from actual source count
totals_row = 4 + actual_staff_count  # = 89 for 85 staff
```

## Verification Checklist for Multi-File Tasks

- [ ] Counted data rows in ALL source files before building
- [ ] Identified key fields for cross-file linking (Building ID, Staff ID, etc.)
- [ ] VLOOKUP ranges cover all possible lookup values
- [ ] Totals row calculated from actual source count, not spec count
- [ ] Run `pytest test_output.py -v` to verify expected counts