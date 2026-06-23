#!/usr/bin/env python3
"""
SEC 13F Filing Analysis Pipeline

Usage:
  python3 process_13f.py <data_dir> <manager_name> <quarter_date>

Outputs JSON to stdout with manager match, AUM, stock holdings, and top CUSIPs.
"""
import csv
import json
import sys
import os
import re
import difflib


def normalize_name(name):
    """Normalize manager name for matching."""
    if not name:
        return ""
    name = name.lower().strip()
    # Remove common legal suffixes
    for suffix in [' llc', ' inc', ' ltd', ' corp', ' lp', ' lllp', ' co', ' advisory', ' management']:
        name = name.replace(suffix, '')
    # Remove punctuation except spaces
    name = re.sub(r'[^\w\s]', ' ', name)
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def is_stock_like(title):
    """
    Classify a holding as stock-like based on TITLEOFCLASS.
    Uses tokenized matching to avoid substring traps.
    """
    if not title:
        return False
    tokens = title.lower().split()
    include = {'common', 'ordinary', 'share', 'shares', 'stock', 'com', 'shs', 'cl', 'class'}
    exclude = {'bond', 'note', 'deb', 'etf', 'trust', 'fund', 'index', 'treas', 'muni', 'pfd', 'pref', 'adr', 'put', 'call', 'option'}
    has_include = any(t in include for t in tokens)
    has_exclude = any(t in exclude for t in tokens)
    return has_include and not has_exclude


def process_13f(data_dir, query_manager, quarter_date):
    cover_path = os.path.join(data_dir, 'COVERPAGE.tsv')
    info_path = os.path.join(data_dir, 'INFOTABLE.tsv')

    # Parse COVERPAGE, filter by quarter
    managers = []
    with open(cover_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('REPORTCALENDARORQUARTER') == quarter_date:
                managers.append(row)

    norm_query = normalize_name(query_manager)
    best_match = None

    # Step 1: Exact match
    for m in managers:
        raw = m.get('FILINGMANAGER_NAME', '')
        norm = normalize_name(raw)
        if norm_query == norm:
            best_match = m
            break

    # Step 2: Substring match (query in manager or manager in query)
    if not best_match:
        for m in managers:
            raw = m.get('FILINGMANAGER_NAME', '')
            norm = normalize_name(raw)
            if norm_query in norm or norm in norm_query:
                best_match = m
                break

    # Step 3: Fuzzy match with high threshold
    if not best_match:
        candidates = []
        for m in managers:
            raw = m.get('FILINGMANAGER_NAME', '')
            norm = normalize_name(raw)
            ratio = difflib.SequenceMatcher(None, norm_query, norm).ratio()
            candidates.append((ratio, m, norm))
        candidates.sort(reverse=True)
        if candidates and candidates[0][0] > 0.85:
            best_match = candidates[0][1]

    # No valid match found
    if not best_match:
        print(json.dumps({"error": f"No match found for '{query_manager}' in {quarter_date}"}))
        sys.exit(1)

    accession = best_match['ACCESSION_NUMBER']
    matched_name = best_match.get('FILINGMANAGER_NAME', '')

    # Parse INFOTABLE
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
    top_cusips = [h['CUSIP'] for h in stock_holdings[:3]]

    result = {
        "manager": matched_name,
        "total_aum": total_aum,
        "stock_aum": stock_aum,
        "stock_holdings_count": len(stock_holdings),
        "top_cusips": top_cusips
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: process_13f.py <data_dir> <manager_name> <quarter_date>")
        sys.exit(1)
    process_13f(sys.argv[1], sys.argv[2], sys.argv[3])
