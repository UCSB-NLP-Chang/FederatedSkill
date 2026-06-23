#!/usr/bin/env python3
"""Inspect CSV headers and first row to verify column-to-field mapping before applying overrides."""
import sys
import csv

def inspect(path):
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        print("=== CSV Headers ===")
        print(reader.fieldnames)
        print("\n=== First Row (as dict) ===")
        for i, row in enumerate(reader):
            if i == 0:
                for k, v in row.items():
                    print(f"  {k!r}: {v!r}")
            break
        else:
            print("(empty file)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: inspect_csv_mapping.py <csv_path>")
        sys.exit(1)
    inspect(sys.argv[1])
