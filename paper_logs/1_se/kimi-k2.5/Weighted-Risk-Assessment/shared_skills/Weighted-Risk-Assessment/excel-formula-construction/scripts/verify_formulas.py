#!/usr/bin/env python3
"""
Verify that Excel formulas evaluate to expected values.

Usage: python3 verify_formulas.py <workbook_path> \
         --task-sheet Task --data-sheet Data \
         --checks "Task!H12=Data!H21" \
         --checks "Task!I14=Data!I24"

Or use a config file with spot-check definitions.
"""

import openpyxl
import argparse
import sys
from pathlib import Path

try:
    from xlcalculator import ModelCompiler, Evaluator
    XLCALCULATOR_AVAILABLE = True
except ImportError:
    XLCALCULATOR_AVAILABLE = False


def parse_check(check_str):
    """Parse check string like 'Task!H12=Data!H21' into components."""
    if '=' not in check_str:
        raise ValueError(f"Check must contain '=': {check_str}")
    actual, expected = check_str.split('=', 1)
    return actual.strip(), expected.strip()


def get_cell_value(wb, cell_ref):
    """Get value from workbook using A1 notation like 'Sheet!A1'."""
    if '!' not in cell_ref:
        raise ValueError(f"Cell reference must include sheet name: {cell_ref}")
    sheet_name, coord = cell_ref.rsplit('!', 1)
    ws = wb[sheet_name]
    return ws[coord].value


def evaluate_with_xlcalculator(wb_path, cell_ref):
    """Evaluate formula using xlcalculator."""
    if not XLCALCULATOR_AVAILABLE:
        return None, "xlcalculator not installed"
    try:
        compiler = ModelCompiler()
        model = compiler.read_and_parse_archive(wb_path)
        evaluator = Evaluator(model)
        result = evaluator.evaluate(cell_ref)
        return result, None
    except Exception as e:
        return None, str(e)


def verify_with_openpyxl(wb_path, checks):
    """Verify by loading with data_only=True and comparing values."""
    wb = openpyxl.load_workbook(wb_path, data_only=True)
    
    results = []
    for actual_ref, expected_ref in checks:
        try:
            actual_val = get_cell_value(wb, actual_ref)
            expected_val = get_cell_value(wb, expected_ref)
            
            match = actual_val == expected_val
            results.append({
                'actual_ref': actual_ref,
                'expected_ref': expected_ref,
                'actual_val': actual_val,
                'expected_val': expected_val,
                'match': match
            })
        except Exception as e:
            results.append({
                'actual_ref': actual_ref,
                'expected_ref': expected_ref,
                'error': str(e),
                'match': False
            })
    
    return results


def verify_with_xlcalculator(wb_path, checks):
    """Verify by evaluating formulas with xlcalculator."""
    results = []
    for actual_ref, expected_ref in checks:
        actual_val, error = evaluate_with_xlcalculator(wb_path, actual_ref)
        expected_val, _ = evaluate_with_xlcalculator(wb_path, expected_ref)
        
        if error:
            results.append({
                'actual_ref': actual_ref,
                'error': error,
                'match': False
            })
            continue
            
        match = actual_val == expected_val
        results.append({
            'actual_ref': actual_ref,
            'expected_ref': expected_ref,
            'actual_val': actual_val,
            'expected_val': expected_val,
            'match': match
        })
    
    return results


def print_results(results, method):
    """Print verification results."""
    print(f"\n=== Verification Results ({method}) ===")
    
    passed = 0
    failed = 0
    
    for r in results:
        if 'error' in r:
            print(f"❌ {r['actual_ref']}: ERROR - {r['error']}")
            failed += 1
        elif r['match']:
            print(f"✅ {r['actual_ref']}: {r['actual_val']} == {r['expected_val']}")
            passed += 1
        else:
            print(f"❌ {r['actual_ref']}: {r['actual_val']} != {r['expected_val']} (expected from {r['expected_ref']})")
            failed += 1
    
    print(f"\nPassed: {passed}, Failed: {failed}")
    return failed == 0


def main():
    parser = argparse.ArgumentParser(description='Verify Excel formulas evaluate correctly')
    parser.add_argument('workbook', help='Path to workbook')
    parser.add_argument('--checks', action='append', required=True,
                        help='Check definitions like "Task!H12=Data!H21"')
    parser.add_argument('--method', choices=['openpyxl', 'xlcalculator', 'auto'],
                        default='auto', help='Verification method')
    
    args = parser.parse_args()
    
    checks = [parse_check(c) for c in args.checks]
    
    # Determine method
    method = args.method
    if method == 'auto':
        method = 'xlcalculator' if XLCALCULATOR_AVAILABLE else 'openpyxl'
    
    print(f"Using verification method: {method}")
    
    if method == 'xlcalculator':
        if not XLCALCULATOR_AVAILABLE:
            print("xlcalculator not available, falling back to openpyxl")
            method = 'openpyxl'
        else:
            results = verify_with_xlcalculator(args.workbook, checks)
    
    if method == 'openpyxl':
        results = verify_with_openpyxl(args.workbook, checks)
    
    success = print_results(results, method)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
