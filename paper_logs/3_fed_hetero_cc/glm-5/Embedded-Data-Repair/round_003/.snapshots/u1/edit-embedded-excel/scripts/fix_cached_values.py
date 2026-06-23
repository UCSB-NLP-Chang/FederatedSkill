#!/usr/bin/env python3
"""
Fix cached formula values in an Excel file after openpyxl edits.

openpyxl preserves formulas but may leave cached <v> values empty or stale.
This script patches the worksheet XML to set correct cached values.

Usage:
    python3 fix_cached_values.py <input.xlsx> <output.xlsx> <cell>=<value> ...

Example:
    python3 fix_cached_values.py /tmp/embedded.xlsx /tmp/fixed.xlsx G4=2 E5=0.5
"""

import argparse
import zipfile
import re
import io


def fix_cached_values(input_xlsx, output_xlsx, cell_values):
    """
    Fix cached values for formula cells in an Excel file.
    
    Args:
        input_xlsx: Path to input Excel file
        output_xlsx: Path to output Excel file
        cell_values: Dict mapping cell refs to computed values
    """
    # Read all entries from input
    with zipfile.ZipFile(input_xlsx, 'r') as zin:
        entries = {name: zin.read(name) for name in zin.namelist()}
    
    # Fix each worksheet
    for sheet_name in [n for n in entries if n.startswith('xl/worksheets/sheet')]:
        xml = entries[sheet_name].decode('utf-8')
        modified = False
        
        for cell_ref, value in cell_values.items():
            # Pattern matches: <c r="G4"><f>...</f><v>old</v></c> or <c r="G4"><f>...</f><v /></c>
            pattern = rf'(<c r="{cell_ref}"><f>[^<]*</f><v[^>]*>)[^<]*(</v></c>)'
            if re.search(pattern, xml):
                replacement = rf'\g<1>{value}\g<2>'
                xml = re.sub(pattern, replacement, xml)
                modified = True
                print(f"Fixed cached value for {cell_ref} -> {value}")
        
        if modified:
            entries[sheet_name] = xml.encode('utf-8')
    
    # Write output
    with zipfile.ZipFile(output_xlsx, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in entries.items():
            zout.writestr(name, data)
    
    print(f"Saved to: {output_xlsx}")


def detect_empty_cached_values(xlsx_path):
    """
    Detect formula cells with empty cached values.
    
    Returns list of cell refs with empty <v /> tags.
    """
    empty_cells = []
    
    with zipfile.ZipFile(xlsx_path, 'r') as z:
        for name in z.namelist():
            if name.startswith('xl/worksheets/sheet'):
                xml = z.read(name).decode('utf-8')
                # Find formula cells with empty <v /> or <v></v>
                matches = re.findall(r'<c r="([A-Z]+\d+)"><f>[^<]+</f><v ?/></c>', xml)
                empty_cells.extend(matches)
    
    return empty_cells


def main():
    parser = argparse.ArgumentParser(
        description='Fix cached formula values in Excel file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Fix specific cells
  python3 fix_cached_values.py input.xlsx output.xlsx G4=2 E5=0.5
  
  # Detect empty cached values
  python3 fix_cached_values.py input.xlsx --detect-only
"""
    )
    parser.add_argument('input_xlsx', help='Input Excel file')
    parser.add_argument('output_xlsx', nargs='?', help='Output Excel file')
    parser.add_argument('cells', nargs='*', help='Cell=value pairs (e.g., G4=2)')
    parser.add_argument('--detect-only', action='store_true', 
                        help='Only detect empty cached values, do not fix')
    
    args = parser.parse_args()
    
    if args.detect_only:
        empty = detect_empty_cached_values(args.input_xlsx)
        if empty:
            print(f"Formula cells with empty cached values: {empty}")
        else:
            print("No empty cached values found.")
        return
    
    if not args.output_xlsx or not args.cells:
        parser.error("output_xlsx and cell=value pairs required when not using --detect-only")
    
    # Parse cell=value pairs
    cell_values = {}
    for cv in args.cells:
        if '=' not in cv:
            parser.error(f"Invalid format '{cv}'. Use CELL=VALUE format (e.g., G4=2)")
        cell, value = cv.split('=', 1)
        # Try to convert to number
        try:
            value = float(value)
            if value == int(value):
                value = int(value)
        except ValueError:
            pass  # Keep as string
        cell_values[cell.upper()] = value
    
    fix_cached_values(args.input_xlsx, args.output_xlsx, cell_values)


if __name__ == '__main__':
    main()
