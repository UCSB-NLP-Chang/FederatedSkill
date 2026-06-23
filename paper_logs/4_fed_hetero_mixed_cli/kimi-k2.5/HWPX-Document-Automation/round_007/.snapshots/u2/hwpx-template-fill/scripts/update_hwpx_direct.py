#!/usr/bin/env python3
"""Replace exact text strings in an HWPX document, handling <hp:run> splits and linesegarray removal."""
import sys
import zipfile
import json
import re
import io
import copy

def update_hwpx_direct(template_path, mapping_path, output_path):
    with open(mapping_path, 'r', encoding='utf-8') as f:
        mapping = json.load(f)  # {"old_text": "new_text", ...}

    with open(template_path, 'rb') as f:
        buf = io.BytesIO(f.read())
    with zipfile.ZipFile(buf, 'r') as zin:
        namelist = zin.namelist()
        infodict = {n: copy.copy(zin.getinfo(n)) for n in namelist}
        filedata = {n: zin.read(n).decode('utf-8') for n in namelist}

    sections = [n for n in namelist if n.startswith('Contents/section') and n.endswith('.xml')]
    para_pattern = re.compile(r'(<hp:p\b[^>]*>.*?</hp:p>)', re.DOTALL)
    lineseg_pattern = re.compile(r'<hp:linesegarray[^>]*/>|<hp:linesegarray>.*?</hp:linesegarray>', re.DOTALL)

    for sec in sections:
        xml = filedata[sec]
        modified_ids = set()

        def replace_in_para(match):
            para = match.group(1)
            id_match = re.search(r'id="(\d+)"', para)
            para_id = int(id_match.group(1)) if id_match else None
            original = para
            # Replace across runs safely by targeting <hp:t> content
            for old, new in mapping.items():
                para = re.sub(re.escape(old), new, para)
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
        filedata[sec] = xml

    # Repackage
    outbuf = io.BytesIO()
    with zipfile.ZipFile(outbuf, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for n in namelist:
            zout.writestr(infodict[n], filedata[n].encode('utf-8'))
    with open(output_path, 'wb') as f:
        f.write(outbuf.getvalue())
    print(f"Updated HWPX written to {output_path}")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: update_hwpx_direct.py <template.hwpx> <mapping.json> <output.hwpx>")
        sys.exit(1)
    update_hwpx_direct(sys.argv[1], sys.argv[2], sys.argv[3])