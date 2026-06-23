#!/usr/bin/env python3
"""Roll up 13F holdings by CUSIP to find top institutional managers."""
import csv
import sys
import json
from collections import defaultdict

def rollup_issuer(infotable_path, coverpage_path, cusip, top_n=5):
    # Aggregate VALUE by ACCESSION_NUMBER for the given CUSIP
    acc_values = defaultdict(float)
    with open(infotable_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('CUSIP', '').strip() == cusip:
                val_str = row.get('VALUE', '0').strip()
                try:
                    val = float(val_str)
                except ValueError:
                    val = 0.0
                acc = row.get('ACCESSION_NUMBER', '').strip()
                if acc:
                    acc_values[acc] += val

    # Sort by value descending
    sorted_accs = sorted(acc_values.items(), key=lambda x: x[1], reverse=True)[:top_n]

    # Map accessions to manager names
    acc_to_manager = {}
    with open(coverpage_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            acc = row.get('ACCESSION_NUMBER', '').strip()
            name = row.get('FILINGMANAGER_NAME', '').strip()
            if acc:
                acc_to_manager[acc] = name

    top_managers = []
    top_accessions = []
    top_values = []
    for acc, val in sorted_accs:
        top_accessions.append(acc)
        top_managers.append(acc_to_manager.get(acc, "Unknown"))
        top_values.append(val)

    return {
        "cusip": cusip,
        "top_managers": top_managers,
        "top_accessions": top_accessions,
        "top_values": top_values
    }

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: rollup_issuer.py <infotable.tsv> <coverpage.tsv> <cusip> [top_n]", file=sys.stderr)
        sys.exit(1)
    infotable = sys.argv[1]
    coverpage = sys.argv[2]
    cusip = sys.argv[3]
    top_n = int(sys.argv[4]) if len(sys.argv) > 4 else 5
    result = rollup_issuer(infotable, coverpage, cusip, top_n)
    print(json.dumps(result, indent=2))