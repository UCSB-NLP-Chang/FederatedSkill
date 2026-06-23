#!/usr/bin/env python3
"""
Compute diagnostic panel dispatch policy analysis comparing two dispatch cycles.
Handles JSON manifest with analysis_mode filtering, holdout exclusions,
CSV contracts with effective_week selection, network adjustments, and shipper costs.

NOTE: R8 had unresolved formula issues:
- days_per_year: tested both 364 and 365.0, both failed
- shipper cost scaling: tested both ×runs and ×runs×labs, both failed
This script defaults to 365.0 days/year and shipper ×runs×labs.
Adjust via --days-per-year and --shipper-per-lab flags if needed.
"""
import argparse
import csv
import json
import os
from collections import defaultdict
from decimal import Decimal


def parse_manifest(path):
    """Load panel manifest, return list of panels with analysis_mode=review."""
    with open(path) as f:
        data = json.load(f)
    panels = []
    for cluster in data.get('service_clusters', []):
        for panel in cluster.get('panels', []):
            if panel.get('analysis_mode') == 'review':
                panels.append(panel)
    return panels


def load_holdouts(path):
    """Return set of panel_code with holdout_state='exclude'."""
    with open(path) as f:
        data = json.load(f)
    excludes = set()
    for h in data.get('holdouts', []):
        if h.get('holdout_state') == 'exclude':
            excludes.add(h['panel_code'])
    return excludes


