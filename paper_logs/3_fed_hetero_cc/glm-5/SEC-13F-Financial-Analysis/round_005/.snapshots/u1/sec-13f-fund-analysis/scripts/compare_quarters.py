#!/usr/bin/env python3
"""Compare 13F holdings across two quarters to find position changes."""

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


def load_stock_holdings(filepath, accession):
    """Load stock-like holdings for a given accession number.
    
    Returns dict mapping CUSIP -> VALUE (in actual USD, not thousands).
    """
    holdings = {}
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('ACCESSION_NUMBER') != accession:
                continue
            
            title = row.get('TITLEOFCLASS', '')
            if not is_stock_like(title):
                continue
            
            cusip = row.get('CUSIP', '').strip()
            val_str = row.get('VALUE', '0').strip()
            try:
                val = float(val_str) * 1000  # Convert from thousands to USD
            except ValueError:
                val = 0.0
            
            if cusip:
                holdings[cusip] = holdings.get(cusip, 0.0) + val
    
    return holdings


def compare_quarters(baseline_file, baseline_accession, current_file, current_accession):
    """Compare holdings between two quarters.
    
    Returns dict with top4_increased_cusips, top3_decreased_cusips, new_positions_top2.
    """
    baseline_holdings = load_stock_holdings(baseline_file, baseline_accession)
    current_holdings = load_stock_holdings(current_file, current_accession)
    
    # Compute changes for positions in current quarter
    changes = {}
    for cusip, current_val in current_holdings.items():
        baseline_val = baseline_holdings.get(cusip, 0.0)
        changes[cusip] = current_val - baseline_val
    
    # Top 4 increased (positive changes, largest first)
    increased = [(cusip, change) for cusip, change in changes.items() if change > 0]
    increased.sort(key=lambda x: x[1], reverse=True)
    top4_increased = [cusip for cusip, _ in increased[:4]]
    
    # Top 3 decreased (negative changes, most negative first)
    decreased = [(cusip, change) for cusip, change in changes.items() if change < 0]
    decreased.sort(key=lambda x: x[1])
    top3_decreased = [cusip for cusip, _ in decreased[:3]]
    
    # New positions (in current but not in baseline)
    new_positions = [(cusip, current_holdings[cusip]) 
                      for cusip in current_holdings 
                      if cusip not in baseline_holdings]
    new_positions.sort(key=lambda x: x[1], reverse=True)
    new_positions_top2 = [cusip for cusip, _ in new_positions[:2]]
    
    return {
        "top4_increased_cusips": top4_increased,
        "top3_decreased_cusips": top3_decreased,
        "new_positions_top2": new_positions_top2,
        "baseline_holdings_count": len(baseline_holdings),
        "current_holdings_count": len(current_holdings)
    }


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: compare_quarters.py <baseline_infotable.tsv> <baseline_accession> <current_infotable.tsv> <current_accession>", 
              file=sys.stderr)
        sys.exit(1)
    
    baseline_file = sys.argv[1]
    baseline_accession = sys.argv[2]
    current_file = sys.argv[3]
    current_accession = sys.argv[4]
    
    result = compare_quarters(baseline_file, baseline_accession, 
                              current_file, current_accession)
    print(json.dumps(result, indent=2))