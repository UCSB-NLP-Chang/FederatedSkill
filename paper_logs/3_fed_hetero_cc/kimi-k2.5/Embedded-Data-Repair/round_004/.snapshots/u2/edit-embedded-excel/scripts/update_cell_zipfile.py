#!/usr/bin/env python3
"""Update a cell value in an embedded Excel workbook inside a PPTX file.
Pure zipfile/XML approach - no openpyxl dependency.

Usage:
    python update_cell_zipfile.py input.pptx output.pptx cell_ref new_value
    python update_cell_zipfile.py input.pptx output.pptx C4 1.159
"""
import sys
import zipfile
import re
from io import BytesIO

def update_embedded_cell(pptx_path, output_path, cell_ref, new_value):
    """Update a cell in the first embedded Excel workbook found in a PPTX."""

    # Read original PPTX
    with zipfile.ZipFile(pptx_path, 'r') as pptx:
        pptx_entries = {name: pptx.read(name) for name in pptx.namelist()}

    # Find embedded workbook
    xlsx_path = next((n for n in pptx_entries if 'embeddings' in n and n.endswith('.xlsx')), None)
    if not xlsx_path:
        raise ValueError("No embedded Excel workbook found")

    # Read embedded XLSX
    xlsx_bytes = pptx_entries[xlsx_path]
    with zipfile.ZipFile(BytesIO(xlsx_bytes), 'r') as xlsx:
        xlsx_entries = {name: xlsx.read(name) for name in xlsx.namelist()}

    # Update sheet1.xml - modify the target cell
    sheet_path = 'xl/worksheets/sheet1.xml'
    sheet_xml = xlsx_entries[sheet_path].decode('utf-8')

    # Pattern to find and update the cell value
    # Matches: <c r="CELL_REF" t="n"><v>OLD_VALUE</v></c>
    pattern = rf'(<c r="{cell_ref}"[^>]*>.*?<v>)[^<]*(</v>.*?</c>)'
    replacement = rf'\g<1>{new_value}\g<2>'

    new_sheet = re.sub(pattern, replacement, sheet_xml, flags=re.DOTALL)
    if new_sheet == sheet_xml:
        raise ValueError(f"Cell {cell_ref} not found or has unsupported format")

    xlsx_entries[sheet_path] = new_sheet.encode('utf-8')

    # Rebuild XLSX
    xlsx_buffer = BytesIO()
    with zipfile.ZipFile(xlsx_buffer, 'w', zipfile.ZIP_DEFLATED) as new_xlsx:
        for name, data in xlsx_entries.items():
            new_xlsx.writestr(name, data)
    pptx_entries[xlsx_path] = xlsx_buffer.getvalue()

    # Rebuild PPTX
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as new_pptx:
        for name, data in pptx_entries.items():
            new_pptx.writestr(name, data)

    print(f"Updated cell {cell_ref} to {new_value}")

if __name__ == '__main__':
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)
    update_embedded_cell(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])