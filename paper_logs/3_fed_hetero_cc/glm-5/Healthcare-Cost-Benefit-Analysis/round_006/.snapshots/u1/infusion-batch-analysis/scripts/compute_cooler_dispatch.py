#!/usr/bin/env python3
"""
Compute oncology cooler dispatch analysis comparing two dispatch cycle lengths.
Handles JSON program catalog with review flags, CSV site overrides with version control,
and exact day-based calculations. Supports configurable days_per_year (commonly 360).
"""
import argparse
import csv
import json
import os
from collections import defaultdict


def parse_catalog(path):
    """Load program catalog, return list of programs with review_flag='review'."""
    with open(path) as f:
        data = json.load(f)
    programs = []
    for sg in data.get('service_groups', []):
        for p in sg.get('programs', []):
            if p.get('review_flag') == 'review':
                programs.append(p)
    return programs


def build_label_map(programs):
    """Map label (case-insensitive) -> program_code."""
    label_map = {}
    for p in programs:
        code = p['program_code']
        for lbl in p.get('known_labels', []):
            label_map[lbl.lower()] = code
        # Also map program_name as label
        label_map[p['program_name'].lower()] = code
    return label_map


def resolve_sites(overrides_path, program_codes, default_sites_map):
    """
    From overrides CSV, return dict program_code -> active_sites.
    Select highest approved version_no per program_code.
    If no approved override exists, fallback to default_active_sites from catalog.
    """
    rows = []
    with open(overrides_path, newline='') as f:
        for row in csv.DictReader(f):
            code = row['program_code']
            if code in program_codes and row['approval_state'].lower() == 'approved':
                rows.append({
                    'program_code': code,
                    'version_no': int(row['version_no']),
                    'active_sites': int(row['active_sites'])
                })
    # Group by program_code, pick max version_no
    by_code = defaultdict(list)
    for r in rows:
        by_code[r['program_code']].append(r)
    result = {}
    for code in program_codes:
        if code in by_code and by_code[code]:
            best = max(by_code[code], key=lambda x: x['version_no'])
            result[code] = best['active_sites']
        else:
            # Fallback to default_active_sites
            result[code] = default_sites_map.get(code, 0)
    return result


def load_cooler_costs(path):
    """Return dict cooler_type -> cooler_cost_usd."""
    costs = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            costs[row['cooler_type']] = float(row['cooler_cost_usd'])
    return costs


def load_payments(path, label_map):
    """Return dict program_code -> payment_per_dispatch_per_site_usd."""
    payments = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            lbl = row['program_label'].lower()
            code = label_map.get(lbl)
            if code:
                payments[code] = float(row['payment_per_dispatch_per_site_usd'])
    return payments


def compute_annual(price_per_1000, units_per_day, days_per_year, sites,
                   cooler_cost, payment, cycle_days):
    """
    Return (drug_cost, cooler_cost, revenue) for annual period.
    Cooler cost is per-dispatch, NOT per-site.
    """
    # Dispatches per year (exact float)
    dispatches = days_per_year / cycle_days

    # Annual drug cost: (price/1000) × units/day × days/year × sites
    annual_drug = (price_per_1000 / 1000.0) * units_per_day * days_per_year * sites

    # Annual cooler cost: cooler_cost × dispatches (NOT × sites)
    annual_cooler = cooler_cost * dispatches

    # Annual revenue: payment × dispatches × sites
    annual_revenue = payment * dispatches * sites

    return annual_drug, annual_cooler, annual_revenue