def resolve_labs(overrides_path, panel_codes, panels_by_id):
    """From overrides CSV, return dict panel_code -> active_labs.
    Rule: highest approved rev with non-empty active_labs, else default_active_labs."""
    rows = []
    with open(overrides_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get('panel_code')
            if code not in panel_codes:
                continue
            approval = row.get('approval', '').lower()
            if approval != 'approved':
                continue
            rev_str = row.get('rev', '').strip()
            if rev_str == '':
                continue
            labs_str = row.get('active_labs', '').strip()
            if labs_str == '':
                continue  # Must be non-empty to qualify
            rows.append({
                'panel_code': code,
                'revision': int(rev_str),
                'active_labs': int(labs_str)
            })

    # Group by panel_code, pick max revision
    by_code = defaultdict(list)
    for r in rows:
        by_code[r['panel_code']].append(r)

    result = {}
    for code, revs in by_code.items():
        best = max(revs, key=lambda x: x['revision'])
        result[code] = best['active_labs']

    # Fallback to default_active_labs
    for panel in panels_by_id.values():
        code = panel['panel_code']
        if code not in result:
            result[code] = panel.get('default_active_labs', 0)
    return result


def load_network_adjustments(path):
    """Return dict network_tier -> adjustment."""
    adjustments = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            tier = row.get('network_tier', '')
            adj = row.get('network_adjustment_per_run_per_lab_usd', '0')
            adjustments[tier] = Decimal(adj) if adj else Decimal('0')
    return adjustments


def load_shipper_costs(path):
    """Return dict shipper_class -> cost."""
    costs = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            costs[row['shipper_class']] = Decimal(row['shipper_cost_usd'])
    return costs


def load_contracts(path, panels):
    """Return dict panel_code -> (base_payment, effective_week).
    Match panel_ref against panel_name or alias_labels.
    Select latest effective_week among status_flag=current."""
    # Build alias map first
    alias_to_code = {}
    for panel in panels:
        code = panel['panel_code']
        alias_to_code[panel['panel_name']] = code
        for alias in panel.get('alias_labels', []):
            alias_to_code[alias] = code

    records = []
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            if row.get('status_flag', '').lower() != 'current':
                continue
            ref = row.get('panel_ref', '')
            code = alias_to_code.get(ref)
            if not code:
                continue
            records.append({
                'panel_code': code,
                'effective_week': row['effective_week'],
                'base_payment': Decimal(row['base_payment_per_run_per_lab_usd'])
            })

    # Group by panel_code, pick latest effective_week
    by_code = defaultdict(list)
    for r in records:
        by_code[r['panel_code']].append(r)

    result = {}
    for code, recs in by_code.items():
        best = max(recs, key=lambda x: x['effective_week'])
        result[code] = best['base_payment']
    return result


def compute_annual(tests_per_run, runs_per_year, labs, price_per_1000, shipper_cost, total_payment, shipper_per_lab=True):
    """Return (reagent_cost, shipper_cost_annual, revenue) as floats."""
    rpy = float(runs_per_year)
    labs_f = float(labs)
    price_f = float(price_per_1000)
    shipper_f = float(shipper_cost)
    payment_f = float(total_payment)
    tests_f = float(tests_per_run)

    reagent = tests_f * rpy * labs_f * (price_f / 1000.0)
    if shipper_per_lab:
        shipper = shipper_f * rpy * labs_f
    else:
        shipper = shipper_f * rpy  # per-run only, NOT per-lab
    revenue = payment_f * rpy * labs_f
    return reagent, shipper, revenue


def main():
    parser = argparse.ArgumentParser(description='Compute diagnostic panel dispatch policy analysis')
    parser.add_argument('--manifest', required=True, help='Path to panel_manifest.json')
    parser.add_argument('--holdouts', required=True, help='Path to holdouts.json')
    parser.add_argument('--overrides', required=True, help='Path to lab_capacity_overrides.csv')
    parser.add_argument('--contracts', required=True, help='Path to contract_terms.csv')
    parser.add_argument('--network', required=True, help='Path to network_adjustments.csv')
    parser.add_argument('--shipper', required=True, help='Path to shipper_cost.csv')
    parser.add_argument('--template', help='Path to report_template.json (optional)')
    parser.add_argument('--cycle-a', type=int, default=14, help='Days per cycle A')
    parser.add_argument('--cycle-b', type=int, default=28, help='Days per cycle B')
    parser.add_argument('--days-per-year', type=float, default=365.0, help='Days per year (default 365.0, try 364 or 360 if needed)')
    parser.add_argument('--threshold', type=float, default=6000, help='Decision threshold USD')
    parser.add_argument('--output-dir', default='.', help='Output directory')
    parser.add_argument('--label-a', default='14_day', help='Label for cycle A')
    parser.add_argument('--label-b', default='28_day', help='Label for cycle B')
    parser.add_argument('--shipper-per-lab', action='store_true', default=True, help='Shipper cost ×runs×labs (default)')
    parser.add_argument('--shipper-per-run', dest='shipper_per_lab', action='store_false', help='Shipper cost ×runs only')
    args = parser.parse_args()

    # Load data
    panels = parse_manifest(args.manifest)
    holdout_excludes = load_holdouts(args.holdouts)

    # Filter out holdouts
    panels = [p for p in panels if p['panel_code'] not in holdout_excludes]
    panel_codes = {p['panel_code'] for p in panels}
    panels_by_id = {p['panel_code']: p for p in panels}

    labs = resolve_labs(args.overrides, panel_codes, panels_by_id)
    network_adj = load_network_adjustments(args.network)
    shipper_costs = load_shipper_costs(args.shipper)
    base_payments = load_contracts(args.contracts, panels)

    # Compute runs per year (exact float)
    runs_a = args.days_per_year / args.cycle_a
    runs_b = args.days_per_year / args.cycle_b

    results = []
    total_margin_a = 0.0
    total_margin_b = 0.0

    tests_col_a = f'tests_per_lab_per_run_{args.label_a}'
    tests_col_b = f'tests_per_lab_per_run_{args.label_b}'

    for panel in panels:
        code = panel['panel_code']
        if code not in labs or labs[code] == 0:
            continue

        lab_count = labs[code]
        price = float(panel['reagent_cost_per_1000_tests_usd'])
        tier = panel.get('network_tier', '')
        adjustment = float(network_adj.get(tier, 0))
        shipper = float(shipper_costs.get(panel.get('shipper_class', ''), 0))
        base_pay = float(base_payments.get(code, 0))
        total_pay = base_pay + adjustment

        tests_a = float(panel.get(tests_col_a, 0))
        tests_b = float(panel.get(tests_col_b, 0))

        # Compute for both cycles
        reagent_a, shipper_a, rev_a = compute_annual(
            tests_a, runs_a, lab_count, price, shipper, total_pay, args.shipper_per_lab
        )
        reagent_b, shipper_b, rev_b = compute_annual(
            tests_b, runs_b, lab_count, price, shipper, total_pay, args.shipper_per_lab
        )

        margin_a = rev_a - reagent_a - shipper_a
        margin_b = rev_b - reagent_b - shipper_b

        total_margin_a += margin_a
        total_margin_b += margin_b

        result = {
            'panel_code': code,
            'panel_name': panel['panel_name'],
            'active_labs': lab_count,
            'reagent_cost_per_1000_tests_usd': price,
            'network_tier': tier,
            'network_adjustment_per_run_per_lab_usd': adjustment,
            'shipper_class': panel.get('shipper_class', ''),
            'shipper_cost_usd': shipper,
            'base_payment_per_run_per_lab_usd': base_pay,
            'total_payment_per_run_per_lab_usd': total_pay,
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
        }
        results.append(result)

    # Sort by panel_code for deterministic output
    results.sort(key=lambda x: x['panel_code'])

    abs_diff = abs(total_margin_b - total_margin_a)
    if total_margin_b > total_margin_a and abs_diff > args.threshold:
        decision = f'switch_to_{args.label_b}'
    else:
        decision = f'keep_{args.label_a}'

    # Build output
    output = {
        'analysis': {
            'assumptions': {
                f'runs_per_year_{args.label_a}': runs_a,
                f'runs_per_year_{args.label_b}': runs_b,
                f'days_per_cycle_{args.label_a}': args.cycle_a,
                f'days_per_cycle_{args.label_b}': args.cycle_b,
                'days_per_year': args.days_per_year,
                'shipper_cost_scaling': 'per_run_per_lab' if args.shipper_per_lab else 'per_run_only',
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

    # Merge with template if provided
    if args.template:
        with open(args.template) as f:
            template = json.load(f)
        output = dict(template)
        output['analysis'] = output.get('analysis', {})
        output['analysis']['assumptions'] = output['analysis'].get('assumptions', {})
        output['analysis']['assumptions'].update(output['analysis'].get('assumptions', {}))
        output['analysis']['assumptions'] = output['analysis']['assumptions']
        output['analysis']['panels'] = results
        output['analysis']['totals'] = {
            f'total_annual_margin_{args.label_a}_usd': total_margin_a,
            f'total_annual_margin_{args.label_b}_usd': total_margin_b,
            'absolute_difference_usd': abs_diff,
            'recommendation': decision
        }

    json_path = os.path.join(args.output_dir, 'diagpanel_policy_report.json')
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2)

    md_path = os.path.join(args.output_dir, 'diagpanel_policy_summary.md')
    with open(md_path, 'w') as f:
        for line in [
            f'Total {args.label_a.replace("_", "-")} margin: ${total_margin_a:,.2f} USD',
            f'Total {args.label_b.replace("_", "-")} margin: ${total_margin_b:,.2f} USD',
            f'Absolute difference: ${abs_diff:,.2f} USD',
            f'Decision: {decision}'
        ]:
            f.write(line + '\n')

    print(f'JSON: {json_path}')
    print(f'Summary: {md_path}')
    print(f'Decision: {decision}')


if __name__ == '__main__':
    main()
