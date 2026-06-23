#!/usr/bin/env python3
"""
Reusable utilities for PPTX XML manipulation.
Use when performing bulk text modifications, caption repositioning, or text width calculations.
"""

import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional
from io import BytesIO

# Standard EMU conversions
EMU_PER_INCH = 914400
EMU_PER_CM = 360000
EMU_PER_PT = 12700
SLIDE_WIDTH = 12192000  # 13.33 inches
SLIDE_HEIGHT = 6858000  # 7.5 inches

# Font width estimates at 15pt Arial (in EMUs) - adjust proportionally for other sizes
CHAR_WIDTHS = {
    'narrow': 50000,   # i, l, I, j, ., ;, :, !, '
    'medium': 70000,   # f, t, s, r, -, (, ), [, ]
    'average': 85000,  # a, c, e, g, m, n, o, p, q, u, v, x, z
    'wide': 100000,    # A-Z, 0-9
    'extra_wide': 120000,  # M, Q, O, &, %, $, #, @, ~, +, =, <, >
    'space': 40000,
}

NARROW_CHARS = set('ilIj.,;:!\'')
MEDIUM_CHARS = set('ftsrv-()[]')
EXTRA_WIDE_CHARS = set('MQO&%$#@~+=<>')


def register_standard_namespaces():
    """Register standard PPTX namespaces to avoid ns0, ns1 prefixes."""
    ET.register_namespace('', 'http://schemas.openxmlformats.org/presentationml/2006/main')
    ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')
    ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')


def get_text_width_emu(text: str, font_size_pt: int, font_name: str = 'Arial') -> int:
    """
    Estimate text width in EMUs based on character composition.
    Use for calculating text box width (cx) to ensure single-line fit.
    
    Args:
        text: The text content
        font_size_pt: Font size in points (e.g., 17 for 17pt)
        font_name: Font family (default Arial metrics used)
    
    Returns:
        Width in EMUs
    """
    base_size = 15  # Reference size for width metrics
    scale = font_size_pt / base_size
    
    total = 0
    for char in text:
        if char in NARROW_CHARS:
            total += CHAR_WIDTHS['narrow']
        elif char in MEDIUM_CHARS:
            total += CHAR_WIDTHS['medium']
        elif char.isupper() or char.isdigit() or char in EXTRA_WIDE_CHARS:
            total += CHAR_WIDTHS['wide']
        elif char == ' ':
            total += CHAR_WIDTHS['space']
        else:
            total += CHAR_WIDTHS['average']
    
    # Add padding for left/right insets (0.1 inch each side)
    padding = 2 * int(0.1 * EMU_PER_INCH)
    return int(total * scale) + padding


def bottom_center_position(text_width: int, text_height: int, 
                          bottom_margin_inches: float = 0.5) -> Tuple[int, int]:
    """
    Calculate x, y coordinates for bottom-center positioning.
    
    Args:
        text_width: Width of text box in EMUs
        text_height: Height of text box in EMUs
        bottom_margin_inches: Distance from bottom of slide (default 0.5")
    
    Returns:
        (x, y) tuple in EMUs
    """
    x = (SLIDE_WIDTH - text_width) // 2
    y = SLIDE_HEIGHT - text_height - int(bottom_margin_inches * EMU_PER_INCH)
    return x, y