def main():
    parser = argparse.ArgumentParser(description='Compute oncology cooler dispatch analysis')
    parser.add_argument('--catalog', required=True, help='Path to program_catalog.json')
    parser.add_argument('--overrides', required=True, help='Path to site_overrides.csv')
    parser.add_argument('--cooler-costs', required=True, help='Path to cooler_cost.csv')
    parser.add_argument('--payments', required=True, help='Path to contract_payment.csv')
    parser.add_argument('--cycle-a', type=int, default=10, help='Days per dispatch cycle A')
    parser.add_argument('--cycle-b', type=int, default=20, help='Days per dispatch cycle B')
    parser.add_argument('--days-per-year', type=float, default=360.0,
                        help='Days per year for drug costing (commonly 360 or 365)')
    parser.add_argument('--threshold', type=float, default=10000.0, help='Decision threshold USD')
    parser.add_argument('--output-dir', default='.', help='Output directory')
    parser.add_argument('--label-a', default='10_day', help='Label for cycle A')
    parser.add_argument('--label-b', default='20_day', help='Label for cycle B')
    args = parser.parse_args()

    # Load data
    programs = parse_catalog(args.catalog)
    program_codes = {p['program_code'] for p in programs}
    label_map = build_label_map(programs)

    # Build default_sites_map from catalog
    default_sites_map = {p['program_code']: p.get('default_active_sites', 0) for p in programs}

    sites = resolve_sites(args.overrides, program_codes, default_sites_map)
    cooler_costs = load_cooler_costs(args.cooler_costs)
    payments = load_payments(args.payments, label_map)

    results = []
    total_margin_a = 0.0
    total_margin_b = 0.0

    for p in programs:
        code = p['program_code']
        active_sites = sites.get(code, 0)
        price = p['acquisition_cost_per_1000_units_usd']
        units = p['units_per_day']
        cooler_type = p['cooler_type']
        cooler_cost = cooler_costs.get(cooler_type, 0)
        payment = payments.get(code, 0)

        # Compute for both cycles
        drug_a, cooler_a, rev_a = compute_annual(
            price, units, args.days_per_year, active_sites,
            cooler_cost, payment, args.cycle_a
        )
        drug_b, cooler_b, rev_b = compute_annual(
            price, units, args.days_per_year, active_sites,
            cooler_cost, payment, args.cycle_b
        )

        margin_a = rev_a - drug_a - cooler_a
        margin_b = rev_b - drug_b - cooler_b

        total_margin_a += margin_a
        total_margin_b += margin_b

        results.append({
            'program_code': code,
            'program_name': p['program_name'],
            'active_sites': active_sites,
            'acquisition_cost_per_1000_units_usd': price,
            'units_per_day': units,
            'cooler_type': cooler_type,
            'cooler_cost_usd': cooler_cost,
            'payment_per_dispatch_per_site_usd': payment,
            f'annual_drug_cost_{args.label_a}_usd': drug_a,
            f'annual_drug_cost_{args.label_b}_usd': drug_b,
            f'annual_cooler_cost_{args.label_a}_usd': cooler_a,
            f'annual_cooler_cost_{args.label_b}_usd': cooler_b,
            f'annual_revenue_{args.label_a}_usd': rev_a,
            f'annual_revenue_{args.label_b}_usd': rev_b,
            f'annual_margin_{args.label_a}_usd': margin_a,
            f'annual_margin_{args.label_b}_usd': margin_b,
            f'annual_margin_difference_{args.label_b}_minus_{args.label_a}_usd': margin_b - margin_a
        })

    abs_diff = abs(total_margin_b - total_margin_a)
    if total_margin_b > total_margin_a and abs_diff > args.threshold:
        decision = f'switch_to_{args.label_b}'
    else:
        decision = f'keep_{args.label_a}'

    # Write JSON
    output = {
        'assumptions': {
            f'dispatches_per_year_{args.label_a}': args.days_per_year / args.cycle_a,
            f'dispatches_per_year_{args.label_b}': args.days_per_year / args.cycle_b,
            f'days_per_dispatch_{args.label_a}': args.cycle_a,
            f'days_per_dispatch_{args.label_b}': args.cycle_b,
            'days_per_year': args.days_per_year,
            'switch_threshold_usd': args.threshold,
            'site_override_rule': 'highest approved version_no per program_code, else default_active_sites'
        },
        'programs': results,
        'totals': {
            f'total_annual_margin_{args.label_a}_usd': total_margin_a,
            f'total_annual_margin_{args.label_b}_usd': total_margin_b,
            'absolute_difference_usd': abs_diff,
            'decision': decision
        }
    }

    json_path = os.path.join(args.output_dir, 'cooler_dispatch_analysis.json')
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2)

    # Write Markdown
    md_path = os.path.join(args.output_dir, 'cooler_dispatch_summary.md')
    with open(md_path, 'w') as f:
        f.write(f'# Oncology Supportive-Care Cooler Dispatch Analysis\n\n')
        f.write(f'**Total {args.label_a.replace("_", "-")} annual margin:** ${total_margin_a:,.2f} USD\n')
        f.write(f'**Total {args.label_b.replace("_", "-")} annual margin:** ${total_margin_b:,.2f} USD\n')
        f.write(f'**Absolute margin difference:** ${abs_diff:,.2f} USD\n\n')
        f.write(f'**Decision:** `{decision}`\n')

    print(f'JSON: {json_path}')
    print(f'Summary: {md_path}')
    print(f'Decision: {decision}')


if __name__ == '__main__':
    main()
