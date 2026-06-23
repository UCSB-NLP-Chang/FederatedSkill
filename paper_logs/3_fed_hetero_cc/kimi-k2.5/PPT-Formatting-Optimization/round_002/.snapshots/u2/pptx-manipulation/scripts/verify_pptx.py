#!/usr/bin/env python3
"""
Verify PowerPoint XML structure and formatting attributes.
Returns non-zero exit code if verification fails.
"""

import zipfile
import xml.etree.ElementTree as ET
import sys
import re

NSMAP = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'
}

class PPTXVerifier:
    def __init__(self, pptx_path):
        self.pptx_path = pptx_path
        self.zf = zipfile.ZipFile(pptx_path, 'r')
    
    def get_slide_xml(self, slide_num):
        """Get XML for a specific slide (1-indexed)."""
        slide_path = f'ppt/slides/slide{slide_num}.xml'
        return self.zf.read(slide_path)
    
    def verify_content_types(self):
        """Verify all slides are registered in [Content_Types].xml."""
        try:
            ct_xml = self.zf.read('[Content_Types].xml')
            root = ET.fromstring(ct_xml)
            
            slides = self.list_slides()
            missing = []
            
            for slide_num in slides:
                part_name = f'/ppt/slides/slide{slide_num}.xml'
                found = False
                for override in root.findall('.//{http://schemas.openxmlformats.org/package/2006/content-types}Override'):
                    if override.get('PartName') == part_name:
                        found = True
                        break
                if not found:
                    missing.append(slide_num)
            
            return missing
        except Exception as e:
            print(f"Error checking content types: {e}")
            return None
    
    def verify_text_formatting(self, slide_num, text_snippet, expected_font=None, 
                               expected_size=None, expected_color=None, expected_bold=None):
        """Verify formatting of text containing snippet."""
        xml = self.get_slide_xml(slide_num)
        root = ET.fromstring(xml)
        
        # Find text runs containing snippet
        for t_elem in root.findall('.//a:t', NSMAP):
            if t_elem.text and text_snippet in t_elem.text:
                # Navigate up to find a:r (run) element
                r_elem = None
                for elem in root.iter():
                    if elem.tag == '{http://schemas.openxmlformats.org/drawingml/2006/main}r':
                        for child in elem:
                            if child == t_elem:
                                r_elem = elem
                                break
                
                if r_elem is None:
                    continue
                
                rpr_elem = r_elem.find('a:rPr', NSMAP)
                if rpr_elem is None:
                    continue
                
                results = []
                
                if expected_font:
                    latin = rpr_elem.find('a:latin', NSMAP)
                    actual_font = latin.get('typeface') if latin is not None else None
                    results.append(('Font', actual_font, expected_font))
                
                if expected_size:
                    actual_size = rpr_elem.get('sz')
                    results.append(('Size', actual_size, str(expected_size)))
                
                if expected_bold is not None:
                    actual_bold = rpr_elem.get('b', '0') == '1'
                    results.append(('Bold', actual_bold, expected_bold))
                
                if expected_color:
                    srgb = rpr_elem.find('.//a:srgbClr', NSMAP)
                    actual_color = srgb.get('val') if srgb is not None else None
                    results.append(('Color', actual_color, expected_color))
                
                return results
        return None
    
    def verify_shape_position(self, slide_num, text_snippet):
        """Get position (x, y) and size (cx, cy) of shape containing text."""
        xml = self.get_slide_xml(slide_num).decode('utf-8')
        
        text_pattern = f'<a:t[^>]*>[^<]*{re.escape(text_snippet)}[^<]*</a:t>'
        if not re.search(text_pattern, xml):
            return None
        
        sp_pattern = r'<p:sp[^>]*>.*?<a:t[^>]*>[^<]*' + re.escape(text_snippet) + r'[^<]*</a:t>.*?</p:sp>'
        sp_match = re.search(sp_pattern, xml, re.DOTALL)
        
        if not sp_match:
            return None
        
        sp_xml = sp_match.group(0)
        
        off_match = re.search(r'<a:off x="(\d+)" y="(\d+)"', sp_xml)
        ext_match = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"', sp_xml)
        
        result = {}
        if off_match:
            result['x'] = int(off_match.group(1))
            result['y'] = int(off_match.group(2))
        if ext_match:
            result['cx'] = int(ext_match.group(1))
            result['cy'] = int(ext_match.group(2))
        
        return result
    
    def verify_alignment(self, slide_num, text_snippet):
        """Check paragraph alignment for text."""
        xml = self.get_slide_xml(slide_num).decode('utf-8')
        pattern = r'<a:p[^>]*>.*?<a:pPr[^>]*algn="([^"]+)".*?<a:t[^>]*>[^<]*' + re.escape(text_snippet)
        match = re.search(pattern, xml, re.DOTALL)
        if match:
            return match.group(1)
        return None
    
    def list_slides(self):
        """Return list of slide numbers in presentation."""
        slides = [n for n in self.zf.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
        return sorted([int(re.search(r'slide(\d+)\.xml', s).group(1)) for s in slides])
    
    def find_textboxes_by_position(self, slide_num, x=None, y=None, cx=None, cy=None):
        """Find all textboxes matching given position/size constraints."""
        xml = self.get_slide_xml(slide_num).decode('utf-8')
        
        results = []
        for sp_match in re.finditer(r'<p:sp[^>]*>.*?</p:sp>', xml, re.DOTALL):
            sp_xml = sp_match.group(0)
            
            if 'txBox' not in sp_xml and '<a:t>' not in sp_xml:
                continue
            
            off_match = re.search(r'<a:off x="(\d+)" y="(\d+)"', sp_xml)
            ext_match = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"', sp_xml)
            
            if not off_match:
                continue
            
            pos_x = int(off_match.group(1))
            pos_y = int(off_match.group(2))
            pos_cx = int(ext_match.group(1)) if ext_match else None
            pos_cy = int(ext_match.group(2)) if ext_match else None
            
            if x is not None and pos_x != x:
                continue
            if y is not None and pos_y != y:
                continue
            if cx is not None and pos_cx != cx:
                continue
            if cy is not None and pos_cy != cy:
                continue
            
            text_matches = re.findall(r'<a:t[^>]*>([^<]*)</a:t>', sp_xml)
            text_content = ' '.join(text_matches)
            
            results.append({
                'x': pos_x,
                'y': pos_y,
                'cx': pos_cx,
                'cy': pos_cy,
                'text': text_content
            })
        
        return results

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pptx_file>")
        sys.exit(1)
    
    verifier = PPTXVerifier(sys.argv[1])
    slides = verifier.list_slides()
    print(f"Slides found: {slides}")
    
    missing_ct = verifier.verify_content_types()
    if missing_ct:
        print(f"ERROR: Slides missing from [Content_Types].xml: {missing_ct}")
        sys.exit(1)
    elif missing_ct is not None:
        print("Content types: OK")
    
    if len(sys.argv) > 2:
        slide = int(sys.argv[2])
        text = sys.argv[3] if len(sys.argv) > 3 else "Sample"
        pos = verifier.verify_shape_position(slide, text)
        print(f"Position for '{text}': {pos}")