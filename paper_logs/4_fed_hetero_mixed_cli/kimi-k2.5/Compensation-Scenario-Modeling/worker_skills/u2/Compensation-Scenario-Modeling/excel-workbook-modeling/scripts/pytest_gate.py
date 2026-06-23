#!/usr/bin/env python3
"""
Pytest Gate Script - MANDATORY verification before saving workbook.

This script runs pytest BEFORE saving and refuses to save if tests fail.
This is the structural fix for the pytest avoidance pattern.

Usage:
    python scripts/pytest_gate.py --save <workbook_path> --test <test_path>
    python scripts/pytest_gate.py --test-only <test_path>

Exit codes:
    0: Pytest passed, workbook saved (or test-only passed)
    1: Pytest failed, workbook NOT saved
    2: Test file not found
"""
import argparse
import subprocess
import sys
from pathlib import Path


def find_test_file(test_path=None):
    """Find test file, prioritizing test_output.py."""
    if test_path:
        path = Path(test_path)
        if path.exists():
            return path
        print(f"ERROR: Provided test path not found: {test_path}")
        return None

    # Search for test_output.py
    search_dirs = [Path("/root"), Path("/workspace"), Path("/app"), Path("/home"), Path(".")]
    for directory in search_dirs:
        if not directory.exists():
            continue
        candidate = directory / "test_output.py"
        if candidate.exists():
            return candidate

    # Also check current directory
    for pattern in ["test_output.py", "test_*.py"]:
        for candidate in Path(".").glob(pattern):
            content = candidate.read_text(errors='ignore')
            if 'pytest' in content or 'def test_' in content:
                return candidate

    return None


def run_pytest(test_path):
    """Run pytest and return True if all tests pass."""
    print("=" * 60)
    print("PYTEST GATE: Running tests BEFORE save operation")
    print("=" * 60)
    print(f"Test file: {test_path}")
    print()

    cmd = [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"]
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)

    result = subprocess.run(cmd)

    print("-" * 60)
    if result.returncode == 0:
        print("RESULT: All tests passed")
        return True
    else:
        print("RESULT: Tests FAILED - workbook will NOT be saved")
        return False


def save_workbook(workbook_path):
    """Save the workbook (called by the caller after gate passes)."""
    # This is a placeholder - actual save happens in the caller's code
    # This script just validates pytest passes first
    print(f"GATE PASSED: You may now save to {workbook_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Pytest gate for workbook saves")
    parser.add_argument("--test", "-t", help="Path to test file (auto-detect if not provided)")
    parser.add_argument("--save", "-s", help="Path to workbook being saved (informational)")
    parser.add_argument("--test-only", action="store_true", help="Only run tests, no save")

    args = parser.parse_args()

    # Find test file
    test_path = find_test_file(args.test)
    if not test_path:
        print("ERROR: No test file found")
        print("\nSearched:")
        print("  /root/test_output.py")
        print("  /workspace/test_output.py")
        print("  /app/test_output.py")
        print("  /home/test_output.py")
        print("  ./*.py")
        return 2

    # Run pytest
    passed = run_pytest(test_path)

    if passed:
        if args.save:
            print(f"\nWorkbook path for save: {args.save}")
        return 0
    else:
        print("\n" + "!" * 60)
        print("! TASK INCOMPLETE: Pytest must pass before saving")
        print("! Fix the failing tests and re-run this gate")
        print("!" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
