# Grouped Caption Cleanup Workflow

Complete guide for cleaning up floating captions that exist as grouped shapes with badges/labels.

## Typical Group Structure

```xml
<p:grpSp>
  <p:nvGrpSpPr>
    <p:cNvPr id="7" name="Caption Group 7"/>
  </p:nvGrpSpPr>
  <p:grpSpPr>
    <a:xfrm>
      <a:off x="685800" y="1320000"/>    <!-- Group position -->
      <a:ext cx="3657600" cy="620000"/>  <!-- Group size -->
    </a:xfrm>
  </p:grpSpPr>
  
  <!-- Badge/Label shape -->
  <p:sp>
    <p:nvSpPr>
      <p:cNvPr id="8" name="Badge 8"/>
    </p:nvSpPr>
    <p:txBody>
      <a:p><a:r><a:t>Route Name</a:t></a:r></a:p>
    </p:txBody>
  </p:sp>
  
  <!-- Caption text shape -->
  <p:sp>
    <p:nvSpPr>
      <p:cNvPr id="6" name="Caption Banner Text"/>
    </p:nvSpPr>
    <p:txBody>
      <a:p>
        <a:r><a:rPr/><a:t>Caption text here</a:t></a:r>
      </a:p>
    </p:txBody>
  </p:sp>
</p:grpSp>
```

## Finding Caption Groups

```python
NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
}

# Find by group name pattern
for grpSp in root.findall('.//p:grpSp', NS):
    cNvPr = grpSp.find('p:nvGrpSpPr/p:cNvPr', NS)
    if cNvPr is not None and 'Caption Group' in cNvPr.get('name', ''):
        yield grpSp
```

## Modifying Group Position and Size

```python
def reposition_group(grpSp, new_width, new_height, x, y, ns):
    """Reposition and resize a group shape."""
    xfrm = grpSp.find('p:grpSpPr/a:xfrm', ns)
    if xfrm is not None:
        off = xfrm.find('a:off', ns)
        ext = xfrm.find('a:ext', ns)
        if off is not None:
            off.set('x', str(x))
            off.set('y', str(y))
        if ext is not None:
            ext.set('cx', str(new_width))
            ext.set('cy', str(new_height))

# Bottom-center positioning
SLIDE_WIDTH = 12192000
SLIDE_HEIGHT = 6858000
new_width = 4000000
new_height = 600000
x = (SLIDE_WIDTH - new_width) // 2
y = SLIDE_HEIGHT - new_height - 200000  # 200000 EMU margin

reposition_group(grpSp, new_width, new_height, x, y, NS)
```

## Formatting Caption Text (Multi-Run Safe)

**CRITICAL**: Always format ALL `a:r` runs in the caption:

```python
def format_caption_text(grpSp, font_name, font_size_pt, color_hex, remove_bold=True, ns=None):
    """
    Format caption text across all runs.
    
    Args:
        grpSp: The group shape element
        font_name: Font family (e.g., 'Arial')
        font_size_pt: Font size in points (e.g., 16)
        color_hex: RGB color without # (e.g., '49607A')
        remove_bold: Whether to remove bold formatting
        ns: Namespace dict
    """
    # Find the caption text shape by name
    for sp in grpSp.findall('p:sp', ns):
        cNvPr = sp.find('p:nvSpPr/p:cNvPr', ns)
        if cNvPr is not None and 'Caption' in cNvPr.get('name', ''):
            # Update ALL runs in ALL paragraphs
            for p in sp.findall('.//a:p', ns):
                for r in p.findall('a:r', ns):
                    rPr = r.find('a:rPr', ns)
                    if rPr is None:
                        rPr = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}rPr')
                        r.insert(0, rPr)
                    
                    # Set font size (in hundredths of points)
                    rPr.set('sz', str(font_size_pt * 100))
                    
                    # Set/remove bold
                    if remove_bold and 'b' in rPr.attrib:
                        del rPr.attrib['b']
                    
                    # Set font
                    latin = rPr.find('a:latin', ns)
                    if latin is None:
                        latin = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/drawingml/2006/main}latin')
                    latin.set('typeface', font_name)
                    
                    # Set color
                    solidFill = rPr.find('a:solidFill', ns)
                    if solidFill is None:
                        solidFill = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill')
                    # Clear existing color
                    for child in list(solidFill):
                        solidFill.remove(child)
                    srgbClr = ET.SubElement(solidFill, '{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr')
                    srgbClr.set('val', color_hex.upper())
```

## Extracting Full Text Content

Join all runs to get the complete caption text:

```python
def get_full_text(grpSp, ns):
    """Extract full text from caption group, joining all runs."""
    texts = []
    for sp in grpSp.findall('p:sp', ns):
        cNvPr = sp.find('p:nvSpPr/p:cNvPr', ns)
        if cNvPr is not None and 'Caption' in cNvPr.get('name', ''):
            for t in sp.findall('.//a:t', ns):
                if t.text:
                    texts.append(t.text)
    return ''.join(texts)
```

