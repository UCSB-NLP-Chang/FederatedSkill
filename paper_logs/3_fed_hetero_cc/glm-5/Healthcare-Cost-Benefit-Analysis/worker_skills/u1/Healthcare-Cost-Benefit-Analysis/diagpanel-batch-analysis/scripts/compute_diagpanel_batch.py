#!/usr/bin/env python3
"""
Compute diagnostic panel batch analysis comparing two replenishment cadences.
Handles JSON manifest with analysis_mode filtering, holdout exclusions,
CSV contracts with effective_week selection, network adjustments, and shipper costs.
"""
import argparse
import csv
import json
import os
from collections import defaultdict


def parse_manifest(path):
    """Load panel manifest, return list of panels with analysis_mode=review."""
    with open(path) as f:
        data = json.load(f)
    panels = []
    for cluster in data.get('service_clusters', []):
        for p in cluster.get('panels', []):
            if p.get('analysis_mode', '').lower() == 'review':
                panels.append(p)
    return panels


def load_holdouts(path):
    """Return set of panel_codes with holdout_state=exclude."""
    with open(path) as f:
        data = json.load(f)
    return {
        h['panel_code']
        for h in data.get('holdouts', [])
        if h.get('holdout_state', '').lower() == 'exclude'
    }


def build_alias_map(panels):
    """Map alias/panel_name (case-insensitive) -> panel_code."""
    alias_map = {}
    for p in panels:
        code = p['panel_code']
        alias_map[p['panel_name'].lower()] = code
        for alias in p.get('alias_labels', []):
            alias_map[alias.lower()] = code
    return alias_map


def resolve_contracts(path, alias_map):
    """Return dict panel_code -> base_payment (latest effective_week among current)."""
    records = []
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            if row['status_flag'].lower() != 'current':
                continue
            ref = row['panel_ref'].lower()
            code = alias_map.get(ref)
            if code:
                records.append({
                    'code': code,
                    'effective_week': row['effective_week'],
                    'payment': float(row['base_payment_per_run_per_lab_usd'])
                })
    by_code = defaultdict(list)
    for r in records:
        by_code[r['code']].append(r)
    result = {}
    for code, recs in by_code.items():
        def week_key(r):
            w = r['effective_week']
            parts = w.split('-W')
            return (int(parts[0]), int(parts[1]))
        best = max(recs, key=week_key)
        result[code] = best['payment']
    return result


def load_network_adjustments(path):
    """Return dict network_tier -> adjustment."""
    adj = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            adj[row['network_tier']] = float(row['network_adjustment_per_run_per_lab_usd'])
    return adj


def load_shipper_costs(path):
    """Return dict shipper_class -> shipper_cost_usd."""
    costs = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            costs[row['shipper_class']] = float(row['shipper_cost_usd'])
    return costs


def resolve_labs(overrides_path, panel_codes, panels_by_id):
    """Return dict panel_code -> active_labs (highest approved rev with non-empty labs)."""
    rows = []
    with open(overrides_path, newline='') as f:
        for row in csv.DictReader(f):
            if row['panel_code'] not in panel_codes:
                continue
            if row['approval'].lower() != 'approved':
                continue
            rev_str = row['rev'].strip()
            labs_str = row['active_labs'].strip()
            if rev_str == '' or labs_str == '':
                continue
            rows.append({
                'code': row['panel_code'],
                'rev': int(rev_str),
                'labs': int(labs_str)
            })
    by_code = defaultdict(list)
    for r in rows:
        by_code[r['code']].append(r)
    result = {}
    for code, revs in by_code.items():
        best = max(revs, key=lambda x: x['rev'])
        result[code] = best['labs']
    for code in panel_codes:
        if code not in result:
            result[code] = panels_by_id[code].get('default_active_labs', 0)
    return result


def compute_annual(tests_per_run, runs, labs, price_per_1000, shipper_cost, total_payment):
    """Return (reagent_cost, shipper_cost_annual, revenue) as floats."""
    annual_reagent = tests_per_run * runs * labs * (price_per_1000 / 1000.0)
    annual_shipper = shipper_cost * runs * labs
    annual_revenue = total_payment * runs * labs
    return annual_reagent, annual_shipper, annual_revenue


