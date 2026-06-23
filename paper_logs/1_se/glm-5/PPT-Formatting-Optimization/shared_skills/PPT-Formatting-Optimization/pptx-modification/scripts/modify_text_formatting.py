#!/usr/bin/env python3
"""Example: Modify text formatting in PPTX text boxes."""

import xml.etree.ElementTree as ET
import zipfile
import os
import shutil

# Standard Office Open XML namespaces
NS = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}

def register_namespaces():
    """Register namespaces for XML output. Avoid reserved prefixes."""
    for prefix, uri in NS.items():
        if prefix not in ('xml',):  # 'xml' is reserved
            ET.register_namespace(prefix, uri)

def local_name(tag):
    """Extract local name from namespaced tag."""
    return tag.split('}')[-1] if '}' in tag else tag

def find_text_boxes(root):
    """Find all text box shapes in a slide."""
    text_boxes = []
    for sp in root.iter():
        if local_name(sp.tag) == 'sp':
            for child in sp.iter():
                if local_name(child.tag) == 'cNvSpPr':
                    if child.get('txBox') == '1':
                        text_boxes.append(sp)
                        break
    return text_boxes

def get_text_content(sp):
    """Get text content from a shape."""
    texts = []
    for elem in sp.iter():
        if local_name(elem.tag) == 't' and elem.text:
            texts.append(elem.text)
    return ' '.join(texts)

def modify_text_formatting(sp, font_name='Arial', font_size=1500, color_hex='6F6C64', 
                            bold=False, italic=False, center=True):
    """Modify text formatting in a text box.
    
    Args:
        sp: Shape element (text box)
        font_name: Font family name
        font_size: Font size in hundredths of points (1500 = 15pt)
        color_hex: RGB color without # (e.g., '6F6C64')
        bold: Whether text should be bold
        italic: Whether text should be italic
        center: Whether to center-align text
    """
    a_ns = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
    
    # Find all text runs
    for r in sp.iter():
        if local_name(r.tag) == 'r':
            # Get or create rPr
            rPr = None
            for child in r:
                if local_name(child.tag) == 'rPr':
                    rPr = child
                    break
            
            if rPr is None:
                rPr = ET.Element(f'{a_ns}rPr')
                r.insert(0, rPr)
            
            # Set font size
            rPr.set('sz', str(font_size))
            
            # Set bold/italic
            if bold:
                rPr.set('b', '1')
            elif 'b' in rPr.attrib:
                del rPr.attrib['b']
            
            if italic:
                rPr.set('i', '1')
            elif 'i' in rPr.attrib:
                del rPr.attrib['i']
            
            # Set font color
            solidFill = None
            for child in rPr:
                if local_name(child.tag) == 'solidFill':
                    solidFill = child
                    break
            
            if solidFill is None:
                solidFill = ET.SubElement(rPr, f'{a_ns}solidFill')
            
            # Clear existing color and set new
            for child in list(solidFill):
                solidFill.remove(child)
            srgbClr = ET.SubElement(solidFill, f'{a_ns}srgbClr')
            srgbClr.set('val', color_hex)
            
            # Set font typeface
            for typeface_tag in ['latin', 'ea', 'cs']:
                tf = None
                for child in rPr:
                    if local_name(child.tag) == typeface_tag:
                        tf = child
                        break
                if tf is None:
                    tf = ET.SubElement(rPr, f'{a_ns}{typeface_tag}')
                tf.set('typeface', font_name)
    
    # Set alignment if centering
    if center:
        for pPr in sp.iter():
            if local_name(pPr.tag) == 'pPr':
                pPr.set('algn', 'ctr')

def modify_slide_captions(slide_path, caption_text, **formatting_kwargs):
    """Modify caption text boxes in a slide.
    
    Args:
        slide_path: Path to slide XML file
        caption_text: Expected caption text to identify the text box
        **formatting_kwargs: Formatting options for modify_text_formatting
    
    Returns:
        bool: True if a caption was modified
    """
    tree = ET.parse(slide_path)
    root = tree.getroot()
    
    modified = False
    for tb in find_text_boxes(root):
        text = get_text_content(tb)
        if caption_text in text or text.strip() == caption_text:
            modify_text_formatting(tb, **formatting_kwargs)
            modified = True
    
    if modified:
        tree.write(slide_path, encoding='UTF-8', xml_declaration=True)
    
    return modified

def main():
    """Example usage."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python modify_text_formatting.py <input.pptx> <output.pptx>")
        return
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    register_namespaces()
    
    # Extract PPTX
    extract_dir = 'pptx_temp'
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    zipfile.ZipFile(input_path, 'r').extractall(extract_dir)
    
    # Modify slides
    slides_dir = os.path.join(extract_dir, 'ppt', 'slides')
    for filename in os.listdir(slides_dir):
        if filename.endswith('.xml') and filename.startswith('slide'):
            slide_path = os.path.join(slides_dir, filename)
            # Example: modify any text box
            # modify_slide_captions(slide_path, "Caption Text", font_size=1500)
            pass
    
    # Repackage
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                path = os.path.join(root, f)
                arcname = os.path.relpath(path, extract_dir)
                zf.write(path, arcname)
    
    shutil.rmtree(extract_dir)
    print(f"Created: {output_path}")

if __name__ == '__main__':
    main()
