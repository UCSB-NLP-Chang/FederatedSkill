#!/usr/bin/env python3
"""Dump Excel formula strings from specified ranges for exact verifier comparison."""
import sys
import openpyxl

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python verify_formulas.py <path> <sheet> <range1> [range2 ...]")
        sys.exit(1)
    path, sheet = sys.argv[1], sys.argv[2]
    ranges = sys.argv[3:]
    
    wb = openpyxl.load_workbook(path, data_only=False)
    ws = wb[sheet]
    
    for r in ranges:
        print(f"--- {r} ---")
        for row in ws[r]:
            for cell in row:
                if cell.value and str(cell.value).startswith('='):
                    print(f"{cell.coordinate}: {cell.value}")
