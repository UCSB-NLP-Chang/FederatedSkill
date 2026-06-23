#!/usr/bin/env python3
"""
Compute reagent kit policy analysis comparing small-kit vs bulk-kit policies.
Handles JSON manifest with aliases, CSV overrides with revision logic, billing with effective_month selection.
"""
import argparse
import csv
import json
import os
from collections import defaultdict

def parse_manifest(path):
    """Load assay manifest, return list of assays with in_scope=True."""
    with open(path) as f:
        data = json.load(f)
    assays = []
    for region in data.get('regions', []):
        for assay in region.get('assays', []):
            if assay.get('in_scope', False):
                assays.append(assay)
    return assays

def build_alias_map(assays):
    """Map alias -> assay_id for billing matching."""
    alias_map = {}
    for assay in assays:
        code = assay['assay_id']
        alias_map[assay['assay_name']] = code
        for alias in assay.get('aliases', []):
            alias_map[alias] = code
    return alias_map

def resolve_labs(overrides_path, assay_ids, assays_by_id):
    """From overrides CSV, return dict assay_id -> active_labs (highest approved revision)."""
    rows = []
    with open(overrides_path, newline='') as f:
        for row in csv.DictReader(f):
            if row['assay_id'] in assay_ids and row['status'].lower() == 'approved':
                rows.append({
                    'assay_id': row['assay_id'],
                    'revision': int(row['revision']),
                    'active_labs': int(row['active_labs'])
                })
    by_id = defaultdict(list)
    for r in rows:
        by_id[r['assay_id']].append(r)
    result = {}
    for code, revs in by_id.items():
        best = max(revs, key=lambda x: x['revision'])
        result[code] = best['active_labs']
    # Fallback to default_active_labs
    for assay in assays_by_id.values():
        if assay['assay_id'] not in result:
            result[assay['assay_id']] = assay.get('default_active_labs', 0)
    return result

def load_carrier_costs(path):
    """Return dict carrier_type -> carrier_cost_usd."""
    costs = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            costs[row['carrier_type']] = float(row['carrier_cost_usd'])
    return costs

def load_billing(path, alias_map):
    """Return dict assay_id -> payment_per_run_per_lab_usd (latest active effective_month)."""
    records = []
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            label = row['assay_label']
            assay_id = alias_map.get(label)
            if assay_id and row['is_active'].lower() == 'true':
                records.append({
                    'assay_id': assay_id,
                    'effective_month': row['effective_month'],
                    'payment': float(row['payment_per_run_per_lab_usd'])
                })
    # Group by assay_id, pick latest effective_month
    by_id = defaultdict(list)
    for r in records:
        by_id[r['assay_id']].append(r)
    result = {}
    for code, recs in by_id.items():
        best = max(recs, key=lambda x: x['effective_month'])
        result[code] = best['payment']
    return result

def compute_annual(tests_per_run, runs_per_year, labs, price_per_1000, carrier_cost, payment):
    """Return (reagent_cost, carrier_cost_annual, revenue) for annual period."""
    # Reagent cost: tests per run × runs × labs × (price/1000)
    annual_reagent = tests_per_run * runs_per_year * labs * (price_per_1000 / 1000.0)
    # Carrier cost: carrier per run × runs × labs
    annual_carrier = carrier_cost * runs_per_year * labs
    # Revenue: payment per run × runs × labs
    annual_revenue = payment * runs_per_year * labs
    return annual_reagent, annual_carrier, annual_revenue

