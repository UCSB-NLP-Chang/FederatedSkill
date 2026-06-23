#!/usr/bin/env python3
"""Update a cell value in an embedded Excel workbook inside a PPTX/DOCX file.
Usage: python update_embedded_xlsx.py <host_file> <embed_path> <cell_ref> <new_value> <output_file>
Example: python update_embedded_xlsx.py input.pptx ppt/embeddings/Microsoft_Excel_Worksheet.xlsx C4 1.1590 output.pptx
"""
import sys
import zipfile
import io
import xml.etree.ElementTree as ET

NS = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def update_cell(sheet_xml: str, cell_ref: str, new_value: str) -> str:
    root = ET.fromstring(sheet_xml)
    for c in root.findall('.//ns:c', NS):
        if c.get('r') == cell_ref:
            for child in list(c):
                c.remove(child)
            v = ET.SubElement(c, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
            v.text = new_value
            if new_value.replace('.','',1).replace('-','',1).isdigit():
                c.set('t', 'n')
            return ET.tostring(root, encoding='unicode')
    raise ValueError(f"Cell {cell_ref} not found in sheet XML")

def main():
    if len(sys.argv) != 6:
        print(__doc__)
        sys.exit(1)
    host_path, embed_path, cell_ref, new_val, out_path = sys.argv[1:]

    with zipfile.ZipFile(host_path, 'r') as host_zip:
        xlsx_data = host_zip.read(embed_path)
        
    with zipfile.ZipFile(io.BytesIO(xlsx_data), 'r') as xlsx_zip:
        sheet_xml = xlsx_zip.read('xl/worksheets/sheet1.xml').decode('utf-8')
        updated_sheet = update_cell(sheet_xml, cell_ref, new_val)
        
        new_xlsx = io.BytesIO()
        with zipfile.ZipFile(new_xlsx, 'w', zipfile.ZIP_DEFLATED) as out_xlsx:
            for item in xlsx_zip.infolist():
                if item.filename == 'xl/worksheets/sheet1.xml':
                    out_xlsx.writestr(item, updated_sheet)
                else:
                    out_xlsx.writestr(item, xlsx_zip.read(item.filename))
                    
    with zipfile.ZipFile(host_path, 'r') as host_zip:
        with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as out_host:
            for item in host_zip.infolist():
                if item.filename == embed_path:
                    out_host.writestr(item, new_xlsx.getvalue())
                else:
                    out_host.writestr(item, host_zip.read(item.filename))
    print(f"Updated {cell_ref} to {new_val} in {embed_path} -> {out_path}")

if __name__ == '__main__':
    main()
