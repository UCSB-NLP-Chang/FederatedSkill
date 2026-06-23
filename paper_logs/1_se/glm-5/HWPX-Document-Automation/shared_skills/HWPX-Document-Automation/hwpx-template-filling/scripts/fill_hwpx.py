#!/usr/bin/env python3
"""Fill HWPX template placeholders with values from JSON."""

import json
import zipfile
import re
import os
import sys

def fill_hwpx(template_path: str, data: dict, output_path: str) -> None:
    """
    Replace {{key}} placeholders in HWPX template with values from data dict.
    Removes linesegarray from modified paragraphs to prevent rendering issues.
    """
    temp_dir = "/tmp/hwpx_work"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Extract template
    with zipfile.ZipFile(template_path, 'r') as zf:
        zf.extractall(temp_dir)
    
    # Find and process section files
    sections_dir = os.path.join(temp_dir, "Contents")
    for filename in os.listdir(sections_dir):
        if filename.endswith(".xml") and filename.startswith("section"):
            section_path = os.path.join(sections_dir, filename)
            with open(section_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Track which paragraphs are modified
            modified_paragraphs = set()
            
            def replace_in_paragraph(match):
                paragraph = match.group(0)
                original = paragraph
                for key, value in data.items():
                    placeholder = f"{{{{{key}}}}}"
                    if placeholder in paragraph:
                        paragraph = paragraph.replace(placeholder, str(value))
                        if paragraph != original:
                            # Generate a simple ID from the paragraph
                            p_id_match = re.search(r'id="(\d+)"', paragraph)
                            if p_id_match:
                                modified_paragraphs.add(p_id_match.group(1))
                return paragraph
            
            # Replace placeholders paragraph by paragraph
            content = re.sub(
                r'<hp:p[^>]*>.*?</hp:p>',
                replace_in_paragraph,
                content,
                flags=re.DOTALL
            )
            
            # Remove linesegarray from modified paragraphs
            def clean_linesegarray(match):
                paragraph = match.group(0)
                p_id_match = re.search(r'id="(\d+)"', paragraph)
                if p_id_match and p_id_match.group(1) in modified_paragraphs:
                    return re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', paragraph, flags=re.DOTALL)
                return paragraph
            
            content = re.sub(
                r'<hp:p[^>]*>.*?</hp:p>',
                clean_linesegarray,
                content,
                flags=re.DOTALL
            )
            
            with open(section_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    # Repack as HWPX
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, temp_dir)
                zf.write(file_path, arc_name)
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: fill_hwpx.py <template.hwpx> <data.json> <output.hwpx>")
        sys.exit(1)
    
    template_path = sys.argv[1]
    data_path = sys.argv[2]
    output_path = sys.argv[3]
    
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fill_hwpx(template_path, data, output_path)
    print(f"Created: {output_path}")
