#!/usr/bin/env python3
"""Utility functions for safe Excel data processing."""

def safe_int(val):
    """Convert Excel cell value to int, handling None, empty strings, and floats."""
    if val is None or str(val).strip() == '':
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0

def safe_float(val):
    """Convert Excel cell value to float, handling None and empty strings."""
    if val is None or str(val).strip() == '':
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