def main():
    parser = argparse.ArgumentParser(description='Compute diagnostic panel batch analysis')
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--holdouts', required=True)
    parser.add_argument('--contracts', required=True)
    parser.add_argument('--network', required=True)
    parser.add_argument('--shipper', required=True)
    parser.add_argument('--overrides', required=True)
    parser.add_argument('--template', help='Report template JSON to preserve metadata')
    parser.add_argument('--cycle-a', type=int, default=14)
    parser.add_argument('--cycle-b', type=int, default=28)
    parser.add_argument('--threshold', type=float, default=6000)
    parser.add_argument('--output-dir', default='.')
    parser.add_argument('--label-a', default='14_day')
    parser.add_argument('--label-b', default='28_day')
    args = parser.parse_args()

    panels = parse_manifest(args.manifest)
    exclude_codes = load_holdouts(args.holdouts)
    panels = [p for p in panels if p['panel_code'] not in exclude_codes]
    panel_codes = {p['panel_code'] for p in panels}
    panels_by_id = {p['panel_code']: p for p in panels}
    alias_map = build_alias_map(panels)
    contracts = resolve_contracts(args.contracts, alias_map)
    network_adj = load_network_adjustments(args.network)
    shipper_costs = load_shipper_costs(args.shipper)
    labs = resolve_labs(args.overrides, panel_codes, panels_by_id)

    days_per_year = 365.0
    runs_a = days_per_year / args.cycle_a
    runs_b = days_per_year / args.cycle_b

    results = []
    total_margin_a = 0.0
    total_margin_b = 0.0

    tests_col_a = f'tests_per_lab_per_run_{args.label_a}'
    tests_col_b = f'tests_per_lab_per_run_{args.label_b}'

    for p in panels:
        code = p['panel_code']
        lab_count = labs.get(code, 0)
        if lab_count == 0:
            continue

        price = p['reagent_cost_per_1000_tests_usd']
        shipper_cost = shipper_costs.get(p.get('shipper_class', ''), 0)
        base_payment = contracts.get(code, 0)
        net_adj = network_adj.get(p.get('network_tier', ''), 0.0)
        total_payment = base_payment + net_adj

        tests_a = p.get(tests_col_a, 0)
        tests_b = p.get(tests_col_b, 0)

        reagent_a, shipper_a, rev_a = compute_annual(tests_a, runs_a, lab_count, price, shipper_cost, total_payment)
        reagent_b, shipper_b, rev_b = compute_annual(tests_b, runs_b, lab_count, price, shipper_cost, total_payment)

        margin_a = rev_a - reagent_a - shipper_a
        margin_b = rev_b - reagent_b - shipper_b

        total_margin_a += margin_a
        total_margin_b += margin_b

        results.append({
            'panel_code': code,
            'panel_name': p['panel_name'],
            'active_labs': lab_count,
            'reagent_cost_per_1000_tests_usd': price,
            'network_tier': p.get('network_tier', ''),
            'network_adjustment_per_run_per_lab_usd': net_adj,
            'shipper_class': p.get('shipper_class', ''),
            'shipper_cost_usd': shipper_cost,
            'base_payment_per_run_per_lab_usd': base_payment,
            'total_payment_per_run_per_lab_usd': total_payment,
            tests_col_a: tests_a,
            tests_col_b: tests_b,
            f'annual_reagent_cost_{args.label_a}_usd': reagent_a,
            f'annual_reagent_cost_{args.label_b}_usd': reagent_b,
            f'annual_shipper_cost_{args.label_a}_usd': shipper_a,
            f'annual_shipper_cost_{args.label_b}_usd': shipper_b,
            f'annual_revenue_{args.label_a}_usd': rev_a,
            f'annual_revenue_{args.label_b}_usd': rev_b,
            f'annual_margin_{args.label_a}_usd': margin_a,
            f'annual_margin_{args.label_b}_usd': margin_b,
            f'annual_margin_difference_{args.label_b}_minus_{args.label_a}_usd': margin_b - margin_a
        })

    results.sort(key=lambda x: x['panel_code'])

    abs_diff = abs(total_margin_b - total_margin_a)
    if total_margin_b > total_margin_a and abs_diff > args.threshold:
        decision = f'switch_to_{args.label_b}'
    else:
        decision = f'keep_{args.label_a}'

    output = {
        'analysis': {
            'assumptions': {
                f'runs_per_year_{args.label_a}': runs_a,
                f'runs_per_year_{args.label_b}': runs_b,
                'days_per_year': days_per_year,
                'switch_threshold_usd': args.threshold,
                'override_rule': 'highest approved rev with non-empty active_labs, else default_active_labs',
                'holdout_rule': 'exclude holdout_state=exclude',
                'billing_rule': 'latest effective_week among status_flag=current, matched by alias_labels'
            },
            'panels': results,
            'totals': {
                f'total_annual_margin_{args.label_a}_usd': total_margin_a,
                f'total_annual_margin_{args.label_b}_usd': total_margin_b,
                'absolute_difference_usd': abs_diff,
                'recommendation': decision
            }
        }
    }

    if args.template:
        with open(args.template) as f:
            template = json.load(f)
        if 'metadata' in template:
            output['metadata'] = template['metadata']
        if 'audit_notes' in template:
            output['audit_notes'] = template['audit_notes']

    json_path = os.path.join(args.output_dir, 'diagpanel_policy_report.json')
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2)

    md_path = os.path.join(args.output_dir, 'diagpanel_policy_summary.md')
    with open(md_path, 'w') as f:
        f.write(f'Regional Diagnostics Network Panel Policy Evaluation\n')
        f.write(f'Retained panels (analysis_mode=review, excluding holdouts): {len(results)}\n')
        f.write(f'Total {args.label_a.replace("_", "-")} annual margin: ${total_margin_a:,.2f} USD\n')
        f.write(f'Total {args.label_b.replace("_", "-")} annual margin: ${total_margin_b:,.2f} USD\n')
        f.write(f'Absolute margin difference ({args.label_b} vs {args.label_a}): ${abs_diff:,.2f} USD\n')
        f.write(f'Decision threshold: ${args.threshold:,.2f} USD\n')
        f.write(f'Recommendation: {decision}\n')

    print(f'JSON: {json_path}')
    print(f'Summary: {md_path}')
    print(f'Decision: {decision}')


if __name__ == '__main__':
    main()
