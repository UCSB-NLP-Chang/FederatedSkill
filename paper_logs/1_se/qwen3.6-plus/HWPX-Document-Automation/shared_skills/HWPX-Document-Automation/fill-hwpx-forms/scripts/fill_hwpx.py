#!/usr/bin/env python3
"""Fill HWPX template placeholders with JSON data and remove layout caches."""
import sys
import zipfile
import json
import re

def fill_hwpx(template_path, data_path, output_path):
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with zipfile.ZipFile(template_path, 'r') as zin:
        namelist = zin.namelist()
        section_files = [n for n in namelist if n.startswith('Contents/section') and n.endswith('.xml')]
        
        modified_xmls = {}
        for sec_file in section_files:
            xml_content = zin.read(sec_file).decode('utf-8')
            original = xml_content
            
            for key, value in data.items():
                placeholder = f"{{{{{key}}}}}"
                xml_content = xml_content.replace(placeholder, str(value))
            
            if xml_content != original:
                xml_content = re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', xml_content, flags=re.DOTALL)
                modified_xmls[sec_file] = xml_content

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name in namelist:
            if name in modified_xmls:
                zout.writestr(name, modified_xmls[name])
            else:
                zout.writestr(name, zin.read(name))

    with zipfile.ZipFile(output_path, 'r') as zout:
        for sec_file in section_files:
            content = zout.read(sec_file).decode('utf-8')
            if re.search(r'{{.*?}}', content):
                print(f"Warning: Unresolved placeholders remain in {sec_file}")
                return False
    print("HWPX filled successfully.")
    return True

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: fill_hwpx.py <template.hwpx> <data.json> <output.hwpx>")
        sys.exit(1)
    success = fill_hwpx(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if success else 1)
