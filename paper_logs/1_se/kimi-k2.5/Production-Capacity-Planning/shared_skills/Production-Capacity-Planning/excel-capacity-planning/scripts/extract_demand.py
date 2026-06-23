#!/usr/bin/env python3
"""
Extract week/demand data from Excel with automatic structure detection.
Assumes: column 1 = week numbers, column 2 = demand values.
Handles header row automatically.
"""

import openpyxl
import sys
import json

def extract_demand(excel_path, sheet_name=None):
    """Extract (week, demand) pairs from Excel file."""
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    
    if sheet_name:
        ws = wb[sheet_name]
    else:
        ws = wb.active
    
    data = []
    header_skipped = False
    
    for row in ws.iter_rows(values_only=True):
        if not row or len(row) < 2:
            continue
        
        week, demand = row[0], row[1]
        
        # Skip header row (non-numeric week)
        if not header_skipped:
            try:
                int(week)
            except (ValueError, TypeError):
                header_skipped = True
                continue
            header_skipped = True
        
        try:
            week_num = int(week)
            demand_val = float(demand) if demand is not None else 0.0
            data.append((week_num, round(demand_val, 2)))
        except (ValueError, TypeError):
            continue
    
    return data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: extract_demand.py <excel_file> [sheet_name]", file=sys.stderr)
        sys.exit(1)
    
    path = sys.argv[1]
    sheet = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = extract_demand(path, sheet)
    print(json.dumps(result))
