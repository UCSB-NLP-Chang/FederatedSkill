#!/usr/bin/env python3
"""Roll up SEC 13F holdings by issuer to find top institutional managers."""
import csv
import json
import re
import sys
from collections import defaultdict

def normalize(s: str) -> str:
    return re.sub(r'[^\w\s]', '', s.lower()).strip()

def resolve_cusip(infotable_path: str, query: str) -> str:
    q = normalize(query)
    matches = defaultdict(float)
    with open(infotable_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        name_col = 'NAMEOFISSUER'
        cusip_col = 'CUSIP'
        val_col = 'VALUEUSD' if 'VALUEUSD' in reader.fieldnames else 'VALUE'
        for row in reader:
            if q in normalize(row.get(name_col, '')):
                cusip = row.get(cusip_col, '').strip()
                if cusip:
                    matches[cusip] += float(row.get(val_col, 0))
    if not matches:
        print(json.dumps({"error": f"Issuer '{query}' not found"}))
        sys.exit(1)
    return max(matches, key=matches.get)

def rollup(infotable_path: str, coverpage_path: str, query: str, top_n: int):
    cusip = resolve_cusip(infotable_path, query)
    
    mgr_values = defaultdict(float)
    with open(infotable_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        cusip_col = 'CUSIP'
        val_col = 'VALUEUSD' if 'VALUEUSD' in reader.fieldnames else 'VALUE'
        for row in reader:
            if row.get(cusip_col, '').strip() == cusip:
                acc = row.get('ACCESSION_NUMBER', '').strip()
                if acc:
                    mgr_values[acc] += float(row.get(val_col, 0))
                    
    acc_to_mgr = {}
    with open(coverpage_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        mgr_col = 'FILINGMANAGER_NAME'
        for row in reader:
            acc = row.get('ACCESSION_NUMBER', '').strip()
            if acc:
                acc_to_mgr[acc] = row.get(mgr_col, 'Unknown')
                
    results = []
    for acc, val in mgr_values.items():
        results.append({
            "manager": acc_to_mgr.get(acc, "Unknown"),
            "accession_number": acc,
            "value_thousands": val,
            "value_usd": val * 1000
        })
        
    results.sort(key=lambda x: x['value_thousands'], reverse=True)
    top = results[:top_n]
    
    print(json.dumps({
        "issuer_query": query,
        "resolved_cusip": cusip,
        "top_managers": top
    }, indent=2))

if __name__ == '__main__':
    if len(sys.argv) != 5:
        print("Usage: issuer_rollup.py <infotable.tsv> <coverpage.tsv> <issuer_query> <top_n>")
        sys.exit(1)
    rollup(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]))
