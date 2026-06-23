#!/usr/bin/env python3
"""
Cross-format tabular data diff tool.
Compares structured data between PDF, Excel, and CSV files.
Handles type normalization automatically (PDF returns strings, Excel returns native types).
"""

import sys
import json
import argparse
from pathlib import Path

def extract_data(filepath):
    """Extract tabular data from PDF, Excel, or CSV."""
    path = Path(filepath)
    suffix = path.suffix.lower()
    
    if suffix == '.pdf':
        try:
            import pdfplumber
        except ImportError:
            print("Error: pdfplumber not installed. Run: pip install pdfplumber --break-system-packages")
            sys.exit(1)
        
        with pdfplumber.open(filepath) as pdf:
            if not pdf.pages:
                raise ValueError(f"PDF has no pages: {filepath}")
            tables = pdf.pages[0].extract_tables()
            if not tables:
                raise ValueError(f"No tables found on first page of PDF: {filepath}")
            table = tables[0]
            headers = table[0]
            rows = table[1:]
            return [dict(zip(headers, row)) for row in rows]
    
    elif suffix in ['.xlsx', '.xls']:
        try:
            import pandas as pd
        except ImportError:
            print("Error: pandas not installed. Run: pip install pandas openpyxl --break-system-packages")
            sys.exit(1)
        
        df = pd.read_excel(filepath)
        return df.to_dict('records')
    
    elif suffix == '.csv':
        try:
            import pandas as pd
        except ImportError:
            print("Error: pandas not installed. Run: pip install pandas --break-system-packages")
            sys.exit(1)
        
        df = pd.read_csv(filepath)
        return df.to_dict('records')
    
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Supported: .pdf, .xlsx, .xls, .csv")

def normalize_value(val):
    """Convert value to native Python type for comparison and JSON serialization."""
    try:
        import pandas as pd
        import numpy as np
        
        if pd.isna(val):
            return None
        if isinstance(val, (np.integer, np.floating, np.bool_)):
            return val.item()
    except ImportError:
        pass
    
    if isinstance(val, str):
        # Strip whitespace first
        val = val.strip()
        # Try int first, then float
        try:
            return int(val)
        except ValueError:
            try:
                return float(val)
            except ValueError:
                return val
    return val

def normalize_record(record):
    """Normalize all values in a record."""
    return {k: normalize_value(v) for k, v in record.items()}

def convert_for_json(obj):
    """Recursively convert numpy/pandas types to Python native types for JSON output."""
    try:
        import pandas as pd
        import numpy as np
        
        if isinstance(obj, dict):
            return {k: convert_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_for_json(item) for item in obj]
        elif isinstance(obj, (np.integer, np.floating, np.bool_)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
    except ImportError:
        pass
    return obj

def diff_data(source_data, target_data, key_field):
    """Compare two datasets and return changes."""
    # Normalize keys to strings for consistent comparison
    source_map = {str(r.get(key_field, '')): normalize_record(r) for r in source_data if key_field in r}
    target_map = {str(r.get(key_field, '')): normalize_record(r) for r in target_data if key_field in r}
    
    source_keys = set(source_map.keys())
    target_keys = set(target_map.keys())
    
    retired = sorted(source_keys - target_keys)
    added = sorted(target_keys - source_keys)
    
    changed = []
    common_keys = source_keys & target_keys
    
    for key in sorted(common_keys):
        s_rec = source_map[key]
        t_rec = target_map[key]
        
        # Compare all fields present in source
        for field in s_rec:
            if field == key_field:
                continue  # Don't report ID field as changed
            if field not in t_rec:
                continue
            
            old_val = s_rec[field]
            new_val = t_rec[field]
            
            if old_val != new_val:
                changed.append({
                    "id": key,
                    "field": field,
                    "old_value": old_val,
                    "new_value": new_val
                })
    
    return {
        "retired_ids": retired,
        "added_ids": added,
        "changed_fields": changed
    }

def main():
    parser = argparse.ArgumentParser(
        description='Diff tabular data across formats (PDF, Excel, CSV). '
                    'Automatically normalizes types (handles PDF strings vs Excel numbers).'
    )
    parser.add_argument('source', help='Source/baseline file (PDF/Excel/CSV)')
    parser.add_argument('target', help='Target/current file (PDF/Excel/CSV)')
    parser.add_argument('--key', '-k', required=True, help='Primary key column name')
    parser.add_argument('--output', '-o', default='diff_report.json', help='Output JSON file path')
    
    args = parser.parse_args()
    
    print(f"Extracting source data from {args.source}...")
    try:
        source_data = extract_data(args.source)
        print(f"  Found {len(source_data)} records")
        if source_data:
            print(f"  Columns: {list(source_data[0].keys())}")
    except Exception as e:
        print(f"Error extracting source: {e}")
        sys.exit(1)
    
    print(f"Extracting target data from {args.target}...")
    try:
        target_data = extract_data(args.target)
        print(f"  Found {len(target_data)} records")
        if target_data:
            print(f"  Columns: {list(target_data[0].keys())}")
    except Exception as e:
        print(f"Error extracting target: {e}")
        sys.exit(1)
    
    print(f"Comparing on key '{args.key}'...")
    result = diff_data(source_data, target_data, args.key)
    
    print(f"  Retired: {len(result['retired_ids'])}")
    if result['retired_ids']:
        print(f"    {result['retired_ids']}")
    print(f"  Added: {len(result['added_ids'])}")
    if result['added_ids']:
        print(f"    {result['added_ids']}")
    print(f"  Changed fields: {len(result['changed_fields'])}")
    
    # Convert for JSON and write output
    result = convert_for_json(result)
    
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\nReport written to {args.output}")

if __name__ == '__main__':
    main()