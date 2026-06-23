#!/usr/bin/env python3
"""Update a cell value in an embedded Excel workbook inside a PPTX/DOCX file.
Usage: python update_embedded_xlsx.py <host_file> <embed_path> <cell_ref> <new_value> <output_file> [--sheet sheetN.xml]
Example: python update_embedded_xlsx.py input.pptx ppt/embeddings/Microsoft_Excel_Worksheet.xlsx C4 1.1590 output.pptx
Example: python update_embedded_xlsx.py input.pptx ppt/embeddings/Microsoft_Excel_Worksheet.xlsx F8 2.0 output.pptx --sheet sheet2.xml

Note: For numeric values, pass the raw float (e.g., 1/0.8645). The script uses repr() for full precision.
"""
import sys
import argparse
import zipfile
import io
import xml.etree.ElementTree as ET

NS = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def update_cell(sheet_xml: str, cell_ref: str, new_value: str) -> str:
    root = ET.fromstring(sheet_xml)
    ns_uri = NS['ns']
    for c in root.findall('.//ns:c', NS):
        if c.get('r') == cell_ref:
            # Safety check: do not overwrite formula cells
            if c.find('.//ns:f', NS) is not None:
                raise ValueError(f"Cell {cell_ref} contains a formula. Refuse to overwrite formula cells with static values.")

            v_elem = c.find('.//ns:v', NS)
            if v_elem is None:
                v_elem = ET.SubElement(c, f'{{{ns_uri}}}v')
            v_elem.text = new_value

            # Update type attribute if numeric
            if new_value.replace('.','',1).replace('-','',1).replace('e','',1).replace('E','',1).isdigit() or \
               ('e' in new_value.lower() and new_value.replace('.','',1).replace('-','',1).replace('e','',1).replace('E','',1).isdigit()):
                c.set('t', 'n')
            return ET.tostring(root, encoding='unicode')
    raise ValueError(f"Cell {cell_ref} not found in sheet XML")

def main():
    parser = argparse.ArgumentParser(description='Update embedded Excel cell in Office document')
    parser.add_argument('host_file', help='Path to host PPTX/DOCX file')
    parser.add_argument('embed_path', help='Path within ZIP to embedded xlsx (e.g., ppt/embeddings/Microsoft_Excel_Worksheet.xlsx)')
    parser.add_argument('cell_ref', help='Cell reference (e.g., C4, F8)')
    parser.add_argument('new_value', help='New value to write')
    parser.add_argument('output_file', help='Output file path')
    parser.add_argument('--sheet', default='sheet1.xml', help='Target worksheet XML filename within xl/worksheets/ (default: sheet1.xml)')

    args = parser.parse_args()

    # If new_val looks like a float, ensure full precision via repr()
    new_val = args.new_value
    try:
        float_val = float(new_val)
        new_val = repr(float_val)
    except ValueError:
        pass  # Not a numeric value, use as-is

    with zipfile.ZipFile(args.host_file, 'r') as host_zip:
        xlsx_data = host_zip.read(args.embed_path)

    sheet_path = f'xl/worksheets/{args.sheet}'

    with zipfile.ZipFile(io.BytesIO(xlsx_data), 'r') as xlsx_zip:
        if sheet_path not in xlsx_zip.namelist():
            available = [n for n in xlsx_zip.namelist() if n.startswith('xl/worksheets/')]
            raise ValueError(f"{sheet_path} not found in embedded workbook. Available sheets: {available}")

        sheet_xml = xlsx_zip.read(sheet_path).decode('utf-8')
        updated_sheet = update_cell(sheet_xml, args.cell_ref, new_val)

        new_xlsx = io.BytesIO()
        with zipfile.ZipFile(new_xlsx, 'w', zipfile.ZIP_DEFLATED) as out_xlsx:
            for item in xlsx_zip.infolist():
                if item.filename == sheet_path:
                    out_xlsx.writestr(item, updated_sheet)
                else:
                    out_xlsx.writestr(item, xlsx_zip.read(item.filename))

    with zipfile.ZipFile(args.host_file, 'r') as host_zip:
        with zipfile.ZipFile(args.output_file, 'w', zipfile.ZIP_DEFLATED) as out_host:
            for item in host_zip.infolist():
                if item.filename == args.embed_path:
                    out_host.writestr(item, new_xlsx.getvalue())
                else:
                    out_host.writestr(item, host_zip.read(item.filename))
    print(f"Updated {args.cell_ref} to {new_val} in {args.embed_path} (sheet: {args.sheet}) -> {args.output_file}")

if __name__ == '__main__':
    main()
