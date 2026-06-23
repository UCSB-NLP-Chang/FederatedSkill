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
import re
from pathlib import Path

# Directories to exclude from search (skill libraries, package managers, etc.)
EXCLUDE_DIRS = {
    '.venv', 'venv', '__pycache__', 'site-packages', 'node_modules',
    '.qwen', '.claude', '.kimi', '.opencode', '.gemini', '.codex',
    '.config', '.factory', '.agents', 'skills', 'skill',
    '.local', '.cache', '.npm', '.nvm',
}

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

def find_tests_by_name(search_roots=None):
    """Search for test files by filename patterns."""
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
            
            # Skip excluded directories
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            
            for fname in filenames:
                if fname.endswith('.py') and (fname.startswith('test') or fname.endswith('_test.py')):
                    fpath = Path(dirpath) / fname
                    if fpath not in seen and is_test_file(fpath):
                        found.append(fpath)
                        seen.add(fpath)
    
    return found

def find_tests_by_content(search_roots=None):
    """Fallback: search for test patterns in ALL Python files, not just by name."""
    if search_roots is None:
        search_roots = [
            Path('/root'),
            Path('/workspace'),
            Path('/app'),
            Path('/tmp'),
            Path('/task'),
            Path.cwd(),
        ]
    
    found = []
    seen = set()
    
    test_patterns = [
        re.compile(r'def\s+test_'),
        re.compile(r'import\s+pytest'),
        re.compile(r'from\s+pytest\s+import'),
        re.compile(r'import\s+unittest'),
        re.compile(r'assert.*\.value'),
        re.compile(r'load_workbook.*data_only'),
    ]
    
    for root in search_roots:
        if not root.exists():
            continue
        
        for dirpath, dirnames, filenames in os.walk(root):
            depth = len(Path(dirpath).relative_to(root).parts)
            if depth > 5:
                dirnames.clear()
                continue
            
            # Skip excluded directories
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            
            for fname in filenames:
                if fname.endswith('.py'):
                    fpath = Path(dirpath) / fname
                    if fpath in seen:
                        continue
                    try:
                        content = fpath.read_text()
                        for pattern in test_patterns:
                            if pattern.search(content):
                                found.append(fpath)
                                seen.add(fpath)
                                break
                    except Exception:
                        pass
    
    return found

def main():
    search_root = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    roots = [search_root] if search_root else None
    
    # Phase 1: Search by filename
    tests = find_tests_by_name(roots)
    
    # Phase 2: If nothing found, search by content
    if not tests:
        print("No test files found by name. Searching by content patterns...")
        tests = find_tests_by_content(roots)
    
    if tests:
        print("Found test files:")
        for t in tests:
            print(f"  {t}")
        sys.exit(0)
    else:
        print("No test files found in standard locations.")
        print("Try searching manually:")
        print("  find / -name 'test*.py' -not -path '*/site-packages/*' -not -path '*/skills/*' -not -path '*/.qwen/*' -not -path '*/.claude/*' 2>/dev/null | head -20")
        print("  find / -name '*_test.py' -not -path '*/site-packages/*' -not -path '*/skills/*' 2>/dev/null | head -20")
        print("  find / -name '*.py' -mmin -60 -not -path '*/site-packages/*' -not -path '*/skills/*' 2>/dev/null")
        print("  grep -r 'def test_' /root --include='*.py' --exclude-dir=skills --exclude-dir=.qwen --exclude-dir=.claude 2>/dev/null | head -20")
        sys.exit(1)

if __name__ == "__main__":
    main()
