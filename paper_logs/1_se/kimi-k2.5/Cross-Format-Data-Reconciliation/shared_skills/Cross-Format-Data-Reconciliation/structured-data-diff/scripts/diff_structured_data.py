#!/usr/bin/env python3
"""
Compare two structured datasets and output retired IDs and field changes.

Usage:
    python3 diff_structured_data.py archive.json current.json output.json
    python3 diff_structured_data.py archive.json current.json output.json \
        --deleted-key deleted_medications --changed-key modified_medications

Input files: JSON arrays of objects with 'ID' field
Output: JSON with configurable keys for deleted and changed records
"""

import json
import sys
import argparse
from typing import List, Dict, Any


def load_data(path: str) -> List[Dict[str, Any]]:
    with open(path) as f:
        return json.load(f)


def to_id_map(data: List[Dict]) -> Dict[str, Dict]:
    """Convert list to dict keyed by 'ID', handling case variations."""
    result = {}
    for row in data:
        key = row.get('ID') or row.get('id')
        if key is None:
            raise ValueError(f"Row missing ID field: {row}")
        result[key] = row
    return result


def find_changes(archive: Dict[str, Dict], current: Dict[str, Dict]) -> tuple:
    archive_ids = set(archive.keys())
    current_ids = set(current.keys())
    
    retired = sorted(archive_ids - current_ids)
    
    changed = []
    common_ids = archive_ids & current_ids
    
    for id_ in sorted(common_ids):
        old_row = archive[id_]
        new_row = current[id_]
        
        all_fields = set(old_row.keys()) | set(new_row.keys())
        for field in sorted(all_fields):
            if field in ('ID', 'id'):
                continue
            old_val = old_row.get(field)
            new_val = new_row.get(field)
            if old_val != new_val:
                changed.append({
                    "id": id_,
                    "field": field,
                    "old_value": old_val,
                    "new_value": new_val
                })
    
    changed.sort(key=lambda x: (x["id"], x["field"]))
    return retired, changed


def main():
    parser = argparse.ArgumentParser(description='Compare structured datasets')
    parser.add_argument('archive', help='Archive JSON file path')
    parser.add_argument('current', help='Current JSON file path')
    parser.add_argument('output', help='Output JSON file path')
    parser.add_argument('--deleted-key', default='retired_service_ids',
                        help='Key name for deleted IDs in output (default: retired_service_ids)')
    parser.add_argument('--changed-key', default='changed_services',
                        help='Key name for changed records in output (default: changed_services)')
    
    args = parser.parse_args()
    
    archive_data = load_data(args.archive)
    current_data = load_data(args.current)
    
    archive_map = to_id_map(archive_data)
    current_map = to_id_map(current_data)
    
    retired, changed = find_changes(archive_map, current_map)
    
    result = {
        args.deleted_key: retired,
        args.changed_key: changed
    }
    
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Diff written to {args.output}")
    print(f"Deleted ({args.deleted_key}): {len(retired)}, Changed ({args.changed_key}): {len(changed)}")


if __name__ == "__main__":
    main()
