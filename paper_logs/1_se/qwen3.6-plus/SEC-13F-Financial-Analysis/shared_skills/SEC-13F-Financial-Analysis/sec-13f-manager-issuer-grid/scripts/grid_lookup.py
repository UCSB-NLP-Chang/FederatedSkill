#!/usr/bin/env python3
"""Compute holding values for a grid of manager-issuer pairs in a single SEC 13F quarter."""
import csv
import json
import re
import sys
from collections import defaultdict

def normalize(s: str) -> str:
    return re.sub(r'[^\w\s]', '', s.lower()).strip()

def resolve_managers(coverpage_path: str, queries: list[str]) -> dict[str, str]:
    targets = {normalize(q): q for q in queries}
    resolved = {}
    with open(coverpage_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            mgr = row.get('FILINGMANAGER_NAME') or row.get('MANAGER_NAME', '')
            norm = normalize(mgr)
            if norm in targets:
                resolved[targets[norm]] = row.get('ACCESSION_NUMBER')
    return resolved

def resolve_cusips(infotable_path: str, queries: list[str]) -> dict[str, str]:
    targets = {normalize(q): q for q in queries}
    cusip_values = defaultdict(lambda: defaultdict(float))
    with open(infotable_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        name_col = 'NAMEOFISSUER'
        cusip_col = 'CUSIP'
        val_col = 'VALUEUSD' if 'VALUEUSD' in reader.fieldnames else 'VALUE'
        for row in reader:
            norm_name = normalize(row.get(name_col, ''))
            for q_norm, q_orig in targets.items():
                if q_norm in norm_name:
                    cusip = row.get(cusip_col, '').strip()
                    if cusip:
                        cusip_values[q_orig][cusip] += float(row.get(val_col, 0))
    
    resolved = {}
    for q_orig, cusip_map in cusip_values.items():
        if cusip_map:
            resolved[q_orig] = max(cusip_map, key=cusip_map.get)
    return resolved

def compute_grid(infotable_path: str, coverpage_path: str, pairs: list[dict]) -> list[dict]:
    managers = list({p['manager'] for p in pairs})
    issuers = list({p['issuer'] for p in pairs})
    
    mgr_to_acc = resolve_managers(coverpage_path, managers)
    iss_to_cusip = resolve_cusips(infotable_path, issuers)
    
    holdings = defaultdict(float)
    with open(infotable_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        cusip_col = 'CUSIP'
        val_col = 'VALUEUSD' if 'VALUEUSD' in reader.fieldnames else 'VALUE'
        for row in reader:
            acc = row.get('ACCESSION_NUMBER', '').strip()
            cusip = row.get(cusip_col, '').strip()
            if acc and cusip:
                holdings[(acc, cusip)] += float(row.get(val_col, 0))
                
    results = []
    for p in pairs:
        mgr = p['manager']
        iss = p['issuer']
        acc = mgr_to_acc.get(mgr)
        cusip = iss_to_cusip.get(iss)
        val = 0.0
        if acc and cusip:
            val = holdings.get((acc, cusip), 0.0)
        results.append({
            "manager": mgr,
            "issuer": iss,
            "cusip": cusip,
            "value_thousands": val,
            "value_usd": val * 1000
        })
    return results

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: grid_lookup.py <infotable.tsv> <coverpage.tsv> <pairs.json>")
        sys.exit(1)
    with open(sys.argv[3], 'r') as f:
        pairs = json.load(f)
    res = compute_grid(sys.argv[1], sys.argv[2], pairs)
    print(json.dumps(res, indent=2))