def extract_slide_text_mapping(pptx_path: str) -> Dict[int, List[str]]:
    """
    Extract all text content from each slide for analysis.
    Use to identify which slides contain captions or target text.
    
    Returns:
        Dict mapping slide number (1-indexed) to list of text strings
    """
    result = {}
    namespaces = {
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
    }
    
    with zipfile.ZipFile(pptx_path, 'r') as z:
        slide_files = sorted([f for f in z.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')])
        
        for slide_file in slide_files:
            slide_num = int(slide_file.split('slide')[1].split('.')[0])
            xml_content = z.read(slide_file).decode('utf-8')
            root = ET.fromstring(xml_content)
            
            texts = []
            for t_elem in root.findall('.//a:t', namespaces):
                if t_elem.text:
                    texts.append(t_elem.text)
            
            result[slide_num] = texts
    
    return result


def find_shape_by_text(pptx_path: str, slide_num: int, target_text: str) -> Optional[Dict]:
    """
    Find shape properties by searching for specific text content.
    Use when shape IDs or names are unknown/unstable.
    
    Returns:
        Dict with shape info or None if not found
    """
    namespaces = {
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
    }
    
    slide_path = f'ppt/slides/slide{slide_num}.xml'
    
    with zipfile.ZipFile(pptx_path, 'r') as z:
        if slide_path not in z.namelist():
            return None
        
        xml_content = z.read(slide_path).decode('utf-8')
        root = ET.fromstring(xml_content)
        
        # Find all shapes
        for sp in root.findall('.//p:sp', namespaces):
            # Check text content
            texts = []
            for t in sp.findall('.//a:t', namespaces):
                if t.text:
                    texts.append(t.text)
            
            full_text = ''.join(texts)
            if target_text in full_text:
                # Extract shape info
                cNvPr = sp.find('.//p:cNvPr', namespaces)
                xfrm = sp.find('.//a:xfrm', namespaces)
                rPr = sp.find('.//a:rPr', namespaces)
                
                info = {
                    'text': full_text,
                    'shape_id': cNvPr.get('id') if cNvPr is not None else None,
                    'shape_name': cNvPr.get('name') if cNvPr is not None else None,
                }
                
                if xfrm is not None:
                    off = xfrm.find('a:off', namespaces)
                    ext = xfrm.find('a:ext', namespaces)
                    if off is not None:
                        info['x'] = int(off.get('x', 0))
                        info['y'] = int(off.get('y', 0))
                    if ext is not None:
                        info['cx'] = int(ext.get('cx', 0))
                        info['cy'] = int(ext.get('cy', 0))
                
                if rPr is not None:
                    info['font_size'] = rPr.get('sz')
                    info['bold'] = rPr.get('b') == '1'
                    info['italic'] = rPr.get('i') == '1'
                    latin = rPr.find('a:latin', namespaces)
                    if latin is not None:
                        info['font'] = latin.get('typeface')
                
                return info
    
    return None


def modify_text_formatting(xml_content: str, target_text: str, 
                          font_name: Optional[str] = None,
                          font_size: Optional[int] = None,
                          color_hex: Optional[str] = None,
                          bold: Optional[bool] = None,
                          italic: Optional[bool] = None) -> str:
    """
    Modify text formatting for all runs matching target_text.
    Returns modified XML string.
    
    Args:
        xml_content: The XML content string
        target_text: Text content to match
        font_name: Font family (e.g., 'Calibri')
        font_size: Font size in points (e.g., 17 for 17pt, stored as 1700)
        color_hex: RGB color without # (e.g., '4A6A54')
        bold: True to set bold, False to remove, None to leave unchanged
        italic: True to set italic, False to remove, None to leave unchanged
    """
    namespaces = {
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
    }
    
    # Register namespaces to preserve prefixes
    register_standard_namespaces()
    
    root = ET.fromstring(xml_content)
    modified = False
    
    # Find all text runs
    for t_elem in root.findall('.//a:t', namespaces):
        if t_elem.text == target_text:
            # Get parent run
            r = t_elem.getparent() if hasattr(t_elem, 'getparent') else None
            if r is None:
                # Fallback for ElementTree without getparent()
                for parent in root.iter():
                    for child in parent:
                        if child == t_elem:
                            r = parent
                            break
            
            if r is not None and r.tag.endswith('}r'):
                # Get or create rPr
                rPr = r.find('a:rPr', namespaces)
                if rPr is None:
                    rPr = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}rPr')
                    r.insert(0, rPr)
                
                # Update attributes
                if font_size is not None:
                    rPr.set('sz', str(font_size * 100))  # Convert pt to hundredths
                
                if bold is not None:
                    if bold:
                        rPr.set('b', '1')
                    elif 'b' in rPr.attrib:
                        del rPr.attrib['b']
                
                if italic is not None:
                    if italic:
                        rPr.set('i', '1')
                    elif 'i' in rPr.attrib:
                        del rPr.attrib['i']
                
                # Update font
                if font_name is not None:
                    latin = rPr.find('a:latin', namespaces)
                    if latin is None:
                        latin = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/drawingml/2006/main}latin')
                    latin.set('typeface', font_name)
                
                # Update color
                if color_hex is not None:
                    solidFill = rPr.find('a:solidFill', namespaces)
                    if solidFill is None:
                        solidFill = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill')
                    else:
                        # Remove existing color elements
                        for child in list(solidFill):
                            solidFill.remove(child)
                    
                    srgbClr = ET.SubElement(solidFill, '{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr')
                    srgbClr.set('val', color_hex.upper())
                
                modified = True
    
    if modified:
        return ET.tostring(root, encoding='unicode')
    return xml_content


def validate_slide_modification(pptx_path: str, slide_num: int, expected_texts: List[str]) -> bool:
    """
    Validate that a slide contains all expected text content.
    Use as mandatory verification step after modifications.
    
    Returns:
        True if all expected texts are found
    """
    mapping = extract_slide_text_mapping(pptx_path)
    slide_texts = mapping.get(slide_num, [])
    
    for expected in expected_texts:
        found = False
        for actual in slide_texts:
            if expected in actual:
                found = True
                break
        if not found:
            print(f"Validation failed: Expected '{expected}' not found in slide {slide_num}")
            return False
    
    return True


if __name__ == '__main__':
    print("PPTX Helper Utilities")
    print("Import this module to use helper functions")
    print()
    print("Example usage:")
    print("  from pptx_helpers import extract_slide_text_mapping, get_text_width_emu")
    print("  texts = extract_slide_text_mapping('file.pptx')")
    print("  width = get_text_width_emu('Sample Text', 17)")
