#!/usr/bin/env python3
"""
Enforcement helper: Prevents the common failure mode where agents 
write custom verification instead of running pytest.

Usage: python3 enforce_test_run.py <search_directory> [--require-pass]

This script:
1. Finds test files automatically
2. Runs them with pytest
3. Returns non-zero exit code on failure (blocking task completion)

Add to your generation workflow BEFORE claiming success.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def find_test_files(directory):
    """Find pytest test files."""
    tests = []
    for pattern in ['test_*.py', '*_test.py']:
        tests.extend(Path(directory).rglob(pattern))
    # Also check current dir
    for pattern in ['test*.py', '*test*.py']:
        tests.extend(Path('.').glob(pattern))
    return sorted(set(str(t) for t in tests if '__pycache__' not in str(t)))


def run_pytest(test_path, verbose=True):
    """Run pytest and return (success, output)."""
    cmd = ['python3', '-m', 'pytest', test_path, '-v']
    if not verbose:
        cmd = ['python3', '-m', 'pytest', test_path, '-q']
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout + result.stderr
    except FileNotFoundError:
        # pytest not installed, try running directly
        try:
            result = subprocess.run(
                ['python3', test_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, f"Failed to run test: {e}"
    except subprocess.TimeoutExpired:
        return False, "Test timed out after 60 seconds"


def main():
    parser = argparse.ArgumentParser(
        description='Enforce test file execution - prevents self-verification trap'
    )
    parser.add_argument('directory', nargs='?', default='.', 
                       help='Directory to search for test files')
    parser.add_argument('--require-pass', action='store_true',
                       help='Exit with error if tests fail (use in CI)')
    parser.add_argument('--test-file', help='Specific test file to run')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("TEST ENFORCEMENT: Verifying actual pytest execution")
    print("=" * 60)
    print()
    
    # Find test files
    if args.test_file:
        test_files = [args.test_file]
    else:
        test_files = find_test_files(args.directory)
        # Also check common locations
        for common in ['./test_output.py', './tests/test_output.py', './test_workbook.py']:
            if os.path.exists(common) and common not in test_files:
                test_files.insert(0, common)
    
    if not test_files:
        print("ERROR: No test files found!")
        print("Searched for: test_*.py, *_test.py")
        print()
        print("If tests don't exist, you may need to:")
        print("1. Check if this is a verification-only task")
        print("2. Look for a different test pattern")
        print("3. Confirm the test file location")
        sys.exit(1)
    
    print(f"Found {len(test_files)} test file(s):")
    for tf in test_files[:5]:
        print(f"  - {tf}")
    if len(test_files) > 5:
        print(f"  ... and {len(test_files) - 5} more")
    print()
    
    # Run the first/most relevant test
    primary_test = test_files[0]
    print(f"Running: {primary_test}")
    print("-" * 60)
    
    success, output = run_pytest(primary_test)
    print(output)
    print("-" * 60)
    
    if success:
        print("✓ TESTS PASSED")
        print()
        print("You may now declare the task complete.")
        return 0
    else:
        print("✗ TESTS FAILED")
        print()
        print("CRITICAL: Fix the failures before submitting.")
        print("DO NOT write custom verification scripts.")
        print("DO NOT rely on structural checks.")
        print()
        print("Next steps:")
        print("1. Read the failure message above")
        print("2. Look at the test source: cat", primary_test)
        print("3. Fix your generation code (not the .xlsx)")
        print("4. Regenerate from scratch")
        print("5. Run this script again")
        
        if args.require_pass:
            return 1
        return 1  # Always fail on test failure


if __name__ == '__main__':
    sys.exit(main())
