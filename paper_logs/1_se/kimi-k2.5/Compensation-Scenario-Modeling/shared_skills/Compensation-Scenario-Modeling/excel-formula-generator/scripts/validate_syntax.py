#!/usr/bin/env python3
"""
Validate Python syntax before execution to catch f-string parenthesis errors.
Usage: python3 validate_syntax.py <script_path>
"""

import ast
import sys

def validate_file(path):
    with open(path, 'r') as f:
        code = f.read()
    
    try:
        ast.parse(code)
        print(f"✓ {path}: Syntax valid")
        return True
    except SyntaxError as e:
        print(f"✗ {path}: Syntax error at line {e.lineno}, col {e.offset}")
        print(f"  {e.msg}")
        # Show context
        lines = code.split('\n')
        if e.lineno > 0 and e.lineno <= len(lines):
            print(f"  Line {e.lineno}: {lines[e.lineno-1]}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 validate_syntax.py <script_path>")
        sys.exit(1)
    
    success = all(validate_file(p) for p in sys.argv[1:])
    sys.exit(0 if success else 1)