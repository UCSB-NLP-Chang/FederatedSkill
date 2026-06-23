#!/usr/bin/env python3
"""
Verification script for statistical process analysis outputs.
Run this before claiming task completion.

Usage:
    python scripts/verify_outputs.py
"""
import subprocess
import sys
import os

def run_tests():
    """Run pytest on test files in current directory."""
    test_files = [f for f in os.listdir('.') if f.startswith('test') and f.endswith('.py')]
    
    if not test_files:
        print("No test files found in current directory")
        return True
    
    all_passed = True
    for test_file in test_files:
        print(f"\nRunning {test_file}...")
        result = subprocess.run(['pytest', test_file, '-v'], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode != 0:
            all_passed = False
    
    return all_passed

def validate_json_metrics():
    """Validate JSON metrics file has statistically sane values."""
    import json
    import glob
    
    json_files = glob.glob('*metrics*.json') + glob.glob('*_metrics.json')
    
    if not json_files:
        print("No metrics JSON files found")
        return True
    
    all_valid = True
    for filepath in json_files:
        try:
            with open(filepath) as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"ERROR: Could not read {filepath}: {e}")
            all_valid = False
            continue
        
        # Check p-values are in [0, 1]
        def check_pvalue(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if 'p_value' in k.lower() or 'pvalue' in k.lower():
                        if isinstance(v, (int, float)) and not (0 <= v <= 1):
                            print(f"ERROR: {path}.{k} = {v} not in [0, 1]")
                            return False
                    if check_pvalue(v, f"{path}.{k}") is False:
                        return False
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    if check_pvalue(v, f"{path}[{i}]") is False:
                        return False
            return True
        
        if not check_pvalue(data, filepath):
            all_valid = False
        else:
            print(f"✓ {filepath} passed sanity checks")
    
    return all_valid

def main():
    print("=== Statistical Process Analysis Verification ===")
    print("Run this script BEFORE claiming task completion.\n")
    
    # Run tests
    print("1. Running test suite...")
    tests_passed = run_tests()
    
    # Validate JSON
    print("\n2. Validating JSON metrics...")
    json_valid = validate_json_metrics()
    
    print("\n" + "="*50)
    if tests_passed and json_valid:
        print("✓ All verifications passed. Safe to claim completion.")
        return 0
    else:
        print("✗ Verification FAILED. Fix issues before claiming completion.")
        return 1

if __name__ == '__main__':
    sys.exit(main())