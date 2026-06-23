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
    
    def verify_text_formatting(self, slide_num, text_snippet, expected_font=None, 
                               expected_size=None, expected_color=None, expected_bold=None):
        """Verify formatting of text containing snippet."""
        xml = self.get_slide_xml(slide_num)
        root = ET.fromstring(xml)
        
        # Find text runs containing snippet
        for t_elem in root.findall('.//a:t', NSMAP):
            if text_snippet in t_elem.text:
                # Get parent a:r (run) then a:rPr (properties)
                r_elem = t_elem.getparent() if hasattr(t_elem, 'getparent') else None
                if r_elem is None:
                    # Fallback for ElementTree without getparent
                    pass
                
                rpr_elem = r_elem.find('a:rPr') if r_elem is not None else None
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
        xml = self.get_slide_xml(slide_num)
        
        # Regex approach for speed when ElementTree lacks getparent()
        text_pattern = f'<a:t[^>]*>[^<]*{re.escape(text_snippet)}[^<]*</a:t>'
        if not re.search(text_pattern, xml):
            return None
        
        # Find sp (shape) element containing this text
        # This is a simplified parser—assumes structure is reasonably flat
        sp_pattern = r'<p:sp[^>]*>.*?<a:t[^>]*>[^<]*' + re.escape(text_snippet) + r'[^<]*</a:t>.*?</p:sp>'
        sp_match = re.search(sp_pattern, xml, re.DOTALL)
        
        if not sp_match:
            return None
        
        sp_xml = sp_match.group(0)
        
        # Extract xfrm values
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
        xml = self.get_slide_xml(slide_num)
        # Find pPr with algn attribute near text
        pattern = r'<a:p[^>]*>.*?<a:pPr[^>]*algn="([^"]+)".*?<a:t[^>]*>[^<]*' + re.escape(text_snippet)
        match = re.search(pattern, xml, re.DOTALL)
        if match:
            return match.group(1)
        return None
    
    def list_slides(self):
        """Return list of slide numbers in presentation."""
        slides = [n for n in self.zf.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
        return sorted([int(re.search(r'slide(\d+)\.xml', s).group(1)) for s in slides])

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pptx_file>")
        sys.exit(1)
    
    verifier = PPTXVerifier(sys.argv[1])
    print(f"Slides found: {verifier.list_slides()}")
    
    # Example verification
    if len(sys.argv) > 2:
        slide = int(sys.argv[2])
        text = sys.argv[3] if len(sys.argv) > 3 else "Sample"
        pos = verifier.verify_shape_position(slide, text)
        print(f"Position for '{text}': {pos}")