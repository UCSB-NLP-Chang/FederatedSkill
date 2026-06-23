#!/usr/bin/env python3
import argparse
import csv
import json
import os
from collections import defaultdict

def load_manifest(path):
    with open(path) as f:
        data = json.load(f)
    campaigns = []
    for region in data.get('regions', []):
        for c in region.get('campaigns', []):
            if c.get('analysis_flag', '').lower() != 'archive':
                campaigns.append(c)
    return campaigns

def load_suspensions(path):
    holds = set()
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            if row.get('suspension_status', '').strip().lower() == 'hold':
                holds.add(row['campaign_id'])
    return holds

def resolve_clinics(overrides_path, campaign_ids, campaigns_by_id):
    rows = []
    with open(overrides_path, newline='') as f:
        for row in csv.DictReader(f):
            cid = row['campaign_id']
            if cid in campaign_ids and row.get('state', '').strip().lower() == 'approved':
                rev_str = row.get('revision', '').strip()
                if rev_str == '':
                    continue
                try:
                    rev = int(rev_str)
                except ValueError:
                    continue
                clinics_str = row.get('active_clinics', '').strip()
                clinics = int(clinics_str) if clinics_str else 0
                rows.append({'cid': cid, 'rev': rev, 'clinics': clinics})
    
    by_id = defaultdict(list)
    for r in rows:
        by_id[r['cid']].append(r)
        
    result = {}
    for cid, revs in by_id.items():
        valid = [r for r in revs if r['clinics'] > 0]
        if valid:
            best = max(valid, key=lambda x: x['rev'])
            result[cid] = best['clinics']
        else:
            result[cid] = campaigns_by_id[cid].get('default_active_clinics', 0)
            
    for cid in campaign_ids:
        if cid not in result:
            result[cid] = campaigns_by_id[cid].get('default_active_clinics', 0)
    return result

def resolve_billing(billing_path, alias_map):
    records = []
    with open(billing_path, newline='') as f:
        for row in csv.DictReader(f):
            label = row['campaign_label']
            cid = alias_map.get(label)
            if cid and row.get('status', '').strip().lower() == 'active':
                records.append({
                    'cid': cid,
                    'cycle_tag': row['cycle_tag'],
                    'payment': float(row['payment_per_dispatch_per_clinic_usd'])
                })
    by_id = defaultdict(list)
    for r in records:
        by_id[r['cid']].append(r)
    result = {}
    for cid, recs in by_id.items():
        best = max(recs, key=lambda x: x['cycle_tag'])
        result[cid] = best['payment']
    return result

def load_crate_costs(path):
    costs = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            costs[row['crate_tier']] = float(row['crate_cost_usd'])
    return costs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--suspensions', required=True)
    parser.add_argument('--overrides', required=True)
    parser.add_argument('--billing', required=True)
    parser.add_argument('--crates', required=True)
    parser.add_argument('--cycle-a', type=int, default=6)
    parser.add_argument('--cycle-b', type=int, default=12)
    parser.add_argument('--threshold', type=float, default=11000)
    parser.add_argument('--output-dir', default='.')
    parser.add_argument('--label-a', default='6_day')
    parser.add_argument('--label-b', default='12_day')
    args = parser.parse_args()

    campaigns = load_manifest(args.manifest)
    holds = load_suspensions(args.suspensions)
    
    campaigns = [c for c in campaigns if c['campaign_id'] not in holds]
    campaign_ids = {c['campaign_id'] for c in campaigns}
    campaigns_by_id = {c['campaign_id']: c for c in campaigns}
    
    alias_map = {}
    for c in campaigns:
        alias_map[c['campaign_name']] = c['campaign_id']
        for alias in c.get('alias_labels', []):
            alias_map[alias] = c['campaign_id']
            
    clinics = resolve_clinics(args.overrides, campaign_ids, campaigns_by_id)
    payments = resolve_billing(args.billing, alias_map)
    crate_costs = load_crate_costs(args.crates)
    
    dispatches_a = 360.0 / args.cycle_a
    dispatches_b = 360.0 / args.cycle_b
    
    results = []
    total_margin_a = 0.0
    total_margin_b = 0.0
    
    for c in campaigns:
        cid = c['campaign_id']
        cl = clinics.get(cid, 0)
        if cl == 0:
            continue
            
        price = c['drug_cost_per_1000_doses_usd']
        doses = c['doses_per_day']
        tier = c['crate_tier']
        crate_cost = crate_costs.get(tier, 0)
        payment = payments.get(cid, 0)
        
        drug_cost = doses * 360.0 * cl * (price / 1000.0)
        
        crate_a = crate_cost * dispatches_a
        crate_b = crate_cost * dispatches_b
        
        rev_a = payment * dispatches_a * cl
        rev_b = payment * dispatches_b * cl
        
        margin_a = rev_a - drug_cost - crate_a
        margin_b = rev_b - drug_cost - crate_b
        
        total_margin_a += margin_a
        total_margin_b += margin_b
        
        results.append({
            'campaign_id': cid,
            'campaign_name': c['campaign_name'],
            'active_clinics': cl,
            'drug_cost_per_1000_doses_usd': price,
            'doses_per_day': doses,
            'crate_tier': tier,
            'crate_cost_usd': crate_cost,
            'payment_per_dispatch_per_clinic_usd': payment,
            f'annual_drug_cost_{args.label_a}_usd': drug_cost,
            f'annual_drug_cost_{args.label_b}_usd': drug_cost,
            f'annual_crate_cost_{args.label_a}_usd': crate_a,
            f'annual_crate_cost_{args.label_b}_usd': crate_b,
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
        
    output = {
        'assumptions': {
            f'dispatches_per_year_{args.label_a}': dispatches_a,
            f'dispatches_per_year_{args.label_b}': dispatches_b,
            f'days_per_dispatch_{args.label_a}': args.cycle_a,
            f'days_per_dispatch_{args.label_b}': args.cycle_b,
            'switch_threshold_usd': args.threshold,
            'override_rule': 'highest numeric approved revision with non-empty active_clinics, else default_active_clinics',
            'suspension_rule': 'exclude hold campaigns'
        },
        'campaigns': results,
        'totals': {
            f'total_annual_margin_{args.label_a}_usd': total_margin_a,
            f'total_annual_margin_{args.label_b}_usd': total_margin_b,
            'absolute_difference_usd': abs_diff,
            'decision': decision
        }
    }
    
    json_path = os.path.join(args.output_dir, 'vaxcrate_analysis.json')
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2)
        
    md_path = os.path.join(args.output_dir, 'vaxcrate_summary.md')
    with open(md_path, 'w') as f:
        f.write(f'## Vaccination Crate Dispatch Analysis: {args.label_a.replace("_", "-")} vs {args.label_b.replace("_", "-")} Policy\n\n')
        f.write(f'- **Total {args.label_a.replace("_", "-")} annual margin:** ${total_margin_a:,.2f} USD\n')
        f.write(f'- **Total {args.label_b.replace("_", "-")} annual margin:** ${total_margin_b:,.2f} USD\n')
        f.write(f'- **Absolute margin difference ({args.label_b} − {args.label_a}):** ${abs_diff:,.2f} USD\n')
        f.write(f'- **Final decision:** {decision}\n\n')
        f.write(f'Campaigns evaluated: {len(results)}. The {args.label_b.replace("_", "-")} dispatch model reduces crate costs by half but cuts revenue proportionally; drug costs remain identical across both policies.\n')
        
    print(f'JSON: {json_path}')
    print(f'Summary: {md_path}')
    print(f'Decision: {decision}')

if __name__ == '__main__':
    main()
