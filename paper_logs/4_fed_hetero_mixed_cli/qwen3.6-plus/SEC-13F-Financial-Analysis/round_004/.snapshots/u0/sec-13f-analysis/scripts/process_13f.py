#!/usr/bin/env python3
"""
SEC 13F Filing Analysis Pipeline

Usage:
  python3 process_13f.py <data_dir> <manager_name> <quarter_date> [--analysis-type {holdings|class_breakdown}]

Outputs JSON to stdout.
"""
import csv
import json
import sys
import os
import re
import difflib
import argparse
from collections import Counter


def normalize_name(name):
    """Normalize manager name for matching."""
    if not name:
        return ""
    name = name.lower().strip()
    for suffix in [' llc', ' inc', ' ltd', ' corp', ' lp', ' lllp', ' co',
                   ' advisory', ' management', ' group', ' partners']:
        name = name.replace(suffix, '')
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def word_level_match(query_words, manager_words):
    """Check if any word from query appears in manager words."""
    query_set = set(query_words)
    manager_set = set(manager_words)
    return bool(query_set & manager_set)


def find_best_manager(managers, query_manager):
    """Find best matching manager using tiered matching strategy."""
    norm_query = normalize_name(query_manager)
    query_words = norm_query.split()

    # Step 1: Exact normalized match
    for m in managers:
        raw = m.get('FILINGMANAGER_NAME', '')
        norm = normalize_name(raw)
        if norm_query == norm:
            return m

    # Step 2: Substring match (query in manager or manager in query)
    for m in managers:
        raw = m.get('FILINGMANAGER_NAME', '')
        norm = normalize_name(raw)
        if norm_query in norm or norm in norm_query:
            return m

    # Step 3: Word-level match (shared words between query and manager)
    for m in managers:
        raw = m.get('FILINGMANAGER_NAME', '')
        norm = normalize_name(raw)
        manager_words = norm.split()
        if word_level_match(query_words, manager_words):
            return m

    # Step 4: Fuzzy match with high threshold
    best_ratio = 0.0
    best_match = None
    for m in managers:
        raw = m.get('FILINGMANAGER_NAME', '')
        norm = normalize_name(raw)
        ratio = difflib.SequenceMatcher(None, norm_query, norm).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = m

    if best_ratio > 0.85:
        return best_match

    return None


def is_stock_like(title):
    """Classify a holding as stock-like based on TITLEOFCLASS."""
    if not title:
        return False
    tokens = title.lower().split()
    include = {'common', 'ordinary', 'share', 'shares', 'stock', 'com', 'shs', 'cl', 'class'}
    exclude = {'bond', 'note', 'deb', 'etf', 'trust', 'fund', 'index', 'treas', 'muni',
               'pfd', 'pref', 'adr', 'ads', 'put', 'call', 'option', 'warrant', 'right'}
    has_include = any(t in include for t in tokens)
    has_exclude = any(t in exclude for t in tokens)
    return has_include and not has_exclude


def process_holdings_analysis(data_dir, manager):
    """Standard holdings analysis - top CUSIPs."""
    accession = manager['ACCESSION_NUMBER']
    matched_name = manager.get('FILINGMANAGER_NAME', '')

    info_path = os.path.join(data_dir, 'INFOTABLE.tsv')
    holdings = []
    with open(info_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('ACCESSION_NUMBER') == accession:
                holdings.append(row)

    total_aum = sum(float(h.get('VALUE', 0) or 0) for h in holdings)
    stock_holdings = [h for h in holdings if is_stock_like(h.get('TITLEOFCLASS', ''))]
    stock_aum = sum(float(h.get('VALUE', 0) or 0) for h in stock_holdings)

    stock_holdings.sort(key=lambda x: float(x.get('VALUE', 0) or 0), reverse=True)
    top_cusips = [h['CUSIP'] for h in stock_holdings[:3]]

    return {
        "manager": matched_name,
        "total_aum": total_aum,
        "stock_aum": stock_aum,
        "stock_holdings_count": len(stock_holdings),
        "top_cusips": top_cusips
    }


def process_class_breakdown(data_dir, manager):
    """Class breakdown analysis - top TITLEOFCLASS labels."""
    accession = manager['ACCESSION_NUMBER']
    matched_name = manager.get('FILINGMANAGER_NAME', '')

    info_path = os.path.join(data_dir, 'INFOTABLE.tsv')
    holdings = []
    with open(info_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('ACCESSION_NUMBER') == accession:
                holdings.append(row)

    total_aum = sum(float(h.get('VALUE', 0) or 0) for h in holdings)
    stock_holdings = [h for h in holdings if is_stock_like(h.get('TITLEOFCLASS', ''))]

    class_counts = Counter()
    for h in stock_holdings:
        title = h.get('TITLEOFCLASS', 'UNKNOWN')
        class_counts[title] += 1

    top_classes = class_counts.most_common(3)
    top_labels = [c[0] for c in top_classes]
    top_counts = [c[1] for c in top_classes]

    unique_cusips = set(h.get('CUSIP', '') for h in stock_holdings)

    return {
        "manager": matched_name,
        "aum_total": total_aum,
        "stock_row_count": len(stock_holdings),
        "stock_cusip_count": len(unique_cusips),
        "top_class_labels": top_labels,
        "top_class_counts": top_counts
    }


def get_null_result(analysis_type, query_manager, quarter_date):
    """Return properly structured null result."""
    if analysis_type == 'class_breakdown':
        return {
            "manager": None,
            "error": f"No match found for '{query_manager}' in {quarter_date}",
            "aum_total": None,
            "stock_row_count": None,
            "stock_cusip_count": None,
            "top_class_labels": [],
            "top_class_counts": []
        }
    else:
        return {
            "manager": None,
            "error": f"No match found for '{query_manager}' in {quarter_date}",
            "total_aum": None,
            "stock_aum": None,
            "stock_holdings_count": None,
            "top_cusips": []
        }


def process_13f(data_dir, query_manager, quarter_date, analysis_type='holdings'):
    cover_path = os.path.join(data_dir, 'COVERPAGE.tsv')

    managers = []
    with open(cover_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('REPORTCALENDARORQUARTER') == quarter_date:
                managers.append(row)

    if not managers:
        result = get_null_result(analysis_type, query_manager, quarter_date)
        result["error"] = f"No filings found for quarter '{quarter_date}'"
        print(json.dumps(result, indent=2))
        sys.exit(0)

    best_match = find_best_manager(managers, query_manager)

    if not best_match:
        result = get_null_result(analysis_type, query_manager, quarter_date)
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if analysis_type == 'class_breakdown':
        result = process_class_breakdown(data_dir, best_match)
    else:
        result = process_holdings_analysis(data_dir, best_match)

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process 13F filings')
    parser.add_argument('data_dir', help='Directory containing COVERPAGE.tsv and INFOTABLE.tsv')
    parser.add_argument('manager_name', help='Manager name to search for')
    parser.add_argument('quarter_date', help='Quarter date (e.g., 30-SEP-2025)')
    parser.add_argument('--analysis-type', choices=['holdings', 'class_breakdown'], default='holdings',
                        help='Type of analysis to perform')
    args = parser.parse_args()

    process_13f(args.data_dir, args.manager_name, args.quarter_date, args.analysis_type)
