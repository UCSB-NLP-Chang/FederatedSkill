#!/usr/bin/env python3
"""
Reusable utilities for PPTX XML manipulation.
Use when performing bulk text modifications, caption repositioning, or text width calculations.
"""

import zipfile
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional, Callable
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

# Standard namespaces
P_NS = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A_NS = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS = {'p': P_NS, 'a': A_NS, 'r': R_NS}


def register_standard_namespaces():
    """Register standard PPTX namespaces to avoid ns0, ns1 prefixes."""
    ET.register_namespace('', P_NS)
    ET.register_namespace('a', A_NS)
    ET.register_namespace('r', R_NS)


def safe_slide_path_match(name: str) -> Optional[int]:
    """
    Safely extract slide number from a namelist entry.
    Returns slide number (1-indexed) or None if not a slide XML path.

    Use this instead of `.split('slide')` which incorrectly matches `_rels/` paths.
    """
    m = re.match(r'^ppt/slides/slide(\d+)\.xml$', name)
    return int(m.group(1)) if m else None


def safe_pptx_modify(input_path: str, output_path: str,
                      modify_fn: Callable[[Dict[str, str], Dict[str, bytes]], Dict[str, str]]):
    """
    Safely read-modify-write a PPTX file, preventing the 'ZIP already closed' error.

    This encapsulates the critical pattern: read ALL data before closing input ZIP.

    Args:
        input_path: Path to input .pptx file
        output_path: Path to output .pptx file
        modify_fn: Function that takes (xml_dict, binary_dict) and returns modified xml_dict.
                   xml_dict maps XML file paths to decoded strings.
                   binary_dict maps non-XML file paths to raw bytes.

    Usage:
        def my_modifications(xmls, binaries):
            xmls['ppt/slides/slide1.xml'] = modified_xml
            return xmls

        safe_pptx_modify('input.pptx', 'output.pptx', my_modifications)
    """
    # READ PHASE: Read EVERYTHING before closing
    with zipfile.ZipFile(input_path, 'r') as z:
        namelist = z.namelist()

        xml_data = {}
        binary_data = {}

        for name in namelist:
            raw = z.read(name)
            if name.endswith('.xml'):
                xml_data[name] = raw.decode('utf-8')
            else:
                binary_data[name] = raw

    # MODIFY PHASE: Work on in-memory data
    modified_xml = modify_fn(xml_data, binary_data)

    # WRITE PHASE: Create new output ZIP
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as out:
        for name in namelist:
            if name in modified_xml:
                out.writestr(name, modified_xml[name])
            elif name in binary_data:
                out.writestr(name, binary_data[name])


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

    with zipfile.ZipFile(pptx_path, 'r') as z:
        slide_files = sorted([f for f in z.namelist() if safe_slide_path_match(f) is not None])

        for slide_file in slide_files:
            slide_num = safe_slide_path_match(slide_file)
            xml_content = z.read(slide_file).decode('utf-8')
            root = ET.fromstring(xml_content)

            texts = []
            for t_elem in root.findall('.//a:t', NS):
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
    slide_path = f'ppt/slides/slide{slide_num}.xml'

    with zipfile.ZipFile(pptx_path, 'r') as z:
        if slide_path not in z.namelist():
            return None

        xml_content = z.read(slide_path).decode('utf-8')
        root = ET.fromstring(xml_content)

        # Find all shapes
        for sp in root.findall('.//p:sp', NS):
            # Check text content
            texts = []
            for t in sp.findall('.//a:t', NS):
                if t.text:
                    texts.append(t.text)

            full_text = ''.join(texts)
            if target_text in full_text:
                # Extract shape info
                cNvPr = sp.find('.//p:cNvPr', NS)
                xfrm = sp.find('.//a:xfrm', NS)
                rPr = sp.find('.//a:rPr', NS)

                info = {
                    'text': full_text,
                    'shape_id': cNvPr.get('id') if cNvPr is not None else None,
                    'shape_name': cNvPr.get('name') if cNvPr is not None else None,
                }

                if xfrm is not None:
                    off = xfrm.find('a:off', NS)
                    ext = xfrm.find('a:ext', NS)
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
                    latin = rPr.find('a:latin', NS)
                    if latin is not None:
                        info['font'] = latin.get('typeface')

                return info

    return None


def replace_shape_by_text(slide_xml: str, target_text: str, new_shape_xml: str) -> str:
    """
    Replace a shape containing target_text with a new shape using DOM manipulation.

    This is the SAFE approach - avoids string replacement which breaks when
    ElementTree serializes with different namespace prefixes (e.g., </spTree> vs </p:spTree>).

    Args:
        slide_xml: The slide XML string
        target_text: Text content to match in existing shape
        new_shape_xml: XML string for the replacement shape

    Returns:
        Modified slide XML string
    """
    register_standard_namespaces()
    root = ET.fromstring(slide_xml)
    sp_tree = root.find('.//p:spTree', NS)

    if sp_tree is None:
        return slide_xml

    # Find and remove matching shape
    found = False
    for sp in list(sp_tree.findall('p:sp', NS)):
        texts = [t.text for t in sp.findall('.//a:t', NS) if t.text]
        if target_text in ''.join(texts):
            sp_tree.remove(sp)
            found = True
            break

    if not found:
        return slide_xml

    # Parse and append new shape
    new_sp = ET.fromstring(new_shape_xml)
    sp_tree.append(new_sp)

    return ET.tostring(root, encoding='unicode')


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
    # Register namespaces to preserve prefixes
    register_standard_namespaces()

    root = ET.fromstring(xml_content)
    modified = False

    # Find all text runs
    for t_elem in root.findall('.//a:t', NS):
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
                rPr = r.find('a:rPr', NS)
                if rPr is None:
                    rPr = ET.Element(f'{{{A_NS}}}rPr')
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
                    latin = rPr.find('a:latin', NS)
                    if latin is None:
                        latin = ET.SubElement(rPr, f'{{{A_NS}}}latin')
                    latin.set('typeface', font_name)

                # Update color
                if color_hex is not None:
                    solidFill = rPr.find('a:solidFill', NS)
                    if solidFill is None:
                        solidFill = ET.SubElement(rPr, f'{{{A_NS}}}solidFill')
                    else:
                        # Remove existing color elements
                        for child in list(solidFill):
                            solidFill.remove(child)

                    srgbClr = ET.SubElement(solidFill, f'{{{A_NS}}}srgbClr')
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
    print("  from pptx_helpers import safe_pptx_modify, extract_slide_text_mapping")
    print("  safe_pptx_modify('input.pptx', 'output.pptx', my_modify_fn)")
