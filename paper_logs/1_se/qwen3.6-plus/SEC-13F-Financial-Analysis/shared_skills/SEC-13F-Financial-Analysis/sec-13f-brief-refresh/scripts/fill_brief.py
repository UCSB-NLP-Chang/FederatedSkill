#!/usr/bin/env python3
"""Orchestrate SEC 13F analysis to populate structured JSON briefs/templates."""
import csv
import json
import re
import sys
from collections import defaultdict

def normalize(s: str) -> str:
    return re.sub(r'[^\w\s]', '', s.lower()).strip()

def detect_value_unit(infotable_path: str, sample_manager: str) -> float:
    """Return multiplier (1.0 for dollars, 1000.0 for thousands) based on magnitude."""
    total = 0.0
    with open(infotable_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        val_col = 'VALUEUSD' if 'VALUEUSD' in reader.fieldnames else 'VALUE'
        for row in reader:
            total += float(row.get(val_col, 0))
    if total > 1e11:  # >$100B implies thousands
        return 1000.0
    return 1.0

def find_accession(coverpage_path: str, query: str) -> str:
    target = normalize(query)
    with open(coverpage_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            mgr = row.get('FILINGMANAGER_NAME') or row.get('MANAGER_NAME', '')
            if normalize(mgr) == target:
                return row.get('ACCESSION_NUMBER')
    return None

def aggregate_holdings(infotable_path: str, accession: str) -> dict:
    holdings = defaultdict(float)
    if not accession:
        return dict(holdings)
    with open(infotable_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        cusip_col = 'CUSIP'
        value_col = 'VALUEUSD' if 'VALUEUSD' in reader.fieldnames else 'VALUE'
        for row in reader:
            if row.get('ACCESSION_NUMBER') == accession:
                cusip = row.get(cusip_col, '').strip()
                if cusip:
                    holdings[cusip] += float(row.get(value_col, 0))
    return dict(holdings)

def fill_brief(template_path: str, baseline_dir: str, current_dir: str):
    with open(template_path, 'r') as f:
        template = json.load(f)

    # Detect unit from current quarter
    multiplier = detect_value_unit(f"{current_dir}/INFOTABLE.tsv", "VANGUARD")

    for section in template.get('sections', []):
        sid = section.get('section_id')
        if sid == 'fund_snapshots':
            for item in section['items']:
                acc = find_accession(f"{current_dir}/COVERPAGE.tsv", item['fund_query'])
                holdings = aggregate_holdings(f"{current_dir}/INFOTABLE.tsv", acc)
                item['aum'] = int(sum(holdings.values()) * multiplier)
                item['stock_holdings'] = len(holdings)
        elif sid == 'issuer_leaders':
            # Simplified: requires issuer_rollup logic; placeholder for routing
            pass
        elif sid == 'change_checks':
            for item in section['items']:
                bl_acc = find_accession(f"{baseline_dir}/COVERPAGE.tsv", item['fund_query'])
                cur_acc = find_accession(f"{current_dir}/COVERPAGE.tsv", item['fund_query'])
                bl_h = aggregate_holdings(f"{baseline_dir}/INFOTABLE.tsv", bl_acc)
                cur_h = aggregate_holdings(f"{current_dir}/INFOTABLE.tsv", cur_acc)
                deltas = {c: cur_h.get(c, 0) - bl_h.get(c, 0) for c in set(bl_h) | set(cur_h)}
                buys = sorted([c for c, d in deltas.items() if d > 0], key=lambda c: deltas[c], reverse=True)
                sells = sorted([c for c, d in deltas.items() if d < 0], key=lambda c: deltas[c])
                item['largest_buy_cusip'] = buys[0] if buys else ""
                item['largest_sell_cusip'] = sells[0] if sells else ""

    print(json.dumps(template, indent=2))

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: fill_brief.py <template.json> <baseline_dir> <current_dir>")
        sys.exit(1)
    fill_brief(sys.argv[1], sys.argv[2], sys.argv[3])
