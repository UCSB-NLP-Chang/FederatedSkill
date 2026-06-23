#!/usr/bin/env python3
"""
Update a cell value in an Excel workbook embedded in a PowerPoint file.
Preserves formulas and repackages the PPTX.

Usage:
    python3 update_embedded_excel.py <input.pptx> <output.pptx> <cell> <value> [--sheet SHEET] [--embed-path PATH]

Example:
    python3 update_embedded_excel.py /root/input.pptx /root/output.pptx C4 1.1590 --sheet "Spot Grid"
"""

import argparse
import zipfile
import tempfile
import os
import shutil

def find_excel_embedding(pptx_path):
    """Find the first Excel embedding path in a PPTX."""
    with zipfile.ZipFile(pptx_path, 'r') as z:
        for name in z.namelist():
            if 'embeddings' in name and name.endswith('.xlsx'):
                return name
    raise ValueError(f"No Excel embedding found in {pptx_path}")

def update_embedded_excel(input_pptx, output_pptx, cell_ref, new_value, sheet_name=None, embed_path=None):
    """Update a cell in embedded Excel and save new PPTX."""
    try:
        import openpyxl
    except ImportError:
        raise RuntimeError("openpyxl not installed. Run: pip install openpyxl --break-system-packages")

    if embed_path is None:
        embed_path = find_excel_embedding(input_pptx)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract Excel
        excel_path = os.path.join(tmpdir, 'embedded.xlsx')
        with zipfile.ZipFile(input_pptx, 'r') as z:
            with open(excel_path, 'wb') as f:
                f.write(z.read(embed_path))

        # Load and inspect
        wb = openpyxl.load_workbook(excel_path)
        if sheet_name:
            ws = wb[sheet_name]
        else:
            ws = wb.active

        cell = ws[cell_ref]

        # Safety check: don't overwrite formulas unless forced
        if cell.data_type == 'f':
            raise ValueError(
                f"Cell {cell_ref} contains formula: {cell.value}. "
                f"Edit the source value cell, not the formula cell."
            )

        # Update and save
        old_value = cell.value
        cell.value = new_value
        wb.save(excel_path)

        # Repackage PPTX
        with zipfile.ZipFile(input_pptx, 'r') as zin:
            with zipfile.ZipFile(output_pptx, 'w', zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    if item.filename == embed_path:
                        zout.write(excel_path, embed_path)
                    else:
                        zout.writestr(item, zin.read(item.filename))

        print(f"Updated {cell_ref}: {old_value} -> {new_value}")
        print(f"Saved to: {output_pptx}")
        return True

def main():
    parser = argparse.ArgumentParser(description='Update embedded Excel in PPTX')
    parser.add_argument('input_pptx', help='Input PowerPoint file')
    parser.add_argument('output_pptx', help='Output PowerPoint file')
    parser.add_argument('cell', help='Cell reference (e.g., C4)')
    parser.add_argument('value', help='New value')
    parser.add_argument('--sheet', help='Sheet name (default: active sheet)')
    parser.add_argument('--embed-path', help='Explicit embedding path in ZIP')
    parser.add_argument('--force-formula', action='store_true', help='Allow overwriting formula cells')

    args = parser.parse_args()

    # Convert value to number if possible
    try:
        value = float(args.value)
        if value == int(value):
            value = int(value)
    except ValueError:
        value = args.value

    update_embedded_excel(
        args.input_pptx,
        args.output_pptx,
        args.cell,
        value,
        args.sheet,
        args.embed_path
    )

if __name__ == '__main__':
    main()