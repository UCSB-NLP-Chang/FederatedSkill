#!/usr/bin/env python3
"""Safely repackages an extracted Office document directory into a new .pptx/.docx/.xlsx file.
Avoids zipfile duplicate-entry warnings and preserves exact internal paths.
Usage: python3 repack_office.py <extracted_dir> <output_file>
"""
import sys
import os
import zipfile

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 repack_office.py <extracted_dir> <output_file>")
        sys.exit(1)
    
    src_dir = sys.argv[1]
    out_file = sys.argv[2]
    
    if not os.path.isdir(src_dir):
        print(f"Error: {src_dir} is not a directory.")
        sys.exit(1)
        
    with zipfile.ZipFile(out_file, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(src_dir):
            for f in files:
                full_path = os.path.join(root, f)
                arcname = os.path.relpath(full_path, src_dir)
                z.write(full_path, arcname)
    print(f"Successfully repackaged to {out_file}")

if __name__ == "__main__":
    main()
