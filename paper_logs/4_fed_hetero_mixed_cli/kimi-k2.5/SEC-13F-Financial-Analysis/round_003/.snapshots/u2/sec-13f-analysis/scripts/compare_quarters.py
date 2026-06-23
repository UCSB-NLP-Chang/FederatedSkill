#!/usr/bin/env python3
"""
Compare 13F holdings between two quarters for a specific manager.

Usage:
  python3 compare_quarters.py <dir_baseline> <date_baseline> <dir_current> <date_current> <manager_name> [--top-n 4]

Outputs JSON with top_increased, top_decreased, new_positions, and dropped_positions arrays of CUSIPs.
"""
import csv
import json
import sys
import os
import re
import argparse
from collections import defaultdict


def normalize_name(name):
    if not name:
        return ""
    name = name.lower().strip()
    for suffix in [' llc', ' inc', ' ltd', ' corp', ' lp', ' lllp', ' co',
                   ' advisory', ' management', ' group', ' partners']:
        name = name.replace(suffix, '')
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def find_manager(cover_path, quarter_date, query):
    norm_q = normalize_name(query)
    q_words = norm_q.split()
    with open(cover_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('REPORTCALENDARORQUARTER') != quarter_date:
                continue
            raw = row.get('FILINGMANAGER_NAME', '')
            norm = normalize_name(raw)
            if norm_q == norm or norm_q in norm or norm in norm_q:
                return row
            m_words = norm.split()
            if set(q_words) & set(m_words):
                return row
    return None


def is_stock_like(title):
    if not title:
        return False
    tokens = title.lower().split()
    inc = {'common', 'ordinary', 'share', 'shares', 'stock', 'com', 'shs', 'cl', 'class'}
    exc = {'bond', 'note', 'deb', 'etf', 'trust', 'fund', 'index', 'treas', 'muni',
           'pfd', 'pref', 'adr', 'ads', 'put', 'call', 'option', 'warrant', 'right'}
    return any(t in inc for t in tokens) and not any(t in exc for t in tokens)


def get_holdings(info_path, accession):
    cusip_vals = defaultdict(float)
    with open(info_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('ACCESSION_NUMBER') == accession and is_stock_like(row.get('TITLEOFCLASS', '')):
                cusip_vals[row['CUSIP']] += float(row.get('VALUE', 0) or 0)
    return cusip_vals


def main():
    parser = argparse.ArgumentParser(description='Compare 13F holdings between two quarters')
    parser.add_argument('dir_baseline')
    parser.add_argument('date_baseline')
    parser.add_argument('dir_current')
    parser.add_argument('date_current')
    parser.add_argument('manager_name')
    parser.add_argument('--top-n', type=int, default=4, help='Number of top entries to return')
    args = parser.parse_args()

    mgr_b = find_manager(os.path.join(args.dir_baseline, 'COVERPAGE.tsv'), args.date_baseline, args.manager_name)
    mgr_c = find_manager(os.path.join(args.dir_current, 'COVERPAGE.tsv'), args.date_current, args.manager_name)

    if not mgr_b or not mgr_c:
        print(json.dumps({
            "error": "Manager not found in one or both quarters",
            "baseline_found": bool(mgr_b),
            "current_found": bool(mgr_c)
        }, indent=2))
        sys.exit(1)

    h_b = get_holdings(os.path.join(args.dir_baseline, 'INFOTABLE.tsv'), mgr_b['ACCESSION_NUMBER'])
    h_c = get_holdings(os.path.join(args.dir_current, 'INFOTABLE.tsv'), mgr_c['ACCESSION_NUMBER'])

    all_cusips = set(h_b.keys()) | set(h_c.keys())
    deltas = []
    for c in all_cusips:
        v_b = h_b.get(c, 0.0)
        v_c = h_c.get(c, 0.0)
        deltas.append({"cusip": c, "baseline": v_b, "current": v_c, "change": v_c - v_b})

    deltas.sort(key=lambda x: x['change'], reverse=True)

    top_inc = [d['cusip'] for d in deltas if d['change'] > 0][:args.top_n]
    top_dec = [d['cusip'] for d in deltas if d['change'] < 0][:args.top_n]
    new_pos = [d['cusip'] for d in deltas if d['baseline'] == 0 and d['current'] > 0][:args.top_n]
    dropped = [d['cusip'] for d in deltas if d['baseline'] > 0 and d['current'] == 0][:args.top_n]

    print(json.dumps({
        "top_increased": top_inc,
        "top_decreased": top_dec,
        "new_positions": new_pos,
        "dropped_positions": dropped
    }, indent=2))


if __name__ == '__main__':
    main()
