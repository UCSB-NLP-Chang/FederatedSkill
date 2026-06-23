#!/usr/bin/env python3
"""Classify 13F INFOTABLE holdings and compute AUM metrics."""
import csv
import sys
import json

STOCK_KEYWORDS = {"COM", "SHS", "CL A", "CL B", "CL C", "ORD", "CAP STK", "COMMON", "STK", "CLASS A", "CLASS B", "CLASS C"}
EXCLUDE_KEYWORDS = {"NOTE", "DEB", "BOND", "PUT", "CALL", "WTS", "RIGHT", "ETF", "FUND", "UNIT", "TR", "ADR", "PFD", "PRFD"}

def is_stock_like(title):
    t = title.upper().strip()
    for kw in EXCLUDE_KEYWORDS:
        if kw in t:
            return False
    for kw in STOCK_KEYWORDS:
        if t == kw or t.startswith(kw + " ") or t.endswith(" " + kw) or t.startswith(kw + "."):
            return True
    return False

def process_infotable(filepath, accession):
    total_aum = 0.0
    stock_aum = 0.0
    stock_count = 0
    cusip_values = []

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('ACCESSION_NUMBER') != accession:
                continue
            val_str = row.get('VALUE', '0').strip()
            try:
                val = float(val_str)
            except ValueError:
                val = 0.0
            total_aum += val

            title = row.get('TITLEOFCLASS', '')
            if is_stock_like(title):
                stock_aum += val
                stock_count += 1
                cusip = row.get('CUSIP', '').strip()
                cusip_values.append((cusip, val))

    cusip_values.sort(key=lambda x: x[1], reverse=True)
    top3 = [c[0] for c in cusip_values[:3]]

    return {
        "total_aum": total_aum * 1000,
        "stock_aum": stock_aum * 1000,
        "stock_count": stock_count,
        "top3_cusips": top3
    }

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: classify_holdings.py <infotable_path> <accession_number>")
        sys.exit(1)
    result = process_infotable(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))