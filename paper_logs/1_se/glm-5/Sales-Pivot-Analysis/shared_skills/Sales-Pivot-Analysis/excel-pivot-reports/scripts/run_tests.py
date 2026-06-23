#!/usr/bin/env python3
"""
Helper script to run pytest and display results.
Run this after generating any Excel report to verify correctness.
"""
import subprocess
import sys

def run_tests(test_file='test_output.py'):
    """Run pytest on the test file and return success status."""
    print(f"Running: pytest {test_file} -v")
    print("=" * 60)
    
    result = subprocess.run(
        ['pytest', test_file, '-v'],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    print("=" * 60)
    
    if result.returncode == 0:
        print("✓ All tests passed!")
        return True
    else:
        print("✗ Tests failed. Fix issues before declaring success.")
        return False

if __name__ == '__main__':
    test_file = sys.argv[1] if len(sys.argv) > 1 else 'test_output.py'
    success = run_tests(test_file)
    sys.exit(0 if success else 1)
