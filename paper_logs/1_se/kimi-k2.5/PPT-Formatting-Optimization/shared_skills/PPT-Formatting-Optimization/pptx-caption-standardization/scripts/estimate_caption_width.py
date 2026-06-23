#!/usr/bin/env python3
"""Calculate EMU width for single-line caption text."""

import sys

# Empirical EMUs per character for common fonts/sizes
# Based on testing with Arial at various sizes
CHAR_WIDTH_EMUS = {
    ('Arial', 12): 72000,
    ('Arial', 14): 90000,
    ('Arial', 16): 100000,
    ('Arial', 18): 115000,
    ('Calibri', 12): 68000,
    ('Calibri', 14): 85000,
    ('Calibri', 16): 95000,
    ('Lucida Grande', 12): 75000,
    ('Lucida Grande', 14): 92000,
}

def estimate_width(text, font='Arial', size_pt=14, safety_factor=1.15):
    """
    Estimate width in EMUs for single-line text caption.
    
    Args:
        text: The caption text
        font: Font family name
        size_pt: Font size in points
        safety_factor: Multiplier for safety margin (default 1.15 = 15% extra)
    
    Returns:
        int: Width in EMUs
    """
    key = (font, size_pt)
    base = CHAR_WIDTH_EMUS.get(key)
    
    if base is None:
        # Interpolate or use default
        # Arial 14 = 90000 is our baseline
        baseline = 90000
        scale = size_pt / 14
        base = int(baseline * scale)
    
    width = int(len(text) * base * safety_factor)
    
    # Minimum width for very short text
    return max(width, 300000)

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} 'Caption Text' [font] [size_pt]")
        print(f"Example: {sys.argv[0]} 'Camera 02 - Loading Dock' Arial 14")
        sys.exit(1)
    
    text = sys.argv[1]
    font = sys.argv[2] if len(sys.argv) > 2 else 'Arial'
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 14
    
    width = estimate_width(text, font, size)
    slide_width = 12192000
    x = (slide_width - width) // 2
    
    print(f"Text: '{text}' ({len(text)} chars)")
    print(f"Font: {font} {size}pt")
    print(f"Width: {width} EMUs ({width/914400:.2f} inches)")
    print(f"Position: x={x}, y=6000000 (bottom-center)")
    print(f"XML snippet:")
    print(f'  <a:off x="{x}" y="6000000"/>')
    print(f'  <a:ext cx="{width}" cy="360000"/>')

if __name__ == '__main__':
    main()
