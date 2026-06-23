#!/usr/bin/env python3
"""Compute class breakdown for 13F stock-like holdings by TITLEOFCLASS frequency."""
import csv
import sys
import json
from collections import Counter

# SEC abbreviation patterns for common equity
STOCK_KEYWORDS = {"COM", "SHS", "CL A", "CL B", "CL C", "ORD", "CAP STK", "COMMON", "STK", "CLASS A", "CLASS B", "CLASS C"}

# Exclusion patterns for non-equity securities
EXCLUDE_KEYWORDS = {"NOTE", "DEB", "BOND", "PUT", "CALL", "WTS", "RIGHT", "ETF", "FUND", "UNIT", "TR", "ADR", "PRFD", "PFD"}


def is_stock_like(title: str) -> bool:
    """Check if TITLEOFCLASS indicates common equity using SEC abbreviations."""
    t = title.upper().strip()

    for kw in EXCLUDE_KEYWORDS:
        if kw in t:
            return False

    for kw in STOCK_KEYWORDS:
        if t == kw or t.startswith(kw + " ") or t.startswith(kw + "."):
            return True
    return False


def compute_class_breakdown(filepath: str, accession: str) -> dict:
    """
    Compute class breakdown for a specific accession number.

    Returns dict with aum_total, stock_row_count, stock_cusip_count,
    top_class_labels, and top_class_counts.
    """
    total_aum = 0.0
    stock_rows = []

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

            total_aum += val * 1000  # Convert from thousands to USD

            title = row.get('TITLEOFCLASS', '').strip()
            if is_stock_like(title):
                cusip = row.get('CUSIP', '').strip()
                stock_rows.append({
                    'title': title.lower(),
                    'cusip': cusip
                })

    # Count by class label
    title_counts = Counter(r['title'] for r in stock_rows)

    # Get top 4: sort by count desc, then alphabetically for ties
    top4 = title_counts.most_common()
    top4.sort(key=lambda x: (-x[1], x[0]))
    top4 = top4[:4]

    distinct_cusips = len(set(r['cusip'] for r in stock_rows))

    return {
        "aum_total": total_aum,
        "stock_row_count": len(stock_rows),
        "stock_cusip_count": distinct_cusips,
        "top_class_labels": [t[0] for t in top4],
        "top_class_counts": [t[1] for t in top4]
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: class_breakdown.py <infotable_path> <accession_number>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    accession = sys.argv[2]

    result = compute_class_breakdown(filepath, accession)
    print(json.dumps(result, indent=2))