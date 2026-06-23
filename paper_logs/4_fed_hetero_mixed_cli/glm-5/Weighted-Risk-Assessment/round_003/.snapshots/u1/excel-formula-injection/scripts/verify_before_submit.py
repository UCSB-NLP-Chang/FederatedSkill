#!/usr/bin/env python3
"""
Pre-completion verification script for Excel formula injection tasks.
Run this BEFORE claiming task completion to catch common failure modes.

Usage:
    python verify_before_submit.py <output_file> [test_file_or_dir]

Exit codes:
    0: All checks passed
    1: Missing or invalid output file
    2: Test suite failed
    3: data_only=True detected in tests (formula values will be None)
"""
import sys
import subprocess
from pathlib import Path

def check_output_file(filepath):
    """Verify output file exists and is valid Excel."""
    path = Path(filepath)
    if not path.exists():
        print(f"ERROR: Output file does not exist: {filepath}")
        return False

    if not filepath.endswith('.xlsx'):
        print(f"WARNING: Output file is not .xlsx: {filepath}")

    try:
        import openpyxl
        wb = openpyxl.load_workbook(filepath)
        print(f"OK: Output file is valid Excel with sheets: {wb.sheetnames}")
        return True
    except Exception as e:
        print(f"ERROR: Cannot open output file: {e}")
        return False

def check_data_only_in_tests(test_path):
    """Check if tests use data_only=True (means they expect calculated values)."""
    import re

    path = Path(test_path)
    files = [path] if path.is_file() else list(path.glob('test*.py')) + list(path.glob('*_test.py'))

    for f in files:
        if not f.exists():
            continue
        content = f.read_text()
        if re.search(r'data_only\s*=\s*True', content):
            print(f"WARNING: {f.name} uses data_only=True")
            print("  Tests expect calculated values, but openpyxl cannot calculate.")
            print("  You may need to write static values or use a different approach.")
            return True
    return False

def run_tests(test_path):
    """Run the test suite and return True if all pass."""
    print(f"\nRunning tests: pytest {test_path} -v")
    result = subprocess.run(
        ['pytest', str(test_path), '-v'],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode == 0:
        print("OK: All tests passed")
        return True
    else:
        print("FAILED: Tests did not pass")
        return False

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    output_file = sys.argv[1]
    test_path = sys.argv[2] if len(sys.argv) > 2 else 'test_output.py'

    print("=== Pre-Completion Verification ===")
    print()

    # Check 1: Output file
    print("1. Checking output file...")
    if not check_output_file(output_file):
        sys.exit(1)

    # Check 2: data_only detection
    print("\n2. Checking test expectations...")
    has_data_only = check_data_only_in_tests(test_path)

    # Check 3: Run tests
    print("\n3. Running test suite...")
    if not run_tests(test_path):
        sys.exit(2)

    if has_data_only:
        print("\nWARNING: Tests passed but use data_only=True.")
        print("If tests check calculated values, they may fail in different environments.")

    print("\n=== All checks passed ===")
    sys.exit(0)

if __name__ == "__main__":
    main()
