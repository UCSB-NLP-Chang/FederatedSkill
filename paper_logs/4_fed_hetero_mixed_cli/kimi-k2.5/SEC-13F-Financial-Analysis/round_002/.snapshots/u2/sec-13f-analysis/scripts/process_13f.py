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
    # Remove common legal suffixes
    for suffix in [' llc', ' inc', ' ltd', ' corp', ' lp', ' lllp', ' co', ' advisory', ' management', ' group', ' partners']:
        name = name.replace(suffix, '')
    # Remove punctuation except spaces
    name = re.sub(r'[^\w\s]', ' ', name)
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def word_overlap_score(query_norm, candidate_norm):
    """Calculate word overlap between normalized names."""
    stop_words = {'the', 'and', 'of', 'associates', 'group', 'capital', 'partners', 'management', 'advisory', 'investment'}
    query_words = set(query_norm.split()) - stop_words
    candidate_words = set(candidate_norm.split()) - stop_words
    if not query_words or not candidate_words:
        return 0.0
    intersection = query_words & candidate_words
    union = query_words | candidate_words
    return len(intersection) / len(union)


def find_best_manager(managers, query_manager):
    """Find best matching manager using tiered matching strategy."""
    norm_query = normalize_name(query_manager)
    best_match = None

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

    # Step 3: Word overlap (Jaccard > 0.3 or significant shared word)
    best_overlap = 0
    overlap_match = None
    for m in managers:
        raw = m.get('FILINGMANAGER_NAME', '')
        norm = normalize_name(raw)
        score = word_overlap_score(norm_query, norm)
        if score > best_overlap:
            best_overlap = score
            overlap_match = m
    if best_overlap >= 0.3:
        return overlap_match

    # Step 4: Fuzzy match with high threshold
    candidates = []
    for m in managers:
        raw = m.get('FILINGMANAGER_NAME', '')
        norm = normalize_name(raw)
        ratio = difflib.SequenceMatcher(None, norm_query, norm).ratio()
        candidates.append((ratio, m))
    candidates.sort(reverse=True)
    if candidates and candidates[0][0] > 0.85:
        return candidates[0][1]

    return None


def is_stock_like(title):
    """Classify a holding as stock-like based on TITLEOFCLASS."""
    if not title:
        return False
    tokens = title.lower().split()
    include = {'common', 'ordinary', 'share', 'shares', 'stock', 'com', 'shs', 'cl', 'class'}
    exclude = {'bond', 'note', 'deb', 'etf', 'trust', 'fund', 'index', 'treas', 'muni', 'pfd', 'pref', 'adr', 'put', 'call', 'option'}
    has_include = any(t in include for t in tokens)
    has_exclude = any(t in exclude for t in tokens)
    return has_include and not has_exclude


def process_holdings_analysis(data_dir, manager, quarter_date):
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


def process_class_breakdown(data_dir, manager, quarter_date):
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

    # Count by class
    class_counts = Counter()
    for h in stock_holdings:
        title = h.get('TITLEOFCLASS', 'UNKNOWN')
        class_counts[title] += 1

    top_classes = class_counts.most_common(3)
    top_labels = [c[0] for c in top_classes]
    top_counts = [c[1] for c in top_classes]

    # Unique CUSIPs among stock holdings
    unique_cusips = set(h.get('CUSIP', '') for h in stock_holdings)

    return {
        "manager": matched_name,
        "aum_total": total_aum,
        "stock_row_count": len(stock_holdings),
        "stock_cusip_count": len(unique_cusips),
        "top_class_labels": top_labels,
        "top_class_counts": top_counts
    }


def process_13f(data_dir, query_manager, quarter_date, analysis_type='holdings'):
    cover_path = os.path.join(data_dir, 'COVERPAGE.tsv')

    # Parse COVERPAGE, filter by quarter
    managers = []
    with open(cover_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('REPORTCALENDARORQUARTER') == quarter_date:
                managers.append(row)

    best_match = find_best_manager(managers, query_manager)

    if not best_match:
        result = {
            "manager": None,
            "error": f"No match found for '{query_manager}' in {quarter_date}"
        }
        if analysis_type == 'class_breakdown':
            result.update({
                "aum_total": None,
                "stock_row_count": None,
                "stock_cusip_count": None,
                "top_class_labels": [],
                "top_class_counts": []
            })
        else:
            result.update({
                "total_aum": None,
                "stock_aum": None,
                "stock_holdings_count": None,
                "top_cusips": []
            })
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if analysis_type == 'class_breakdown':
        result = process_class_breakdown(data_dir, best_match, quarter_date)
    else:
        result = process_holdings_analysis(data_dir, best_match, quarter_date)

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