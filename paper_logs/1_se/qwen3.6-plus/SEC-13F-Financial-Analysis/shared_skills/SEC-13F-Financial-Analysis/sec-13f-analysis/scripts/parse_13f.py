#!/usr/bin/env python3
"""Robust parser for SEC 13F COVERPAGE and INFOTABLE TSV files."""
import csv
import json
import re
import sys

def normalize_name(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r'[^\w\s]', '', n)
    for suffix in ['llc', 'inc', 'lp', 'ltd', 'co', 'corp', 'llp', 'l p', 'l l c']:
        n = re.sub(rf'\b{suffix}\b', '', n).strip()
    return n

def is_equity(title: str) -> bool:
    t = title.upper()
    equity_indicators = ['COM', 'SHS', 'CL A', 'CL B', 'CL C', 'ORD', 'COMMON', 'CAP STK', 'SPONSORED ADS', 'TR UNIT']
    non_equity_indicators = ['PFD', 'NOTE', 'DEB', 'BOND', 'ETF', 'RIGHT', 'WARR', 'ADS', 'PRF', 'PREF']
    if any(x in t for x in non_equity_indicators):
        return False
    return any(x in t for x in equity_indicators)

def parse_13f(coverpage_path: str, infotable_path: str, query: str):
    target_norm = normalize_name(query)
    matched_name = None
    matched_accession = None
    
    with open(coverpage_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            mgr_name = row.get('FILINGMANAGER_NAME') or row.get('MANAGER_NAME', '')
            if normalize_name(mgr_name) == target_norm:
                matched_name = mgr_name
                matched_accession = row.get('ACCESSION_NUMBER')
                break
    
    if not matched_accession:
        print(json.dumps({"error": f"Manager '{query}' not found in COVERPAGE"}))
        sys.exit(1)

    total_aum_raw = 0.0
    stock_aum_raw = 0.0
    stock_count = 0
    stock_holdings = []

    with open(infotable_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        title_col = 'TITLEOFCLASS' if 'TITLEOFCLASS' in reader.fieldnames else 'TITLE'
        value_col = 'VALUEUSD' if 'VALUEUSD' in reader.fieldnames else 'VALUE'
        
        for row in reader:
            if row.get('ACCESSION_NUMBER') != matched_accession:
                continue
            val = float(row.get(value_col, 0))
            total_aum_raw += val
            if is_equity(row.get(title_col, '')):
                stock_aum_raw += val
                stock_count += 1
                stock_holdings.append({
                    "cusip": row.get('CUSIP'),
                    "title": row.get(title_col),
                    "value_raw": val
                })

    stock_holdings.sort(key=lambda x: x['value_raw'], reverse=True)
    top3_cusips = [h['cusip'] for h in stock_holdings[:3]]

    result = {
        "fund_query": query,
        "matched_manager": matched_name,
        "accession_number": matched_accession,
        "total_aum_thousands": total_aum_raw,
        "stock_holdings_count": stock_count,
        "stock_aum_thousands": stock_aum_raw,
        "top3_cusips_by_value": top3_cusips
    }
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: parse_13f.py <coverpage.tsv> <infotable.tsv> <manager_name>")
        sys.exit(1)
    parse_13f(sys.argv[1], sys.argv[2], sys.argv[3])
