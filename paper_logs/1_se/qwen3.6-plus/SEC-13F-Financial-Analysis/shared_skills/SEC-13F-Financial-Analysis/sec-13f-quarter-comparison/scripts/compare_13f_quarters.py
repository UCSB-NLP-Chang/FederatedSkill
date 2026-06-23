#!/usr/bin/env python3
"""Compare SEC 13F holdings across two quarters for a specific manager."""
import csv
import json
import re
import sys
from collections import defaultdict

def normalize_name(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r'[^\w\s]', '', n)
    for suffix in ['llc', 'inc', 'lp', 'ltd', 'co', 'corp', 'llp', 'l p', 'l l c']:
        n = re.sub(rf'\b{suffix}\b', '', n).strip()
    return n

def find_accession(coverpage_path: str, query: str) -> str:
    target = normalize_name(query)
    with open(coverpage_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            mgr = row.get('FILINGMANAGER_NAME') or row.get('MANAGER_NAME', '')
            if normalize_name(mgr) == target:
                return row.get('ACCESSION_NUMBER')
    return None

def aggregate_holdings(infotable_path: str, accession: str) -> dict:
    holdings = defaultdict(float)
    if not accession:
        return dict(holdings)
    with open(infotable_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        cusip_col = 'CUSIP'
        value_col = 'VALUEUSD' if 'VALUEUSD' in reader.fieldnames else 'VALUE'
        for row in reader:
            if row.get('ACCESSION_NUMBER') == accession:
                cusip = row.get(cusip_col, '').strip()
                if cusip:
                    holdings[cusip] += float(row.get(value_col, 0))
    return dict(holdings)

def compare_quarters(baseline_dir: str, current_dir: str, query: str):
    bl_acc = find_accession(f"{baseline_dir}/COVERPAGE.tsv", query)
    cur_acc = find_accession(f"{current_dir}/COVERPAGE.tsv", query)
    
    # Handle missing quarters gracefully: treat as empty holdings
    bl_holdings = aggregate_holdings(f"{baseline_dir}/INFOTABLE.tsv", bl_acc)
    cur_holdings = aggregate_holdings(f"{current_dir}/INFOTABLE.tsv", cur_acc)

    all_cusips = set(bl_holdings.keys()) | set(cur_holdings.keys())
    deltas = []
    for cusip in all_cusips:
        v_bl = bl_holdings.get(cusip, 0.0)
        v_cur = cur_holdings.get(cusip, 0.0)
        delta = v_cur - v_bl
        deltas.append({"cusip": cusip, "baseline_value": v_bl, "current_value": v_cur, "delta": delta})

    deltas.sort(key=lambda x: x['delta'], reverse=True)
    
    increased = [d['cusip'] for d in deltas if d['delta'] > 0]
    decreased = [d['cusip'] for d in deltas if d['delta'] < 0]
    new_pos = [d['cusip'] for d in deltas if d['baseline_value'] == 0 and d['current_value'] > 0]
    exited = [d['cusip'] for d in deltas if d['baseline_value'] > 0 and d['current_value'] == 0]

    result = {
        "manager": query,
        "baseline_accession": bl_acc,
        "current_accession": cur_acc,
        "top_increased": increased[:10],
        "top_decreased": decreased[:10],
        "new_positions": new_pos[:10],
        "exited_positions": exited[:10]
    }
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: compare_13f_quarters.py <baseline_dir> <current_dir> <manager_name>")
        sys.exit(1)
    compare_quarters(sys.argv[1], sys.argv[2], sys.argv[3])
