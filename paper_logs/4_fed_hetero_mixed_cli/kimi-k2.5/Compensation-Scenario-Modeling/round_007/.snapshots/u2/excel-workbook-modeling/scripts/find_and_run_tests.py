#!/usr/bin/env python3
"""
Find and run pytest tests for Excel workbook tasks.
Searches exhaustively for test_output.py and runs with verbose output.

Usage:
    python find_and_run_tests.py [optional_path_to_test.py]

If test file is found, runs pytest and exits with pytest's exit code.
If not found, prints search locations and exits with code 1.
"""
import subprocess
import sys
from pathlib import Path


def find_test_files():
    """Exhaustively search for test files."""
    test_files = []
    
    # Directories to search (priority order)
    search_dirs = [
        Path("/root"),
        Path("/workspace"),
        Path("/app"),
        Path("/home"),
        Path("."),
    ]
    
    # Search patterns
    patterns = [
        "test_output.py",
        "test_*.py",
        "*_test.py",
    ]
    
    found_paths = set()
    
    for directory in search_dirs:
        if not directory.exists():
            continue
            
        for pattern in patterns:
            if pattern == "test_output.py":
                # Direct check
                candidate = directory / "test_output.py"
                if candidate.exists() and candidate not in found_paths:
                    test_files.append(candidate)
                    found_paths.add(candidate)
            else:
                # Glob pattern
                for candidate in directory.glob(pattern):
                    if candidate.is_file() and candidate not in found_paths:
                        # Check if it's a pytest file
                        content = candidate.read_text(errors='ignore')
                        if 'pytest' in content or 'def test_' in content:
                            test_files.append(candidate)
                            found_paths.add(candidate)
    
    # Also check common subdirectories
    for directory in search_dirs:
        for subdir in ["tests", "test", "."]:
            test_dir = directory / subdir
            if test_dir.exists():
                for candidate in test_dir.glob("test_*.py"):
                    if candidate.is_file() and candidate not in found_paths:
                        content = candidate.read_text(errors='ignore')
                        if 'pytest' in content or 'def test_' in content:
                            test_files.append(candidate)
                            found_paths.add(candidate)
    
    return test_files


def run_pytest(test_path):
    """Run pytest on the given test file."""
    cmd = [sys.executable, "-m", "pytest", str(test_path), "-v"]
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    
    result = subprocess.run(cmd)
    return result.returncode


def main():
    # Check if path provided as argument
    if len(sys.argv) > 1:
        test_path = Path(sys.argv[1])
        if test_path.exists():
            print(f"Using provided test file: {test_path}")
            return run_pytest(test_path)
        else:
            print(f"Provided test file not found: {test_path}")
            return 1
    
    # Search for test files
    print("Searching for test files...")
    test_files = find_test_files()
    
    # Prioritize test_output.py if found
    test_output_files = [f for f in test_files if f.name == "test_output.py"]
    other_test_files = [f for f in test_files if f.name != "test_output.py"]
    
    if test_output_files:
        print(f"Found test_output.py: {test_output_files[0]}")
        return run_pytest(test_output_files[0])
    elif other_test_files:
        print(f"Found test files: {[str(f) for f in other_test_files]}")
        print(f"Running first match: {other_test_files[0]}")
        return run_pytest(other_test_files[0])
    else:
        print("ERROR: No test files found.")
        print("\nSearched in:")
        print("  /root")
        print("  /workspace")  
        print("  /app")
        print("  /home")
        print("  Current directory")
        print("\nRun with explicit path if test exists elsewhere:")
        print(f"  python {sys.argv[0]} /path/to/test_output.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
