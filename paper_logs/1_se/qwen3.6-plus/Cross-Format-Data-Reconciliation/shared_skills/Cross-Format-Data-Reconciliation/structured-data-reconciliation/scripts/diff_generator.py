#!/usr/bin/env python3
import argparse
import json
import sys

def load_data(path):
    with open(path) as f:
        return json.load(f)

def compute_diff(old_data, new_data, key_field):
    old_map = {item[key_field]: item for item in old_data}
    new_map = {item[key_field]: item for item in new_data}
    
    retired = [k for k in old_map if k not in new_map]
    added = [k for k in new_map if k not in old_map]
    
    changed = []
    common_keys = set(old_map.keys()) & set(new_map.keys())
    for k in sorted(common_keys):
        old_item = old_map[k]
        new_item = new_map[k]
        all_fields = sorted(set(old_item.keys()) | set(new_item.keys()))
        for field in all_fields:
            old_val = old_item.get(field)
            new_val = new_item.get(field)
            if old_val != new_val:
                changed.append({
                    "id": k,
                    "field": field,
                    "old_value": old_val,
                    "new_value": new_val
                })
                
    return {
        "retired_service_ids": retired,
        "added_service_ids": added,
        "changed_services": changed
    }

def main():
    parser = argparse.ArgumentParser(description="Generate structured diff between two JSON datasets")
    parser.add_argument("--old", required=True, help="Path to old dataset JSON")
    parser.add_argument("--new", required=True, help="Path to new dataset JSON")
    parser.add_argument("--key", required=True, help="Unique identifier field name")
    parser.add_argument("--output", required=True, help="Output diff JSON path")
    args = parser.parse_args()
    
    old = load_data(args.old)
    new = load_data(args.new)
    diff = compute_diff(old, new, args.key)
    
    with open(args.output, "w") as f:
        json.dump(diff, f, indent=2)
    print(f"Diff written to {args.output}")

if __name__ == "__main__":
    main()
