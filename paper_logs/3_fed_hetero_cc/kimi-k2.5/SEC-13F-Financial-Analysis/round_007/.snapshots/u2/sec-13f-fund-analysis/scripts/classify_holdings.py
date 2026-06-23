#!/usr/bin/env python3
"""Classify 13F INFOTABLE holdings and compute AUM metrics using SEC abbreviations."""
import csv
import sys
import json

# SEC abbreviation patterns for common equity (from actual TITLEOFCLASS values)
STOCK_KEYWORDS = {"COM", "SHS", "CL A", "CL B", "CL C", "ORD", "CAP STK", "COMMON", "STK", "CLASS A", "CLASS B", "CLASS C"}

# Exclusion patterns for non-equity securities
EXCLUDE_KEYWORDS = {"NOTE", "DEB", "BOND", "PUT", "CALL", "WTS", "RIGHT", "ETF", "FUND", "UNIT", "TR", "ADR", "PRFD", "PFD"}

def is_stock_like(title: str) -> bool:
    """Check if TITLEOFCLASS indicates common equity using SEC abbreviations."""
    t = title.upper().strip()

    # Check exclusions first
    for kw in EXCLUDE_KEYWORDS:
        if kw in t:
            return False

    # Check stock patterns - must match exactly or as prefix
    for kw in STOCK_KEYWORDS:
        if t == kw or t.startswith(kw + " ") or t.startswith(kw + "."):
            return True
    return False


def process_infotable(filepath: str, accession: str) -> dict:
    """
    Process INFOTABLE for a specific accession number.

    Returns dict with total_aum, stock_aum, stock_count, and top3_cusips.
    """
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
        "total_aum": total_aum,
        "stock_aum": stock_aum,
        "stock_count": stock_count,
        "top3_cusips": top3
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: classify_holdings.py <infotable_path> <accession_number>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    accession = sys.argv[2]

    result = process_infotable(filepath, accession)
    print(json.dumps(result, indent=2))