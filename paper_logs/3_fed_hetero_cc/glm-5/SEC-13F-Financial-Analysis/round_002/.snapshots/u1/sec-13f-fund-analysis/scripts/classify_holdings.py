#!/usr/bin/env python3
"""Classify 13F INFOTABLE holdings and compute AUM metrics."""

import csv
import sys
import json


# SEC abbreviations for common equity (exact match or prefix)
STOCK_KEYWORDS = {
    "COM", "SHS", "CL A", "CL B", "CL C", "ORD", "CAP STK",
    "COMMON", "STK", "CLASS A", "CLASS B", "CLASS C"
}

# Exclusion patterns for non-equity securities
EXCLUDE_KEYWORDS = {
    "NOTE", "DEB", "BOND", "PUT", "CALL", "WTS", "RIGHT",
    "ETF", "FUND", "UNIT", "TR", "ADR", "PFD", "PREF"
}


def is_stock_like(title):
    """Check if TITLEOFCLASS indicates common equity."""
    t = title.upper().strip()

    # First check exclusions
    for excl in EXCLUDE_KEYWORDS:
        if t.startswith(excl) or excl in t.split():
            return False

    # Check stock keywords (exact match or prefix)
    for kw in STOCK_KEYWORDS:
        if t == kw or t.startswith(kw + " ") or t.startswith(kw + "."):
            return True

    return False


def process_infotable(filepath, accession):
    """
    Process INFOTABLE.tsv for a given accession number.

    Returns dict with total_aum, stock_aum, stock_count, top3_cusips.
    Note: VALUE in 13F filings is in thousands USD.
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

    # Sort by value descending, extract top 3 CUSIPs
    cusip_values.sort(key=lambda x: x[1], reverse=True)
    top3 = [c[0] for c in cusip_values[:3]]

    # Return raw values (no rounding) — agent decides precision at trial time
    return {
        "total_aum": total_aum,
        "stock_aum": stock_aum,
        "stock_count": stock_count,
        "top3_cusips": top3
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: classify_holdings.py <infotable.tsv> <accession_number>", file=sys.stderr)
        sys.exit(1)

    result = process_infotable(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))