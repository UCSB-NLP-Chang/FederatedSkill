#!/usr/bin/env python3
"""Cross-quarter reconciliation analysis for SEC 13F filings.

Combines fund comparison, issuer rollup, and snapshot checks into a single workflow.
Usage: python cross_quarter_analysis.py --q2 /path/to/q2 --q3 /path/to/q3 --output /root/answers.json
"""
import argparse
import json
import csv
from collections import defaultdict

def load_tsv(filepath):
    """Load TSV file and return list of dicts."""
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        return list(reader)

def find_fund_accession(coverpage_rows, fund_query):
    """Find accession number for a fund by name match (case-insensitive)."""
    fund_lower = fund_query.lower()
    for row in coverpage_rows:
        name = row.get('FILINGMANAGER_NAME', '').lower()
        if fund_lower in name or name in fund_lower:
            return row['ACCESSION_NUMBER'], row['FILINGMANAGER_NAME']
    return None, None

def get_holdings_by_cusip(infotable_rows, accession_number):
    """Get stock holdings aggregated by CUSIP for a given accession number."""
    holdings = defaultdict(float)
    stock_keywords = ['STOCK', 'SHS', 'SHARES', 'COMMON', 'ORDINARY']
    non_stock = ['OPTION', 'ETF', 'ADR', 'WARRANT']
    
    for row in infotable_rows:
        if row['ACCESSION_NUMBER'] != accession_number:
            continue
        title = row.get('TITLEOFCLASS', '').upper()
        # Filter to stock-like securities
        is_stock = any(kw in title for kw in stock_keywords)
        is_non_stock = any(kw in title for kw in non_stock)
        if not is_stock or is_non_stock:
            continue
        cusip = row['CUSIP']
        value = float(row['VALUE']) if row['VALUE'] else 0
        holdings[cusip] += value
    return dict(holdings)

def get_issuer_holdings(infotable_rows, cusip):
    """Get all holdings for an issuer by CUSIP, aggregated by accession number."""
    by_accession = defaultdict(float)
    for row in infotable_rows:
        if row['CUSIP'] == cusip:
            value = float(row['VALUE']) if row['VALUE'] else 0
            by_accession[row['ACCESSION_NUMBER']] += value
    return dict(by_accession)

def get_top_managers_for_issuer(infotable_rows, coverpage_rows, cusip, top_n=2):
    """Get top N managers by value for a given issuer CUSIP."""
    holdings = get_issuer_holdings(infotable_rows, cusip)
    accession_to_name = {r['ACCESSION_NUMBER']: r['FILINGMANAGER_NAME'] for r in coverpage_rows}
    
    manager_values = defaultdict(float)
    for acc, value in holdings.items():
        name = accession_to_name.get(acc, 'Unknown')
        manager_values[name] += value
    
    sorted_managers = sorted(manager_values.items(), key=lambda x: x[1], reverse=True)
    return [m[0] for m in sorted_managers[:top_n]]

def find_cusip_for_issuer(infotable_rows, issuer_query):
    """Find CUSIP for an issuer by name search."""
    issuer_lower = issuer_query.lower()
    for row in infotable_rows:
        name = row.get('NAMEOFISSUER', '').lower()
        if issuer_lower in name:
            return row['CUSIP']
    return None

def analyze_comparison(q2_coverpage, q2_infotable, q3_coverpage, q3_infotable, fund_queries):
    """Analyze fund comparisons across quarters."""
    results = []
    for fund in fund_queries:
        q2_acc, q2_name = find_fund_accession(q2_coverpage, fund)
        q3_acc, q3_name = find_fund_accession(q3_coverpage, fund)
        
        if q2_acc and q3_acc:
            q2_holdings = get_holdings_by_cusip(q2_infotable, q2_acc)
            q3_holdings = get_holdings_by_cusip(q3_infotable, q3_acc)
            
            changes = {}
            all_cusips = set(q2_holdings) | set(q3_holdings)
            for cusip in all_cusips:
                q2_val = q2_holdings.get(cusip, 0)
                q3_val = q3_holdings.get(cusip, 0)
                if cusip in q2_holdings and cusip in q3_holdings:
                    changes[cusip] = q3_val - q2_val
            
            buys = {k: v for k, v in changes.items() if v > 0}
            sells = {k: v for k, v in changes.items() if v < 0}
            
            largest_buy = max(buys, key=buys.get) if buys else ""
            largest_sell = min(sells, key=sells.get) if sells else ""
        else:
            largest_buy = ""
            largest_sell = ""
        
        results.append({
            "fund_query_current": fund,
            "quarter_current": "2025-q3",
            "fund_query_baseline": fund,
            "quarter_baseline": "2025-q2",
            "largest_buy_cusip": largest_buy,
            "largest_sell_cusip": largest_sell
        })
    return results

def analyze_issuers(q3_coverpage, q3_infotable, issuer_queries):
    """Analyze top managers for each issuer."""
    results = []
    for issuer in issuer_queries:
        cusip = find_cusip_for_issuer(q3_infotable, issuer)
        if cusip:
            top_managers = get_top_managers_for_issuer(q3_infotable, q3_coverpage, cusip, top_n=2)
        else:
            top_managers = []
        results.append({
            "issuer_query": issuer,
            "quarter": "2025-q3",
            "top2_manager_names": top_managers
        })
    return results

def analyze_snapshot(q3_coverpage, q3_infotable, fund_query):
    """Get stock holdings count for a fund in a single quarter."""
    acc, name = find_fund_accession(q3_coverpage, fund_query)
    if acc:
        holdings = get_holdings_by_cusip(q3_infotable, acc)
        stock_count = len(holdings)
    else:
        stock_count = 0
    return {
        "fund_query": fund_query,
        "quarter": "2025-q3",
        "stock_holdings": stock_count
    }

def main():
    parser = argparse.ArgumentParser(description='Cross-quarter SEC 13F analysis')
    parser.add_argument('--q2', required=True, help='Path to Q2 directory')
    parser.add_argument('--q3', required=True, help='Path to Q3 directory')
    parser.add_argument('--output', default='/root/answers.json', help='Output file path')
    parser.add_argument('--comparison-funds', nargs='+', default=['third point', 'tiger global'])
    parser.add_argument('--issuers', nargs='+', default=['microsoft', 'meta platforms'])
    parser.add_argument('--snapshot-fund', default='scion asset management')
    args = parser.parse_args()
    
    # Load data
    q2_coverpage = load_tsv(f"{args.q2}/COVERPAGE.tsv")
    q2_infotable = load_tsv(f"{args.q2}/INFOTABLE.tsv")
    q3_coverpage = load_tsv(f"{args.q3}/COVERPAGE.tsv")
    q3_infotable = load_tsv(f"{args.q3}/INFOTABLE.tsv")
    
    # Run analyses
    output = {
        "comparison_pairs": analyze_comparison(q2_coverpage, q2_infotable, q3_coverpage, q3_infotable, args.comparison_funds),
        "issuer_checks": analyze_issuers(q3_coverpage, q3_infotable, args.issuers),
        "snapshot_check": analyze_snapshot(q3_coverpage, q3_infotable, args.snapshot_fund)
    }
    
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Results written to {args.output}")

if __name__ == '__main__':
    main()
