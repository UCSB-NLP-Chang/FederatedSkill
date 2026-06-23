#!/usr/bin/env python3
"""Find and run pytest tests for Excel formula validation.

Usage:
    python scripts/run_tests.py
    python scripts/run_tests.py /root
    python scripts/run_tests.py --verbose
"""
import subprocess
import sys
from pathlib import Path

def find_test_files(root_dir: str = "/root") -> list[Path]:
    """Find test files in common locations."""
    root = Path(root_dir)
    patterns = ["test_*.py", "*_test.py", "tests.py"]
    test_files = []
    for pattern in patterns:
        test_files.extend(root.glob(pattern))
        test_files.extend(root.glob(f"**/{pattern}"))
    return sorted(set(test_files))

def run_tests(root_dir: str = "/root", verbose: bool = True) -> int:
    """Run pytest on found test files. Returns exit code."""
    test_files = find_test_files(root_dir)
    if not test_files:
        print("ERROR: No test files found!")
        print("Searched patterns: test_*.py, *_test.py, tests.py")
        return 1
    
    print(f"Found test files: {[str(f) for f in test_files]}")
    
    # Try pytest first
    cmd = [sys.executable, "-m", "pytest"]
    if verbose:
        cmd.append("-v")
    cmd.extend([str(f) for f in test_files])
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=root_dir)
    
    if result.returncode != 0:
        print("\n=== TESTS FAILED ===")
        print("Do NOT declare completion. Fix issues and re-run.")
    else:
        print("\n=== ALL TESTS PASSED ===")
    
    return result.returncode

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("root_dir", nargs="?", default="/root")
    parser.add_argument("-v", "--verbose", action="store_true", default=True)
    args = parser.parse_args()
    sys.exit(run_tests(args.root_dir, args.verbose))
