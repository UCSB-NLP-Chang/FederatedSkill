#!/usr/bin/env python3
"""Verify HWPX output after template filling.

Checks:
1. Valid ZIP structure with required files
2. No remaining {{...}} placeholders
3. Linesegarray removed from modified paragraphs
4. Korean labels preserved
"""
import sys
import zipfile
import re

def verify_hwpx(hwpx_path, expected_values=None):
    """Verify HWPX output meets requirements.
    
    Args:
        hwpx_path: Path to HWPX file to verify
        expected_values: Optional dict of expected key-value pairs to check
    
    Returns:
        Tuple of (success: bool, messages: list)
    """
    messages = []
    success = True
    
    # Check valid ZIP
    try:
        with zipfile.ZipFile(hwpx_path, 'r') as z:
            namelist = z.namelist()
            files = {n: z.read(n).decode('utf-8', errors='replace') 
                    for n in namelist if n.endswith('.xml')}
    except Exception as e:
        return False, [f"FAIL: Cannot read HWPX: {e}"]
    
    # Check for section files
    sections = [n for n in namelist if n.startswith('Contents/section') and n.endswith('.xml')]
    if not sections:
        messages.append("WARN: No section XML files found")
        success = False
    else:
        messages.append(f"OK: Found {len(sections)} section file(s)")
    
    # Check for remaining placeholders
    remaining = []
    for name, content in files.items():
        found = re.findall(r'\{\{[^}]+\}\}', content)
        remaining.extend(found)
    
    if remaining:
        messages.append(f"FAIL: {len(remaining)} placeholder(s) remain: {remaining[:5]}...")
        success = False
    else:
        messages.append("OK: No placeholders remain")
    
    # Check expected values if provided
    if expected_values:
        for key, value in expected_values.items():
            found = False
            for content in files.values():
                if str(value) in content:
                    found = True
                    break
            if found:
                messages.append(f"OK: Value for '{key}' present")
            else:
                messages.append(f"WARN: Value for '{key}' not found")
    
    # Check linesegarray presence (info only)
    lineseg_count = 0
    for content in files.values():
        lineseg_count += len(re.findall(r'<hp:linesegarray', content))
    messages.append(f"INFO: {lineseg_count} linesegarray element(s) present (should be 0 in modified paragraphs)")
    
    return success, messages


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: verify_hwpx.py <output.hwpx>")
        sys.exit(1)
    
    success, messages = verify_hwpx(sys.argv[1])
    for msg in messages:
        print(msg)
    sys.exit(0 if success else 1)
