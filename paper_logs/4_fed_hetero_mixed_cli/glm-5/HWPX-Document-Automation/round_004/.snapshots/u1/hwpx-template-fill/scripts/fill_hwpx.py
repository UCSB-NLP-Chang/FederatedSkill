#!/usr/bin/env python3
"""Fill {{...}} placeholders in an HWPX document using JSON data."""
import sys
import zipfile
import json
import re
import io

def fill_hwpx(template_path, json_path, output_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open(template_path, 'rb') as f:
        template_bytes = f.read()

    buf = io.BytesIO(template_bytes)
    with zipfile.ZipFile(buf, 'r') as zin:
        namelist = zin.namelist()
        infodict = {name: zin.getinfo(name) for name in namelist}
        filedata = {name: zin.read(name).decode('utf-8') for name in namelist}

    # Process ALL section XMLs (placeholders often span multiple sections)
    section_names = [n for n in namelist if n.startswith('Contents/section') and n.endswith('.xml')]
    if not section_names:
        raise ValueError("No section XML found in HWPX archive.")

    para_pattern = re.compile(r'(<hp:p\b[^>]*>.*?</hp:p>)', re.DOTALL)
    # Matches both <hp:linesegarray /> and <hp:linesegarray>...</hp:linesegarray>
    lineseg_pattern = re.compile(r'<hp:linesegarray\s*/?>|<hp:linesegarray>.*?</hp:linesegarray>', re.DOTALL)

    for section_name in section_names:
        xml = filedata[section_name]
        modified_ids = set()

        def replace_in_para(match):
            para = match.group(1)
            id_match = re.search(r'id="(\d+)"', para)
            para_id = int(id_match.group(1)) if id_match else None
            original = para
            for key, value in data.items():
                para = para.replace('{{' + key + '}}', str(value))
            if para != original and para_id is not None:
                modified_ids.add(para_id)
            return para

        xml = para_pattern.sub(replace_in_para, xml)

        def remove_lineseg(match):
            para = match.group(1)
            id_match = re.search(r'id="(\d+)"', para)
            if id_match and int(id_match.group(1)) in modified_ids:
                para = lineseg_pattern.sub('', para)
            return para

        xml = para_pattern.sub(remove_lineseg, xml)
        filedata[section_name] = xml

    # Verify across all sections
    remaining = []
    for s_name in section_names:
        remaining.extend(re.findall(r'\{\{[^}]+\}\}', filedata[s_name]))
    if remaining:
        print(f"WARNING: Remaining placeholders: {remaining}")
    else:
        print("All placeholders replaced successfully.")

    outbuf = io.BytesIO()
    with zipfile.ZipFile(outbuf, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for name in namelist:
            zout.writestr(infodict[name], filedata[name].encode('utf-8'))

    with open(output_path, 'wb') as f:
        f.write(outbuf.getvalue())
    print(f"Output written to {output_path}")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: fill_hwpx.py <template.hwpx> <data.json> <output.hwpx>")
        sys.exit(1)
    fill_hwpx(sys.argv[1], sys.argv[2], sys.argv[3])
