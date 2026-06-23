#!/usr/bin/env python3
"""Scan Excel formulas for unqualified cell references and fail if found."""
import sys
import re
import openpyxl

def check_unqualified(path, sheet_name):
    wb = openpyxl.load_workbook(path, data_only=False)
    ws = wb[sheet_name]
    # Matches cell refs like A1, B$2, $C3, $D$4 that are NOT preceded by SheetName!
    pattern = re.compile(r'(?<![A-Za-z0-9_!])(\$?[A-Z]+\$?\d+)(?![A-Za-z0-9_!])')
    issues = []
    for row in ws.iter_rows():
        for cell in row:
            if cell.value and isinstance(cell.value, str) and cell.value.startswith('='):
                matches = pattern.findall(cell.value)
                if matches:
                    issues.append(f"{cell.coordinate}: {cell.value} -> Unqualified refs: {matches}")
    if issues:
        print("FAIL: Unqualified references detected. Fix immediately:")
        for issue in issues:
            print(f"  {issue}")
        sys.exit(1)
    else:
        print("PASS: All references are fully qualified.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python check_unqualified.py <path> <sheet_name>")
        sys.exit(1)
    check_unqualified(sys.argv[1], sys.argv[2])
