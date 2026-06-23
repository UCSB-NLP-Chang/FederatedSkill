#!/usr/bin/env python3
"""Robust Excel loader for inventory analysis tasks."""
import subprocess
import sys
from datetime import datetime, date, timedelta
import math

def ensure_openpyxl():
    """Install openpyxl if missing, handling externally-managed environments."""
    try:
        import openpyxl
        return openpyxl
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "-q", "--break-system-packages"])
        import openpyxl
        return openpyxl

def parse_date(val):
    """Normalize Excel cell values to date objects."""
    if isinstance(val, (datetime, date)):
        return val if isinstance(val, date) else val.date()
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return val

def extract_formula_multiplier(cell_val):
    """Extract numeric multiplier from formula strings like '=80*C2'."""
    if isinstance(cell_val, str) and cell_val.startswith("="):
        parts = cell_val.replace("=", "").replace("*", " ").split()
        for p in parts:
            try:
                return float(p)
            except ValueError:
                continue
    return None
