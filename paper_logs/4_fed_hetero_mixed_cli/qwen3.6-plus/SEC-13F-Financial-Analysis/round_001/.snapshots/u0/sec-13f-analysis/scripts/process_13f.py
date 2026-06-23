#!/usr/bin/env python3
"""Process SEC 13F filing data to extract manager info, AUM, stock holdings, and top CUSIPs.

Usage: python3 process_13f.py <data_dir> <manager_name> <quarter_date>
Output: JSON to stdout
"""
import csv
import json
import sys
import os
import re
from difflib import SequenceMatcher


def normalize_name(name):
    if not name:
        return ""
    name = name.lower().strip()
    for suffix in [' llc', ' inc', ' ltd', ' corp', ' lp', ' lllp', ' co', ' advisory']:
        name = name.replace(suffix, '')
    name = re.sub(r'[^\w\s]', '', name)
    return name.strip()


def is_stock_like(title):
    if not title:
        return False
    tokens = title.lower().split()
    include = {'common', 'ordinary', 'share', 'stock', 'com', 'shs', 'cl', 'class'}
    exclude = {'bond', 'note', 'deb', 'etf', 'trust', 'fund', 'index', 'treas', 'muni',
               'pfd', 'pref', 'adr', 'ads', 'put', 'call', 'option', 'warrant', 'right'}
    has_include = any(t in include for t in tokens)
    has_exclude = any(t in exclude for t in tokens)
    return has_include and not has_exclude


def match_manager(managers, query_manager):
    norm_query = normalize_name(query_manager)
    best_match = None

    # 1. Exact match
    for m in managers:
        norm = normalize_name(m.get('FILINGMANAGER_NAME', ''))
        if norm_query == norm:
            return m

    # 2. Substring match (query contained in manager or vice versa)
    for m in managers:
        norm = normalize_name(m.get('FILINGMANAGER_NAME', ''))
        if norm_query in norm or norm in norm_query:
            return m

    # 3. Fuzzy match with high threshold only
    best_ratio = 0.0
    for m in managers:
        norm = normalize_name(m.get('FILINGMANAGER_NAME', ''))
        ratio = SequenceMatcher(None, norm_query, norm).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = m

    if best_ratio > 0.85:
        return best_match

    return None


def process_13f(data_dir, query_manager, quarter_date):
    cover_path = os.path.join(data_dir, 'COVERPAGE.tsv')
    info_path = os.path.join(data_dir, 'INFOTABLE.tsv')

    managers = []
    with open(cover_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('REPORTCALENDARORQUARTER') == quarter_date:
                managers.append(row)

    if not managers:
        print(json.dumps({"error": f"No filings found for quarter '{quarter_date}'"}))
        sys.exit(1)

    matched = match_manager(managers, query_manager)
    if not matched:
        print(json.dumps({"error": f"No match found for '{query_manager}' in {quarter_date}"}))
        sys.exit(1)

    accession = matched['ACCESSION_NUMBER']
    matched_name = matched['FILINGMANAGER_NAME']

    holdings = []
    with open(info_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row['ACCESSION_NUMBER'] == accession:
                holdings.append(row)

    total_aum = sum(float(h.get('VALUE', 0)) for h in holdings)
    stock_holdings = [h for h in holdings if is_stock_like(h.get('TITLEOFCLASS', ''))]
    stock_aum = sum(float(h.get('VALUE', 0)) for h in stock_holdings)

    stock_holdings.sort(key=lambda x: float(x.get('VALUE', 0)), reverse=True)
    top3 = [h['CUSIP'] for h in stock_holdings[:3]]

    result = {
        "fund_query": query_manager,
        "quarter": quarter_date,
        "matched_manager": matched_name,
        "accession_number": accession,
        "aum": total_aum,
        "stock_holdings": len(stock_holdings),
        "stock_aum": stock_aum,
        "top3_cusips_by_value": top3
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: process_13f.py <data_dir> <manager_name> <quarter_date>", file=sys.stderr)
        sys.exit(1)
    process_13f(sys.argv[1], sys.argv[2], sys.argv[3])