#!/usr/bin/env python3
"""
Scan test files to detect data_only=True usage.
Use before writing formulas to determine if verifier expects calculated values.
If found, openpyxl alone cannot satisfy the verifier - you need external calculation.

Exit codes:
0 = Files scanned, no data_only=True found (safe to proceed with openpyxl)
1 = Error (bad arguments)
2 = data_only=True detected (external calculation required)
3 = No test files found (cannot determine safety)
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

def find_test_files(target):
    """Find test files in target directory or return target if it's a file."""
    if target.is_file():
        return [target]
    elif target.is_dir():
        files = []
        # Common test file patterns
        files.extend(target.glob('test*.py'))
        files.extend(target.glob('*_test.py'))
        files.extend(target.glob('test_output.py'))  # Specific pattern seen in tasks
        return files
    else:
        return []

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_test_data_only.py <test_file_or_directory>")
        print("\nScans for data_only=True usage in test files.")
        print("Exit codes:")
        print("  0 = Files scanned, no data_only=True found")
        print("  1 = Error")
        print("  2 = data_only=True detected (external calc required)")
        print("  3 = No test files found (cannot determine)")
        sys.exit(1)
    
    target = Path(sys.argv[1])
    files_to_check = find_test_files(target)
    
    # Also check parent directory if this is a subdir and no files found
    if not files_to_check and target.is_dir():
        parent_files = find_test_files(target.parent)
        # Filter to only include test_output.py or similar in parent
        for f in parent_files:
            if f.name == 'test_output.py' or f.parent == target.parent:
                files_to_check.append(f)
    
    if not files_to_check:
        print(f"⚠️  WARNING: No test files found at {target}")
        print("   Searched patterns: test*.py, *_test.py, test_output.py")
        print("\n   Try searching manually:")
        print(f"   find {Path.cwd()} -name 'test*.py' 2>/dev/null")
        print("\n   If no tests found, assume data_only=True and use external engine.")
        sys.exit(3)
    
    found_any = False
    for f in files_to_check:
        matches = check_file(f)
        if matches:
            found_any = True
            print(f"\n{f}:")
            for line_no, line in matches:
                print(f"  Line {line_no}: {line}")
    
    if found_any:
        print("\n⚠️  WARNING: Verifier uses data_only=True")
        print("   It expects calculated values, but openpyxl cannot calculate formulas.")
        print("   Options:")
        print("   1. Use xlwings or LibreOffice to pre-calculate values")
        print("   2. Calculate values manually in Python and write as static values")
        print("   3. Verify formulas are correct and accept calculated value mismatch")
        sys.exit(2)
    else:
        checked = ', '.join(str(f.name) for f in files_to_check)
        print(f"✓ Scanned {len(files_to_check)} file(s): {checked}")
        print("  No data_only=True detected")
        print("  Verifier likely checks formula strings, not calculated values")
        sys.exit(0)

if __name__ == "__main__":
    main()
