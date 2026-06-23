#!/usr/bin/env python3
"""Compute structured diff between two lists of dictionaries.
Usage: python compute_diff.py old.json new.json [--key ID]
Outputs JSON to stdout.
"""
import json
import sys
import argparse

def normalize(val):
    """Normalize for comparison: strip strings, convert numbers to float."""
    if isinstance(val, str):
        val = val.strip()
        try:
            return float(val)
        except ValueError:
            return val
    return val

def format_output(val):
    """Format for output: convert float whole numbers to int."""
    if isinstance(val, float) and val.is_integer():
        return int(val)
    return val

def main():
    parser = argparse.ArgumentParser(description="Compute tabular diff")
    parser.add_argument("old_file", help="Path to old dataset JSON")
    parser.add_argument("new_file", help="Path to new dataset JSON")
    parser.add_argument("--key", default="ID", help="Primary key column name")
    args = parser.parse_args()

    with open(args.old_file) as f:
        old_data = json.load(f)
    with open(args.new_file) as f:
        new_data = json.load(f)

    old_map = {str(row.get(args.key)): row for row in old_data}
    new_map = {str(row.get(args.key)): row for row in new_data}

    old_keys = set(old_map.keys())
    new_keys = set(new_map.keys())

    removed = sorted(old_keys - new_keys)
    added = sorted(new_keys - old_keys)
    common = old_keys & new_keys

    changed = []
    for k in sorted(common):
        old_row = old_map[k]
        new_row = new_map[k]
        all_keys = set(old_row.keys()) | set(new_row.keys())
        for field in sorted(all_keys):
            old_val = normalize(old_row.get(field))
            new_val = normalize(new_row.get(field))
            if old_val != new_val:
                changed.append({
                    "id": k,
                    "field": field,
                    "old_value": format_output(old_val),
                    "new_value": format_output(new_val)
                })

    result = {
        "removed_ids": removed,
        "added_ids": added,
        "changed_records": changed
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
