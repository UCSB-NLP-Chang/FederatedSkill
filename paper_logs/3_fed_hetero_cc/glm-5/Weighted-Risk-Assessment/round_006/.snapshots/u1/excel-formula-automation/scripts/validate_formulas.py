#!/usr/bin/env python3
"""
Validation script for Excel formula reference locking.
Run after formula injection to verify $ signs in correct positions.
Exits non-zero if violations found.
"""
import sys
import re
import openpyxl

def check_reference_locking(formula: str) -> list:
    """Check formula for proper $ locking. Returns list of violations."""
    violations = []

    # Check for fully locked ranges (should have $ before both row and col in range references)
    # Pattern: Sheet!$X$nn:$Y$mm (fully locked lookup range)
    range_pattern = r'[A-Z]+!\$[A-Z]+\$\d+:\$[A-Z]+\$\d+'
    ranges = re.findall(range_pattern, formula)

    # Check for row-locked statistics ranges: H$35:H$40
    stat_pattern = r'[A-Z]+\$\d+:[A-Z]+\$\d+'
    stat_ranges = re.findall(stat_pattern, formula)

    # Warn if ranges lack locking
    if 'INDEX' in formula or 'MATCH' in formula:
        # Lookup formulas should have fully locked ranges
        if not re.search(r'\$[A-Z]+\$\d+:\$[A-Z]+\$\d+', formula):
            violations.append("INDEX/MATCH formula lacks fully locked range ($A$1:$B$10)")

    return violations

def validate_workbook(path: str) -> bool:
    """Validate all formulas in workbook. Returns True if valid."""
    wb = openpyxl.load_workbook(path, data_only=False)
    all_valid = True

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.value and str(cell.value).startswith('='):
                    violations = check_reference_locking(str(cell.value))
                    if violations:
                        print(f"FAIL: {ws.title}!{cell.coordinate}: {violations}")
                        all_valid = False

    if all_valid:
        print(f"PASS: All formulas have valid reference locking")
    return all_valid

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_formulas.py <workbook.xlsx>")
        sys.exit(1)

    if not validate_workbook(sys.argv[1]):
        sys.exit(1)
