#!/usr/bin/env python3
"""
Flatten nested clinical JSON panels to CSV for harmonization.
Usage: python3 json_to_csv.py input.json output.csv [--status final] [--ref-csv columns.csv]
"""
import json
import csv
import sys
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("output_csv")
    parser.add_argument("--status", default="final")
    parser.add_argument("--ref-csv", help="CSV file to define column order")
    args = parser.parse_args()

    with open(args.input_json) as f:
        data = json.load(f)

    panels = data.get("panels", [])
    rows = []
    for p in panels:
        if args.status and p.get("status") != args.status:
            continue
        flat = {"sample_id": p.get("sample_id")}
        for category, metrics in p.get("measurements", {}).items():
            flat.update(metrics)
        rows.append(flat)

    if not rows:
        print("No rows found.")
        return

    # Determine column order
    if args.ref_csv:
        with open(args.ref_csv) as f:
            reader = csv.DictReader(f)
            headers = [r["Key"] for r in reader]
    else:
        headers = list(rows[0].keys())

    # Ensure sample_id is first if present
    if "sample_id" in headers:
        headers.remove("sample_id")
        headers.insert(0, "sample_id")

    with open(args.output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"Wrote {len(rows)} rows to {args.output_csv}")

if __name__ == "__main__":
    main()
