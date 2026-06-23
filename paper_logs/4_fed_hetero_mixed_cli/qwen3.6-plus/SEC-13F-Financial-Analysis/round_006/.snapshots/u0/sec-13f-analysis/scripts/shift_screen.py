#!/usr/bin/env python3
"""
SEC 13F Cross-Quarter Shift Screening

Compares holdings between two quarters to identify increased, decreased,
and new positions.

Usage:
  python3 shift_screen.py <current_dir> <baseline_dir> <manager_name> <current_quarter_date> <baseline_quarter_date>

Output JSON to stdout with top increased, decreased, and new positions.
"""
import csv
import json
import sys
import os
import re
import difflib
import argparse
from collections import defaultdict


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


def word_overlap_score(query_norm, candidate_norm):
    """Calculate word overlap between normalized names using Jaccard."""
    stop_words = {'the', 'and', 'of', 'associates', 'group', 'capital',
                  'partners', 'management', 'advisory', 'investment'}
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

    # Step 1: Exact normalized match
    for m in managers:
        raw = m.get('FILINGMANAGER_NAME', '')
        norm = normalize_name(raw)
        if norm_query == norm:
            return m

    # Step 2: Substring match
    for m in managers:
        raw = m.get('FILINGMANAGER_NAME', '')
        norm = normalize_name(raw)
        if norm_query in norm or norm in norm_query:
            return m

    # Step 3: Word overlap (Jaccard >= 0.3)
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

    # Step 4: Fuzzy match (> 0.85 threshold)
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
    exclude = {'bond', 'note', 'deb', 'etf', 'trust', 'fund', 'index', 'treas', 'muni',
               'pfd', 'pref', 'adr', 'put', 'call', 'option', 'warrant', 'right'}
    has_include = any(t in include for t in tokens)
    has_exclude = any(t in exclude for t in tokens)
    return has_include and not has_exclude


def load_holdings(data_dir, quarter_date, manager_name):
    """Load stock holdings for a specific manager and quarter."""
    cover_path = os.path.join(data_dir, 'COVERPAGE.tsv')
    info_path = os.path.join(data_dir, 'INFOTABLE.tsv')

    # Find manager
    managers = []
    with open(cover_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('REPORTCALENDARORQUARTER') == quarter_date:
                managers.append(row)

    match = find_best_manager(managers, manager_name)
    if not match:
        return None, None

    accession = match['ACCESSION_NUMBER']
    matched_name = match.get('FILINGMANAGER_NAME', '')

    # Load holdings
    holdings = []
    with open(info_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('ACCESSION_NUMBER') == accession:
                holdings.append(row)

    # Filter to stocks and build CUSIP -> Value map (preserve CUSIP case)
    cusip_values = {}
    for h in holdings:
        if is_stock_like(h.get('TITLEOFCLASS', '')):
            cusip = h.get('CUSIP', '')
            value = float(h.get('VALUE', 0) or 0)
            if cusip:
                cusip_values[cusip] = value

    return matched_name, cusip_values


def compare_quarters(current_dir, baseline_dir, manager_name, current_q, baseline_q):
    """Compare holdings between two quarters."""
    current_name, current_holdings = load_holdings(current_dir, current_q, manager_name)
    baseline_name, baseline_holdings = load_holdings(baseline_dir, baseline_q, manager_name)

    if current_holdings is None:
        return {
            "manager": None,
            "error": f"Manager not found in current quarter {current_q}",
            "fund_query_current": manager_name,
            "quarter_current": current_q,
            "fund_query_baseline": manager_name,
            "quarter_baseline": baseline_q,
            "top4_increased_cusips": [],
            "top3_decreased_cusips": [],
            "new_positions_top2": []
        }
    if baseline_holdings is None:
        return {
            "manager": None,
            "error": f"Manager not found in baseline quarter {baseline_q}",
            "fund_query_current": manager_name,
            "quarter_current": current_q,
            "fund_query_baseline": manager_name,
            "quarter_baseline": baseline_q,
            "top4_increased_cusips": [],
            "top3_decreased_cusips": [],
            "new_positions_top2": []
        }

    # Calculate differences for CUSIPs in both quarters (INCREASED and DECREASED)
    increased = []
    decreased = []

    for cusip, curr_val in current_holdings.items():
        if cusip in baseline_holdings:
            base_val = baseline_holdings[cusip]
            diff = curr_val - base_val
            if diff > 0:
                increased.append((cusip, diff, curr_val))
            elif diff < 0:
                decreased.append((cusip, abs(diff), curr_val))

    # Sort by absolute difference (descending)
    increased.sort(key=lambda x: x[1], reverse=True)
    decreased.sort(key=lambda x: x[1], reverse=True)

    # New positions (in current, NOT in baseline)
    new_positions = []
    for cusip, curr_val in current_holdings.items():
        if cusip not in baseline_holdings:
            new_positions.append((cusip, curr_val))
    new_positions.sort(key=lambda x: x[1], reverse=True)

    return {
        "manager": current_name,
        "fund_query_current": manager_name,
        "quarter_current": current_q,
        "fund_query_baseline": manager_name,
        "quarter_baseline": baseline_q,
        "current_holdings_count": len(current_holdings),
        "baseline_holdings_count": len(baseline_holdings),
        "top4_increased_cusips": [c[0] for c in increased[:4]],
        "top3_decreased_cusips": [c[0] for c in decreased[:3]],
        "new_positions_top2": [c[0] for c in new_positions[:2]]
    }


def main():
    parser = argparse.ArgumentParser(description='Compare 13F holdings between two quarters')
    parser.add_argument('current_dir', help='Directory containing current quarter TSV files')
    parser.add_argument('baseline_dir', help='Directory containing baseline quarter TSV files')
    parser.add_argument('manager_name', help='Manager name to search for')
    parser.add_argument('current_quarter_date', help='Current quarter date (e.g., 30-SEP-2025)')
    parser.add_argument('baseline_quarter_date', help='Baseline quarter date (e.g., 30-JUN-2025)')
    args = parser.parse_args()

    result = compare_quarters(
        args.current_dir,
        args.baseline_dir,
        args.manager_name,
        args.current_quarter_date,
        args.baseline_quarter_date
    )
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