def main():
    parser = argparse.ArgumentParser(description='Compute reagent kit policy analysis')
    parser.add_argument('--manifest', required=True, help='Path to assay_manifest.json')
    parser.add_argument('--overrides', required=True, help='Path to lab_overrides.csv')
    parser.add_argument('--billing', required=True, help='Path to billing.csv')
    parser.add_argument('--carriers', required=True, help='Path to carrier_cost.csv')
    parser.add_argument('--runs-small', type=int, default=24, help='Runs per year for small-kit policy')
    parser.add_argument('--runs-bulk', type=int, default=12, help='Runs per year for bulk-kit policy')
    parser.add_argument('--threshold', type=float, default=7000, help='Decision threshold USD')
    parser.add_argument('--output-dir', default='.', help='Output directory')
    parser.add_argument('--label-small', default='small_kit', help='Label for small-kit policy')
    parser.add_argument('--label-bulk', default='bulk_kit', help='Label for bulk-kit policy')
    args = parser.parse_args()

    assays = parse_manifest(args.manifest)
    assay_ids = {a['assay_id'] for a in assays}
    assays_by_id = {a['assay_id']: a for a in assays}
    alias_map = build_alias_map(assays)
    labs = resolve_labs(args.overrides, assay_ids, assays_by_id)
    carrier_costs = load_carrier_costs(args.carriers)
    payments = load_billing(args.billing, alias_map)

    results = []
    total_margin_small = 0.0
    total_margin_bulk = 0.0

    for assay in assays:
        code = assay['assay_id']
        if code not in labs or labs[code] == 0:
            continue

        lab_count = labs[code]
        price = assay['reagent_price_per_1000_tests_usd']
        carrier_cost = carrier_costs.get(assay['carrier_type'], 0)
        payment = payments.get(code, 0)
        tests_small = assay['tests_per_run_small']
        tests_bulk = assay['tests_per_run_bulk']

        # Compute for both policies
        reagent_small, carrier_small, rev_small = compute_annual(
            tests_small, args.runs_small, lab_count, price, carrier_cost, payment
        )
        reagent_bulk, carrier_bulk, rev_bulk = compute_annual(
            tests_bulk, args.runs_bulk, lab_count, price, carrier_cost, payment
        )

        margin_small = rev_small - reagent_small - carrier_small
        margin_bulk = rev_bulk - reagent_bulk - carrier_bulk

        total_margin_small += margin_small
        total_margin_bulk += margin_bulk

        results.append({
            'assay_id': code,
            'assay_name': assay['assay_name'],
            'active_labs': lab_count,
            'reagent_price_per_1000_tests_usd': price,
            'carrier_type': assay['carrier_type'],
            'carrier_cost_usd': carrier_cost,
            'payment_per_run_per_lab_usd': payment,
            'tests_per_lab_per_run_small': tests_small,
            'tests_per_lab_per_run_bulk': tests_bulk,
            f'annual_reagent_cost_{args.label_small}_usd': reagent_small,
            f'annual_reagent_cost_{args.label_bulk}_usd': reagent_bulk,
            f'annual_carrier_cost_{args.label_small}_usd': carrier_small,
            f'annual_carrier_cost_{args.label_bulk}_usd': carrier_bulk,
            f'annual_revenue_{args.label_small}_usd': rev_small,
            f'annual_revenue_{args.label_bulk}_usd': rev_bulk,
            f'annual_margin_{args.label_small}_usd': margin_small,
            f'annual_margin_{args.label_bulk}_usd': margin_bulk,
            f'annual_margin_difference_{args.label_bulk}_minus_{args.label_small}_usd': margin_bulk - margin_small
        })

    abs_diff = abs(total_margin_bulk - total_margin_small)
    if total_margin_bulk > total_margin_small and abs_diff > args.threshold:
        decision = f'adopt_{args.label_bulk}'
    else:
        decision = f'keep_{args.label_small}'

    output = {
        'analysis': {
            'assumptions': {
                f'runs_per_year_{args.label_small}': args.runs_small,
                f'runs_per_year_{args.label_bulk}': args.runs_bulk,
                'switch_threshold_usd': args.threshold,
                'lab_override_rule': 'highest approved revision per assay_id, else default_active_labs',
                'billing_rule': 'latest active effective_month per assay'
            },
            'assays': results,
            'totals': {
                f'total_annual_margin_{args.label_small}_usd': total_margin_small,
                f'total_annual_margin_{args.label_bulk}_usd': total_margin_bulk,
                'absolute_difference_usd': abs_diff,
                'decision': decision
            }
        }
    }

    json_path = os.path.join(args.output_dir, 'reagent_policy_report.json')
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2)

    md_path = os.path.join(args.output_dir, 'reagent_policy_summary.md')
    with open(md_path, 'w') as f:
        f.write(f'Total {args.label_small.replace("_", "-")} annual margin: ${total_margin_small:,.2f}\n')
        f.write(f'Total {args.label_bulk.replace("_", "-")} annual margin: ${total_margin_bulk:,.2f}\n')
        f.write(f'Absolute margin difference: ${abs_diff:,.2f}\n')
        f.write(f'Decision: {decision}\n')

    print(f'JSON: {json_path}')
    print(f'Summary: {md_path}')
    print(f'Decision: {decision}')

if __name__ == '__main__':
    main()