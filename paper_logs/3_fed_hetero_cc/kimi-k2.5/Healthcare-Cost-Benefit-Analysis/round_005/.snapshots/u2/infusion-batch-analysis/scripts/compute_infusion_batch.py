#!/usr/bin/env python3
"""
Compute infusion therapy batch analysis comparing two delivery cycles.
Handles JSON catalog with aliases, CSV overrides with revision logic, and exact day-based calculations.
"""
import argparse
import csv
import json
import os
from collections import defaultdict

def parse_catalog(path):
    """Load therapy catalog, return list of therapies with include_in_review=True."""
    with open(path) as f:
        data = json.load(f)
    therapies = []
    for sl in data.get('service_lines', []):
        for t in sl.get('therapies', []):
            if t.get('include_in_review', False):
                therapies.append(t)
    return therapies

def build_alias_map(therapies):
    """Map alias (case-insensitive) -> therapy_code."""
    alias_map = {}
    for t in therapies:
        code = t['therapy_code']
        for alias in t.get('aliases', []):
            alias_map[alias.lower()] = code
        # Also map therapy_name as alias
        alias_map[t['therapy_name'].lower()] = code
    return alias_map

def resolve_patients(overrides_path, therapy_codes):
    """From overrides CSV, return dict therapy_code -> active_patients (highest approved revision)."""
    rows = []
    with open(overrides_path, newline='') as f:
        for row in csv.DictReader(f):
            if row['therapy_code'] in therapy_codes and row['status'].lower() == 'approved':
                rows.append({
                    'therapy_code': row['therapy_code'],
                    'revision': int(row['revision']),
                    'active_patients': int(row['active_patients'])
                })
    # Group by therapy_code, pick max revision
    by_code = defaultdict(list)
    for r in rows:
        by_code[r['therapy_code']].append(r)
    result = {}
    for code, revs in by_code.items():
        best = max(revs, key=lambda x: x['revision'])
        result[code] = best['active_patients']
    return result

def load_supply_costs(path):
    """Return dict bag_size_ml -> bag_supply_cost_usd."""
    costs = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            key = str(int(float(row['bag_size_ml'])))
            costs[key] = float(row['bag_supply_cost_usd'])
    return costs

def load_payments(path, alias_map):
    """Return dict therapy_code -> payment_per_delivery_per_patient_usd."""
    payments = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            label = row['therapy_label'].lower()
            code = alias_map.get(label)
            if code:
                payments[code] = float(row['payment_per_delivery_per_patient_usd'])
    return payments

def compute_annual(dose_mg_per_day, patients, price_per_1000, bag_cost, payment, days_cycle):
    """Return (drug_cost, supply_cost, revenue) for annual period."""
    # Exact deliveries per year using floating point
    deliveries_per_year = 365.0 / days_cycle
    
    # Annual drug cost: dose * 365 days * patients * (price/1000)
    annual_drug = dose_mg_per_day * 365.0 * patients * (price_per_1000 / 1000.0)
    
    # Annual supply: bag_cost * deliveries * patients
    annual_supply = bag_cost * deliveries_per_year * patients
    
    # Annual revenue: payment * deliveries * patients
    annual_revenue = payment * deliveries_per_year * patients
    
    return annual_drug, annual_supply, annual_revenue

