#!/usr/bin/env python3
"""Fill {{placeholders}} in an HWPX template using a JSON file.
Removes hp:linesegarray from modified paragraphs to prevent rendering overlap.
Usage: python3 fill_hwpx.py <input.hwpx> <data.json> <output.hwpx>
"""
import sys
import zipfile
import json
import re

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 fill_hwpx.py <input.hwpx> <data.json> <output.hwpx>")
        sys.exit(1)

    input_path, json_path, output_path = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with zipfile.ZipFile(input_path, 'r') as zin:
        file_list = zin.namelist()
        # Target XML files usually contain the document text
        target_files = [f for f in file_list if f.endswith('.xml') and 'section' in f.lower()]
        if not target_files:
            target_files = [f for f in file_list if f.endswith('.xml')]

        modified_files = {}
        for xml_name in target_files:
            content = zin.read(xml_name).decode('utf-8')
            original = content
            for key, value in data.items():
                content = content.replace(f'{{{{{key}}}}}', str(value))

            if content != original:
                # Remove layout cache elements to prevent overlapping text
                content = re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', content, flags=re.DOTALL)
                modified_files[xml_name] = content

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name in file_list:
            if name in modified_files:
                zout.writestr(name, modified_files[name])
            else:
                zout.writestr(name, zin.read(name))

    print(f"Successfully created {output_path}")

if __name__ == '__main__':
    main()