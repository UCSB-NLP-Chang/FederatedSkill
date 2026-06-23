#!/usr/bin/env python3
"""Compare two pandas DataFrames and produce a structured diff."""

import pandas as pd
import json
from typing import List, Dict, Any, Optional


def diff_datasets(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    key_column: str,
    float_tolerance: float = 1e-6
) -> Dict[str, Any]:
    """
    Compare two DataFrames and return structured diff.
    
    Args:
        old_df: Baseline/older DataFrame
        new_df: Current/newer DataFrame
        key_column: Column name that uniquely identifies records
        float_tolerance: Tolerance for numeric comparisons
    
    Returns:
        Dict with 'removed_ids', 'added_ids', 'changed_records'
    """
    # Validate key column exists
    if key_column not in old_df.columns:
        raise ValueError(f"Key column '{key_column}' not in old dataset")
    if key_column not in new_df.columns:
        raise ValueError(f"Key column '{key_column}' not in new dataset")
    
    # Get key sets
    old_keys = set(old_df[key_column].astype(str))
    new_keys = set(new_df[key_column].astype(str))
    
    removed_ids = sorted(old_keys - new_keys)
    added_ids = sorted(new_keys - old_keys)
    common_keys = old_keys & new_keys
    
    # Detect field-level changes
    changed_records = []
    old_indexed = old_df.set_index(key_column)
    new_indexed = new_df.set_index(key_column)
    
    for key in sorted(common_keys):
        old_row = old_indexed.loc[str(key)]
        new_row = new_indexed.loc[str(key)]
        
        # Handle duplicate keys by taking first
        if isinstance(old_row, pd.DataFrame):
            old_row = old_row.iloc[0]
        if isinstance(new_row, pd.DataFrame):
            new_row = new_row.iloc[0]
        
        for col in old_df.columns:
            if col == key_column:
                continue
            
            old_val = old_row.get(col)
            new_val = new_row.get(col)
            
            # Compare values
            if pd.isna(old_val) and pd.isna(new_val):
                continue
            if pd.isna(old_val) or pd.isna(new_val):
                changed_records.append({
                    "id": str(key),
                    "field": col,
                    "old_value": None if pd.isna(old_val) else old_val,
                    "new_value": None if pd.isna(new_val) else new_val
                })
                continue
            
            # Numeric comparison with tolerance
            if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                if abs(old_val - new_val) > float_tolerance:
                    changed_records.append({
                        "id": str(key),
                        "field": col,
                        "old_value": old_val,
                        "new_value": new_val
                    })
            # String comparison
            elif str(old_val) != str(new_val):
                changed_records.append({
                    "id": str(key),
                    "field": col,
                    "old_value": old_val,
                    "new_value": new_val
                })
    
    return {
        "removed_ids": removed_ids,
        "added_ids": added_ids,
        "changed_records": changed_records
    }


def main():
    """Example usage."""
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: diff_datasets.py <old_file> <new_file> <key_column> [output.json]")
        print("  Supports .xlsx, .csv, .json files")
        sys.exit(1)
    
    old_file = sys.argv[1]
    new_file = sys.argv[2]
    key_col = sys.argv[3]
    output_file = sys.argv[4] if len(sys.argv) > 4 else None
    
    # Load files based on extension
    def load_file(path: str) -> pd.DataFrame:
        if path.endswith('.xlsx'):
            return pd.read_excel(path)
        elif path.endswith('.csv'):
            return pd.read_csv(path)
        elif path.endswith('.json'):
            return pd.read_json(path)
        else:
            raise ValueError(f"Unsupported file type: {path}")
    
    old_df = load_file(old_file)
    new_df = load_file(new_file)
    
    result = diff_datasets(old_df, new_df, key_col)
    
    output = json.dumps(result, indent=2)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(output)
        print(f"Diff written to {output_file}")
    else:
        print(output)


if __name__ == "__main__":
    main()