def main():
    parser = argparse.ArgumentParser(description='Compute infusion batch analysis')
    parser.add_argument('--catalog', required=True, help='Path to therapy_catalog.json')
    parser.add_argument('--supply', required=True, help='Path to bag_supply_cost.csv')
    parser.add_argument('--payments', required=True, help='Path to delivery_payment.csv')
    parser.add_argument('--overrides', required=True, help='Path to patient_overrides.csv')
    parser.add_argument('--cycle-a', type=int, default=7, help='Days per delivery cycle A')
    parser.add_argument('--cycle-b', type=int, default=14, help='Days per delivery cycle B')
    parser.add_argument('--threshold', type=float, default=15000, help='Decision threshold USD')
    parser.add_argument('--output-dir', default='.', help='Output directory')
    parser.add_argument('--label-a', default='7_day', help='Label for cycle A')
    parser.add_argument('--label-b', default='14_day', help='Label for cycle B')
    args = parser.parse_args()
    
    # Load data
    therapies = parse_catalog(args.catalog)
    therapy_codes = {t['therapy_code'] for t in therapies}
    alias_map = build_alias_map(therapies)
    patients = resolve_patients(args.overrides, therapy_codes)
    supply_costs = load_supply_costs(args.supply)
    payments = load_payments(args.payments, alias_map)
    
    results = []
    total_margin_a = 0.0
    total_margin_b = 0.0
    
    for t in therapies:
        code = t['therapy_code']
        if code not in patients:
            continue  # Skip if no approved patient data
        
        pat = patients[code]
        dose = t['dose_mg_per_day']
        price = t['drug_cost_per_1000_mg_usd']
        bag_key = str(t['bag_size_ml'])
        bag_cost = supply_costs.get(bag_key, 0)
        payment = payments.get(code, 0)
        
        # Compute for both cycles
        drug_a, supply_a, rev_a = compute_annual(dose, pat, price, bag_cost, payment, args.cycle_a)
        drug_b, supply_b, rev_b = compute_annual(dose, pat, price, bag_cost, payment, args.cycle_b)
        
        margin_a = rev_a - drug_a - supply_a
        margin_b = rev_b - drug_b - supply_b
        
        total_margin_a += margin_a
        total_margin_b += margin_b
        
        results.append({
            'therapy_code': code,
            'therapy_name': t['therapy_name'],
            'active_patients': pat,
            'dose_mg_per_day': dose,
            'drug_cost_per_1000_mg_usd': price,
            'bag_size_ml': t['bag_size_ml'],
            'bag_supply_cost_usd': bag_cost,
            'payment_per_delivery_per_patient_usd': payment,
            f'annual_drug_cost_{args.label_a}_usd': drug_a,
            f'annual_drug_cost_{args.label_b}_usd': drug_b,
            f'annual_supply_cost_{args.label_a}_usd': supply_a,
            f'annual_supply_cost_{args.label_b}_usd': supply_b,
            f'annual_revenue_{args.label_a}_usd': rev_a,
            f'annual_revenue_{args.label_b}_usd': rev_b,
            f'annual_margin_{args.label_a}_usd': margin_a,
            f'annual_margin_{args.label_b}_usd': margin_b,
            f'annual_margin_difference_{args.label_b}_minus_{args.label_a}_usd': margin_b - margin_a
        })
    
    abs_diff = abs(total_margin_b - total_margin_a)
    if total_margin_b > total_margin_a and abs_diff > args.threshold:
        decision = f'move_to_{args.label_b}'
    else:
        decision = f'keep_{args.label_a}'
    
    # Write JSON
    output = {
        'assumptions': {
            f'deliveries_per_year_{args.label_a}': 365.0 / args.cycle_a,
            f'deliveries_per_year_{args.label_b}': 365.0 / args.cycle_b,
            f'days_per_delivery_{args.label_a}': args.cycle_a,
            f'days_per_delivery_{args.label_b}': args.cycle_b,
            'switch_threshold_usd': args.threshold,
            'patient_override_rule': 'highest approved revision per therapy_code'
        },
        'therapies': results,
        'totals': {
            f'total_annual_margin_{args.label_a}_usd': total_margin_a,
            f'total_annual_margin_{args.label_b}_usd': total_margin_b,
            'absolute_difference_usd': abs_diff,
            'decision': decision
        }
    }
    
    json_path = os.path.join(args.output_dir, 'infusion_batch_analysis.json')
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    # Write Markdown
    md_path = os.path.join(args.output_dir, 'infusion_batch_summary.md')
    with open(md_path, 'w') as f:
        f.write(f'## Infusion Batching Analysis Summary\n\n')
        f.write(f'- Total {args.label_a.replace("_", "-")} delivery annual margin: ${total_margin_a:,.2f} USD\n')
        f.write(f'- Total {args.label_b.replace("_", "-")} delivery annual margin: ${total_margin_b:,.2f} USD\n')
        f.write(f'- Absolute margin difference: ${abs_diff:,.2f} USD\n\n')
        f.write(f'**Decision: {decision}**\n')
    
    print(f'JSON: {json_path}')
    print(f'Summary: {md_path}')
    print(f'Decision: {decision}')

if __name__ == '__main__':
    main()