## Complete Cleanup Script Template

```python
import zipfile
import xml.etree.ElementTree as ET

def cleanup_captions(input_path, output_path, slides_to_clean, font_name='Arial', 
                     font_size=16, color='49607A', new_width=4000000):
    """
    Clean up platform captions on specified slides.
    
    Args:
        input_path: Source PPTX file
        output_path: Destination PPTX file (must be different)
        slides_to_clean: List of slide numbers (1-indexed)
        font_name: Font family
        font_size: Font size in points
        color: RGB hex color (no #)
        new_width: New caption width in EMUs
    """
    NS = {
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
    }
    
    # Register namespaces
    ET.register_namespace('', 'http://schemas.openxmlformats.org/presentationml/2006/main')
    ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')
    ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
    
    # Calculate position for bottom-center
    slide_width = 12192000
    slide_height = 6858000
    new_height = 600000
    margin = 200000
    x = (slide_width - new_width) // 2
    y = slide_height - new_height - margin
    
    z = zipfile.ZipFile(input_path, 'r')
    namelist = z.namelist()
    
    # Collect all captions found (for Platform Log)
    all_captions = []
    
    # Process slides
    modified_slides = {}
    
    for slide_num in slides_to_clean:
        slide_path = f'ppt/slides/slide{slide_num}.xml'
        if slide_path not in namelist:
            continue
            
        xml_content = z.read(slide_path).decode('utf-8')
        root = ET.fromstring(xml_content)
        
        # Find and process caption groups
        for grpSp in root.findall('.//p:grpSp', NS):
            cNvPr = grpSp.find('p:nvGrpSpPr/p:cNvPr', NS)
            if cNvPr is not None and 'Caption Group' in cNvPr.get('name', ''):
                # Reposition group
                xfrm = grpSp.find('p:grpSpPr/a:xfrm', NS)
                if xfrm is not None:
                    off = xfrm.find('a:off', NS)
                    ext = xfrm.find('a:ext', NS)
                    if off is not None:
                        off.set('x', str(x))
                        off.set('y', str(y))
                    if ext is not None:
                        ext.set('cx', str(new_width))
                        ext.set('cy', str(new_height))
                
                # Format text and collect caption
                caption_text = ''
                for sp in grpSp.findall('p:sp', NS):
                    sp_name = sp.find('p:nvSpPr/p:cNvPr', NS)
                    name_attr = sp_name.get('name', '') if sp_name is not None else ''
                    
                    if 'Caption' in name_attr:
                        # Get and format all runs
                        texts = []
                        for p in sp.findall('.//a:p', NS):
                            for r in p.findall('a:r', NS):
                                t = r.find('a:t', NS)
                                if t is not None and t.text:
                                    texts.append(t.text)
                                
                                # Format the run
                                rPr = r.find('a:rPr', NS)
                                if rPr is None:
                                    rPr = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}rPr')
                                    r.insert(0, rPr)
                                
                                rPr.set('sz', str(font_size * 100))
                                rPr.attrib.pop('b', None)  # Remove bold
                                
                                # Set font
                                latin = rPr.find('a:latin', NS)
                                if latin is None:
                                    latin = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/drawingml/2006/main}latin')
                                latin.set('typeface', font_name)
                                
                                # Set color
                                solidFill = rPr.find('a:solidFill', NS)
                                if solidFill is None:
                                    solidFill = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill')
                                for child in list(solidFill):
                                    solidFill.remove(child)
                                srgbClr = ET.SubElement(solidFill, '{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr')
                                srgbClr.set('val', color.upper())
                        
                        caption_text = ''.join(texts)
                        if caption_text:
                            all_captions.append(caption_text)
        
        modified_slides[slide_path] = ET.tostring(root, encoding='unicode')
    
    # Write output
    output = zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED)
    for name in namelist:
        if name in modified_slides:
            output.writestr(name, modified_slides[name])
        else:
            output.writestr(name, z.read(name))
    
    output.close()
    z.close()
    
    # Return unique captions in order of first appearance
    seen = set()
    unique_captions = []
    for cap in all_captions:
        if cap not in seen:
            seen.add(cap)
            unique_captions.append(cap)
    
    return unique_captions
```

## Verification Checklist

After cleanup, verify:
- [ ] All target slides have been processed
- [ ] Group positions are at bottom center (y ~ 6,000,000)
- [ ] Group widths match target (e.g., 4,000,000 EMUs)
- [ ] All text runs have correct font, size, color
- [ ] Bold has been removed from all runs
- [ ] Badge shapes preserved with original formatting
- [ ] Full caption text is preserved (join all runs and compare)
