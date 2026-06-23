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
from collections import Counter

# Stock classification tokens
STOCK_INCLUDE = {'common', 'com', 'ordinary', 'shares', 'shs', 'stock', 'class', 'cl'}
STOCK_EXCLUDE = {'etf', 'put', 'call', 'option', 'bond', 'note', 'preferred', 'pfd', 'adr', 'trust', 'fund', 'index', 'deb', 'treas', 'muni'}

LEGAL_SUFFIXES = [' llc', ' inc', ' ltd', ' corp', ' lp', ' lllp', ' co', ' advisory', ' management', ' group', ' partners']

STOP_WORDS = {'the', 'and', 'of', 'associates', 'group', 'capital', 'partners', 'management', 'advisory', 'investment'}


def normalize_name(name):
    """Normalize manager name for matching."""
    if not name:
        return ""
    name = name.lower().strip()
    for suffix in LEGAL_SUFFIXES:
        name = name.replace(suffix, '')
    name = re.sub(r'[^\w\s]', ' ', name)
    return re.sub(r'\s+', ' ', name).strip()


def is_stock_like(title):
    """Determine if TITLEOFCLASS indicates a stock holding using tokenized matching."""
    if not title:
        return False
    tokens = title.lower().split()
    has_include = any(t in STOCK_INCLUDE for t in tokens)
    has_exclude = any(t in STOCK_EXCLUDE for t in tokens)
    return has_include and not has_exclude


def word_overlap_score(query_norm, candidate_norm):
    """Calculate word overlap (Jaccard) between normalized names."""
    query_words = set(query_norm.split()) - STOP_WORDS
    candidate_words = set(candidate_norm.split()) - STOP_WORDS
    if not query_words or not candidate_words:
        return 0.0
    intersection = query_words & candidate_words
    union = query_words | candidate_words
    return len(intersection) / len(union)


def match_manager(managers, query_manager, threshold=0.85):
    """
    Match manager name with tiered matching strategy.
    Returns matched row or None if no match.
    """
    norm_query = normalize_name(query_manager)

    # 1. Exact match
    for m in managers:
        raw_name = m.get('FILINGMANAGER_NAME', '')
        if normalize_name(raw_name) == norm_query:
            return m

    # 2. Substring match (query in manager or manager in query)
    for m in managers:
        raw_name = m.get('FILINGMANAGER_NAME', '')
        norm_name = normalize_name(raw_name)
        if norm_query in norm_name or norm_name in norm_query:
            return m

    # 3. Word-level match (shared words between query and manager)
    best_overlap = 0
    overlap_match = None
    for m in managers:
        raw_name = m.get('FILINGMANAGER_NAME', '')
        norm_name = normalize_name(raw_name)
        score = word_overlap_score(norm_query, norm_name)
        if score > best_overlap:
            best_overlap = score
            overlap_match = m
    if best_overlap >= 0.3:
        return overlap_match

    # 4. Fuzzy match with high threshold only
    candidates = []
    for m in managers:
        raw_name = m.get('FILINGMANAGER_NAME', '')
        norm_name = normalize_name(raw_name)
        ratio = difflib.SequenceMatcher(None, norm_query, norm_name).ratio()
        if ratio > threshold:
            candidates.append((ratio, m))

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]

    return None


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
    top_cusips = [h.get('CUSIP', '') for h in stock_holdings[:3]]

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
    """Process SEC 13F filing and extract metrics."""
    cover_path = os.path.join(data_dir, 'COVERPAGE.tsv')
    info_path = os.path.join(data_dir, 'INFOTABLE.tsv')

    if not os.path.exists(cover_path):
        result = {"error": f"COVERPAGE.tsv not found in {data_dir}", "manager": None}
        print(json.dumps(result, indent=2))
        sys.exit(1)
    if not os.path.exists(info_path):
        result = {"error": f"INFOTABLE.tsv not found in {data_dir}", "manager": None}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    # Filter managers by quarter
    managers = []
    with open(cover_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('REPORTCALENDARORQUARTER') == quarter_date:
                managers.append(row)

    if not managers:
        result = {"error": f"No filings found for quarter '{quarter_date}'", "manager": None}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    # Match manager
    matched = match_manager(managers, query_manager)

    if not matched:
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
        result = process_class_breakdown(data_dir, matched, quarter_date)
    else:
        result = process_holdings_analysis(data_dir, matched, quarter_date)

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: process_13f.py <data_dir> <manager_name> <quarter_date> [--analysis-type {holdings|class_breakdown}]")
        print("Example: process_13f.py 2025-q3 'Renaissance Technologies' '30-SEP-2025'")
        sys.exit(1)

    data_dir = sys.argv[1]
    manager_name = sys.argv[2]
    quarter_date = sys.argv[3]
    analysis_type = 'holdings'

    if len(sys.argv) > 4:
        if sys.argv[4] == '--analysis-type' and len(sys.argv) > 5:
            analysis_type = sys.argv[5]
        elif sys.argv[4].startswith('--analysis-type='):
            analysis_type = sys.argv[4].split('=')[1]

    process_13f(data_dir, manager_name, quarter_date, analysis_type)
