#!/usr/bin/env python3
"""
Scan test files to detect data_only=True usage.
Use before writing formulas to determine if verifier expects calculated values.
If found, openpyxl alone cannot satisfy the verifier - you need external calculation.
"""
import sys
import re
from pathlib import Path

def check_file(filepath):
    """Check a Python test file for data_only=True patterns."""
    content = Path(filepath).read_text()

    # Patterns that indicate data_only usage
    patterns = [
        r'data_only\s*=\s*True',
        r'load_workbook.*data_only',
        r'data_only.*load_workbook'
    ]

    matches = []
    for i, line in enumerate(content.split('\n'), 1):
        for pattern in patterns:
            if re.search(pattern, line):
                matches.append((i, line.strip()))
                break

    return matches

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_test_data_only.py <test_file_or_directory>")
        print("\nScans for data_only=True usage in test files.")
        print("If found, the verifier expects calculated values - openpyxl alone will fail.")
        sys.exit(1)

    target = Path(sys.argv[1])
    files_to_check = []

    if target.is_file():
        files_to_check.append(target)
    elif target.is_dir():
        files_to_check.extend(target.glob('test*.py'))
        files_to_check.extend(target.glob('*_test.py'))

    found_any = False
    for f in files_to_check:
        matches = check_file(f)
        if matches:
            found_any = True
            print(f"\n{f}:")
            for line_no, line in matches:
                print(f"  Line {line_no}: {line}")

    if found_any:
        print("\nWARNING: Verifier uses data_only=True")
        print("   It expects calculated values, but openpyxl cannot calculate formulas.")
        print("   Options:")
        print("   1. Use xlwings or LibreOffice to pre-calculate values")
        print("   2. Calculate values manually in Python and write as static values")
        print("   3. Verify formulas are correct and accept calculated value mismatch")
        sys.exit(2)
    else:
        print("OK: No data_only=True detected in test files")
        print("  Verifier likely checks formula strings, not calculated values")
        sys.exit(0)

if __name__ == "__main__":
    main()
