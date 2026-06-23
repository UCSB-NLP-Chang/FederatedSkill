#!/usr/bin/env python3
"""
Comprehensive test file discovery for Excel formula tasks.
Searches common directories, checks for pytest markers, and prioritizes likely test files.

Usage:
    python3 find_tests.py [search_root]

Exit codes:
    0 = Found test files (prints paths)
    1 = No test files found
"""
import sys
import os
from pathlib import Path

def is_test_file(filepath):
    """Check if a Python file looks like a test file."""
    try:
        content = filepath.read_text()
        # Look for pytest markers
        if 'def test_' in content or 'import pytest' in content:
            return True
        # Look for openpyxl assertions (common in formula tasks)
        if 'openpyxl' in content and ('assert' in content or 'load_workbook' in content):
            return True
    except Exception:
        pass
    return False

def find_tests(search_roots=None):
    """Search for test files across multiple directories."""
    if search_roots is None:
        search_roots = [
            Path.cwd(),
            Path('/root'),
            Path('/workspace'),
            Path('/app'),
            Path('/home'),
            Path('/root/output'),
            Path('/root/data'),
            Path('/root/tests'),
            Path('/tmp'),
            Path('/task'),
        ]
    
    found = []
    seen = set()
    
    # Priority patterns
    priority_names = ['test_output.py', 'test_formulas.py', 'test_workbook.py', 'test_excel.py']
    
    for root in search_roots:
        if not root.exists():
            continue
        
        # Check priority files first
        for name in priority_names:
            candidate = root / name
            if candidate.exists() and candidate not in seen:
                if is_test_file(candidate):
                    found.append(candidate)
                    seen.add(candidate)
        
        # Walk directory (limit depth to 5)
        for dirpath, dirnames, filenames in os.walk(root):
            depth = len(Path(dirpath).relative_to(root).parts)
            if depth > 5:
                dirnames.clear()
                continue
            
            # Skip virtualenvs and site-packages
            dirnames[:] = [d for d in dirnames if d not in ('.venv', 'venv', '__pycache__', 'site-packages', 'node_modules')]
            
            for fname in filenames:
                if fname.endswith('.py') and (fname.startswith('test') or fname.endswith('_test.py')):
                    fpath = Path(dirpath) / fname
                    if fpath not in seen and is_test_file(fpath):
                        found.append(fpath)
                        seen.add(fpath)
    
    return found

def main():
    search_root = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    roots = [search_root] if search_root else None
    
    tests = find_tests(roots)
    
    if tests:
        print("Found test files:")
        for t in tests:
            print(f"  {t}")
        sys.exit(0)
    else:
        print("No test files found in standard locations.")
        print("Try searching manually:")
        print("  find / -name 'test*.py' -not -path '*/site-packages/*' 2>/dev/null | head -20")
        print("  find / -name '*_test.py' -not -path '*/site-packages/*' 2>/dev/null | head -20")
        print("  find / -name '*.py' -mmin -60 2>/dev/null | grep -v site-packages")
        sys.exit(1)

if __name__ == "__main__":
    main()
