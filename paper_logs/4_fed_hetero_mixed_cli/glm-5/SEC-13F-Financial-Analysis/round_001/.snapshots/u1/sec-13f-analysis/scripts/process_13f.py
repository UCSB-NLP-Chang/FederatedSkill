#!/usr/bin/env python3
"""
SEC 13F Filing Analysis Script

Usage:
  python3 process_13f.py <data_dir> <manager_name> <quarter_date> [--top-n N]

Outputs JSON to stdout with manager match info, AUM metrics, stock holdings, and top CUSIPs.
"""
import csv
import json
import sys
import os
import re
import difflib

# Stock classification tokens
STOCK_INCLUDE = {'common', 'com', 'ordinary', 'shares', 'shs', 'stock', 'class', 'cl'}
STOCK_EXCLUDE = {'etf', 'put', 'call', 'option', 'bond', 'note', 'preferred', 'pfd', 'adr', 'trust', 'fund', 'index', 'deb', 'treas', 'muni'}

LEGAL_SUFFIXES = [' llc', ' inc', ' ltd', ' corp', ' lp', ' lllp', ' co', ' advisory', ' management', ' partners']


def normalize_name(name):
    """Normalize manager name for matching."""
    if not name:
        return ""
    name = name.lower().strip()
    for suffix in LEGAL_SUFFIXES:
        name = name.replace(suffix, '')
    name = re.sub(r'[^\w\s]', '', name)
    return ' '.join(name.split())


def is_stock_like(title):
    """Determine if TITLEOFCLASS indicates a stock holding using tokenized matching."""
    if not title:
        return False
    tokens = title.lower().split()
    has_include = any(t in STOCK_INCLUDE for t in tokens)
    has_exclude = any(t in STOCK_EXCLUDE for t in tokens)
    return has_include and not has_exclude


def match_manager(managers, query_manager, threshold=0.85):
    """
    Match manager name with strict fallback rules.
    Returns (matched_row, matched_name, confidence) or (None, None, None) if no match.
    """
    norm_query = normalize_name(query_manager)

    # 1. Exact match
    for m in managers:
        raw_name = m.get('FILINGMANAGER_NAME', '')
        if normalize_name(raw_name) == norm_query:
            return (m, raw_name, 1.0)

    # 2. Substring match (query in manager)
    for m in managers:
        raw_name = m.get('FILINGMANAGER_NAME', '')
        norm_name = normalize_name(raw_name)
        if norm_query in norm_name:
            return (m, raw_name, 0.95)

    # 3. Manager contains query as word
    query_words = norm_query.split()
    for m in managers:
        raw_name = m.get('FILINGMANAGER_NAME', '')
        norm_name = normalize_name(raw_name)
        name_words = norm_name.split()
        if any(qw in name_words for qw in query_words):
            return (m, raw_name, 0.90)

    # 4. Fuzzy match with high threshold only
    candidates = []
    for m in managers:
        raw_name = m.get('FILINGMANAGER_NAME', '')
        norm_name = normalize_name(raw_name)
        ratio = difflib.SequenceMatcher(None, norm_query, norm_name).ratio()
        if ratio > threshold:
            candidates.append((ratio, m, raw_name))

    if candidates:
        candidates.sort(reverse=True)
        best_ratio, best_row, best_name = candidates[0]
        return (best_row, best_name, best_ratio)

    return (None, None, None)


def process_13f(data_dir, query_manager, quarter_date, top_n=3):
    """Process SEC 13F filing and extract metrics."""
    cover_path = os.path.join(data_dir, 'COVERPAGE.tsv')
    info_path = os.path.join(data_dir, 'INFOTABLE.tsv')

    if not os.path.exists(cover_path):
        return {"error": f"COVERPAGE.tsv not found in {data_dir}"}
    if not os.path.exists(info_path):
        return {"error": f"INFOTABLE.tsv not found in {data_dir}"}

    # Filter managers by quarter
    managers = []
    with open(cover_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('REPORTCALENDARORQUARTER') == quarter_date:
                managers.append(row)

    if not managers:
        return {"error": f"No filings found for quarter {quarter_date}"}

    # Match manager
    matched_row, matched_name, confidence = match_manager(managers, query_manager)

    if not matched_row:
        return {
            "error": f"No match found for '{query_manager}' in {quarter_date}",
            "query": query_manager,
            "quarter": quarter_date,
            "available_managers": [m.get('FILINGMANAGER_NAME', '') for m in managers[:10]]
        }

    accession = matched_row['ACCESSION_NUMBER']

    # Extract holdings
    holdings = []
    with open(info_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('ACCESSION_NUMBER') == accession:
                holdings.append(row)

    # Calculate metrics
    total_aum = sum(float(h.get('VALUE', 0) or 0) for h in holdings)
    stock_holdings = [h for h in holdings if is_stock_like(h.get('TITLEOFCLASS', ''))]
    stock_aum = sum(float(h.get('VALUE', 0) or 0) for h in stock_holdings)

    # Top CUSIPs by value
    stock_holdings.sort(key=lambda x: float(x.get('VALUE', 0) or 0), reverse=True)
    top_cusips = [h.get('CUSIP', '') for h in stock_holdings[:top_n]]

    result = {
        "fund_query": query_manager,
        "matched_manager": matched_name,
        "match_confidence": confidence,
        "quarter": quarter_date,
        "accession_number": accession,
        "total_aum": total_aum,
        "stock_holdings_count": len(stock_holdings),
        "stock_aum": stock_aum,
        f"top_{top_n}_cusips_by_value": top_cusips
    }

    return result


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: process_13f.py <data_dir> <manager_name> <quarter_date> [--top-n N]")
        print("Example: process_13f.py 2025-q3 'Renaissance Technologies' '30-SEP-2025'")
        sys.exit(1)

    data_dir = sys.argv[1]
    manager_name = sys.argv[2]
    quarter_date = sys.argv[3]
    top_n = 3

    if len(sys.argv) > 4 and sys.argv[4].startswith('--top-n'):
        try:
            top_n = int(sys.argv[4].split('=')[1] if '=' in sys.argv[4] else sys.argv[5])
        except (ValueError, IndexError):
            pass

    result = process_13f(data_dir, manager_name, quarter_date, top_n)
    print(json.dumps(result, indent=2))