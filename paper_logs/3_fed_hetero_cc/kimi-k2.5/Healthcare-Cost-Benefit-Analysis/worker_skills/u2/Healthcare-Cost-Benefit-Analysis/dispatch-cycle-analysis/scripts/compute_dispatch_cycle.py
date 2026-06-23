#!/usr/bin/env python3
"""
Compute dispatch cycle analysis comparing two dispatch frequencies.
Handles JSON catalog with aliases, CSV overrides with revision logic, 
CSV billing with cycle_tag selection, and optional suspension filtering.
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

def parse_catalog(path, scope_flag='analysis_flag', scope_value='review', 
                  entity_key='campaigns', nested_key='regions'):
    """Load catalog, return list of in-scope entities."""
    with open(path) as f:
        data = json.load(f)
    
    entities = []
    # Try common nesting patterns
    containers = data.get(nested_key, data.get('service_lines', data.get('service_groups', [data])))
    
    for container in containers:
        if entity_key in container:
            for entity in container[entity_key]:
                # Check scope flag
                flag_val = entity.get(scope_flag, entity.get('include_in_review', entity.get('review_flag')))
                if scope_flag == 'analysis_flag' and flag_val == scope_value:
                    entities.append(entity)
                elif scope_flag == 'include_in_review' and flag_val == (scope_value == 'true' or scope_value is True):
                    entities.append(entity)
                elif scope_flag == 'review_flag' and flag_val == scope_value:
                    entities.append(entity)
                elif flag_val == scope_value or (isinstance(scope_value, bool) and flag_val == scope_value):
                    entities.append(entity)
    return entities

def build_alias_map(entities, name_col='campaign_name', alias_col='alias_labels'):
    """Map alias (case-insensitive) -> entity_id."""
    alias_map = {}
    for e in entities:
        code = e.get('campaign_id', e.get('therapy_code', e.get('program_code', e.get('assay_id'))))
        # Primary name as alias
        name = e.get(name_col, e.get('therapy_name', e.get('program_name', e.get('assay_name'))))
        if name:
            alias_map[name.lower()] = code
        # Additional aliases
        aliases = e.get(alias_col, e.get('aliases', e.get('known_labels', [])))
        for alias in aliases:
            alias_map[alias.lower()] = code
    return alias_map

def load_suspensions(path):
    """Return dict of entity_id -> suspension_status to exclude."""
    suspensions = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            entity_id = row.get('campaign_id', row.get('therapy_code', row.get('program_code')))
            status = row.get('suspension_status', row.get('status', ''))
            suspensions[entity_id] = status
    return suspensions

def resolve_counts(overrides_path, entity_ids, entities_by_id, 
                   revision_col='revision', status_col='state', count_col='active_clinics',
                   default_col='default_active_clinics'):
    """From overrides CSV, return dict entity_id -> count (highest approved revision)."""
    rows = []
    with open(overrides_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entity_id = row.get('campaign_id', row.get('therapy_code', row.get('program_code', row.get('assay_id'))))
            if entity_id not in entity_ids:
                continue
            status = row.get(status_col, '').lower()
            if status != 'approved':
                continue
            rev = row.get(revision_col, '').strip()
            if rev == '':
                continue
            count_val = row.get(count_col, '').strip()
            if count_val == '':
                continue
            rows.append({
                'entity_id': entity_id,
                'revision': int(rev),
                'count': int(count_val)
            })
    
    # Group by entity, pick max revision
    by_entity = defaultdict(list)
    for r in rows:
        by_entity[r['entity_id']].append(r)
    
    result = {}
    for code, revs in by_entity.items():
        best = max(revs, key=lambda x: x['revision'])
        result[code] = best['count']
    
    # Fallback to default
    for entity in entities_by_id.values():
        code = entity.get('campaign_id', entity.get('therapy_code', entity.get('program_code', entity.get('assay_id'))))
        if code not in result:
            result[code] = entity.get(default_col, entity.get('default_active_sites', entity.get('default_active_patients', entity.get('default_active_labs', 0))))
    return result

def load_supply_costs(path, key_col='crate_tier', cost_col='crate_cost_usd'):
    """Return dict key -> cost_usd."""
    costs = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            key = row.get(key_col, row.get('bag_size_ml', row.get('cooler_type')))
            cost = float(row.get(cost_col, row.get('bag_supply_cost_usd', row.get('cooler_cost_usd', 0))))
            costs[key] = cost
    return costs

def load_billing(path, alias_map, label_col='campaign_label', 
                 status_col='status', active_val='active',
                 date_col='cycle_tag', payment_col='payment_per_dispatch_per_clinic_usd'):
    """Return dict entity_id -> payment (latest active date)."""
    records = []
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            label = row.get(label_col, row.get('therapy_label', row.get('program_label', row.get('assay_label'))))
            status = row.get(status_col, '').lower()
            if status != active_val:
                continue
            entity_id = alias_map.get(label.lower())
            if not entity_id:
                continue
            records.append({
                'entity_id': entity_id,
                'date': row.get(date_col, row.get('effective_month', '')),
                'payment': float(row.get(payment_col, row.get('payment_per_delivery_per_patient_usd', row.get('payment_per_run_per_lab_usd', 0))))
            })
    
    # Group by entity, pick latest date
    by_entity = defaultdict(list)
    for r in records:
        by_entity[r['entity_id']].append(r)
    
    result = {}
    for code, recs in by_entity.items():
        best = max(recs, key=lambda x: x['date'])
        result[code] = best['payment']
    return result

def compute_annual(doses_per_day, days_per_year, count, price_per_1000, 
                   supply_cost, payment, dispatches_per_year):
    """Return (drug_cost, supply_cost_annual, revenue) for annual period."""
    # Annual drug cost: doses/day * days/year * count * (price/1000)
    annual_drug = doses_per_day * days_per_year * count * (price_per_1000 / 1000.0)
    # Annual supply: supply_cost * dispatches/year * count
    annual_supply = supply_cost * dispatches_per_year * count
    # Annual revenue: payment * dispatches/year * count
    annual_revenue = payment * dispatches_per_year * count
    return annual_drug, annual_supply, annual_revenue

def main():
    parser = argparse.ArgumentParser(description='Compute dispatch cycle analysis')
    parser.add_argument('--catalog', required=True, help='Path to catalog JSON')
    parser.add_argument('--overrides', required=True, help='Path to overrides CSV')
    parser.add_argument('--billing', required=True, help='Path to billing CSV')
    parser.add_argument('--supply', required=True, help='Path to supply cost CSV')
    parser.add_argument('--suspensions', help='Path to suspensions CSV (optional)')
    parser.add_argument('--cycle-a', type=int, required=True, help='Days per cycle A')
    parser.add_argument('--cycle-b', type=int, required=True, help='Days per cycle B')
    parser.add_argument('--days-per-year', type=float, default=365.0, help='Days per year for calculations')
    parser.add_argument('--threshold', type=float, required=True, help='Decision threshold USD')
    parser.add_argument('--output-dir', default='.', help='Output directory')
    parser.add_argument('--output-prefix', default='dispatch_cycle', help='Prefix for output files')
    parser.add_argument('--label-a', help='Label for cycle A (default: {cycle_a}_day)')
    parser.add_argument('--label-b', help='Label for cycle B (default: {cycle_b}_day)')
    parser.add_argument('--scope-flag', default='analysis_flag', help='Flag field for in-scope check')
    parser.add_argument('--scope-value', default='review', help='Value for in-scope check')
    parser.add_argument('--suspension-status', default='hold', help='Status to exclude')
    args = parser.parse_args()
    
    label_a = args.label_a or f"{args.cycle_a}_day"
    label_b = args.label_b or f"{args.cycle_b}_day"
    
    # Load data
    entities = parse_catalog(args.catalog, args.scope_flag, args.scope_value)
    entity_ids = {e.get('campaign_id', e.get('therapy_code', e.get('program_code', e.get('assay_id')))) for e in entities}
    entities_by_id = {e.get('campaign_id', e.get('therapy_code', e.get('program_code', e.get('assay_id')))): e for e in entities}
    
    # Filter suspensions
    if args.suspensions:
        suspensions = load_suspensions(args.suspensions)
        excluded = {eid for eid, status in suspensions.items() if status == args.suspension_status}
        entities = [e for e in entities if e.get('campaign_id', e.get('therapy_code', e.get('program_code', e.get('assay_id')))) not in excluded]
        entity_ids -= excluded
        entities_by_id = {k: v for k, v in entities_by_id.items() if k not in excluded}
    
    alias_map = build_alias_map(entities)
    counts = resolve_counts(args.overrides, entity_ids, entities_by_id)
    supply_costs = load_supply_costs(args.supply)
    payments = load_billing(args.billing, alias_map)
    
    # Compute dispatches per year
    dispatches_a = args.days_per_year / args.cycle_a
    dispatches_b = args.days_per_year / args.cycle_b
    
    results = []
    total_margin_a = 0.0
    total_margin_b = 0.0
    
    for entity in entities:
        code = entity.get('campaign_id', entity.get('therapy_code', entity.get('program_code', entity.get('assay_id'))))
        if code not in counts or counts[code] == 0:
            continue
        
        count = counts[code]
        price = entity.get('drug_cost_per_1000_doses_usd', entity.get('drug_cost_per_1000_mg_usd', entity.get('acquisition_cost_per_1000_units_usd', 0)))
        doses = entity.get('doses_per_day', entity.get('dose_mg_per_day', entity.get('units_per_day', 0)))
        supply_key = entity.get('crate_tier', entity.get('bag_size_ml', entity.get('cooler_type', '')))
        supply_cost = supply_costs.get(str(supply_key), 0)
        payment = payments.get(code, 0)
        
        # Compute for both cycles
        drug_a, supply_a, rev_a = compute_annual(doses, args.days_per_year, count, price, supply_cost, payment, dispatches_a)
        drug_b, supply_b, rev_b = compute_annual(doses, args.days_per_year, count, price, supply_cost, payment, dispatches_b)
        
        margin_a = rev_a - drug_a - supply_a
        margin_b = rev_b - drug_b - supply_b
        
        total_margin_a += margin_a
        total_margin_b += margin_b
        
        result = {
            'entity_id': code,
            'name': entity.get('campaign_name', entity.get('therapy_name', entity.get('program_name', entity.get('assay_name')))),
            'active_count': count,
            'drug_cost_per_1000_usd': price,
            'doses_per_day': doses,
            'supply_type': supply_key,
            'supply_cost_usd': supply_cost,
            'payment_per_dispatch_usd': payment,
            f'annual_drug_cost_{label_a}_usd': drug_a,
            f'annual_drug_cost_{label_b}_usd': drug_b,
            f'annual_supply_cost_{label_a}_usd': supply_a,
            f'annual_supply_cost_{label_b}_usd': supply_b,
            f'annual_revenue_{label_a}_usd': rev_a,
            f'annual_revenue_{label_b}_usd': rev_b,
            f'annual_margin_{label_a}_usd': margin_a,
            f'annual_margin_{label_b}_usd': margin_b,
            f'annual_margin_difference_{label_b}_minus_{label_a}_usd': margin_b - margin_a
        }
        results.append(result)
    
    abs_diff = abs(total_margin_b - total_margin_a)
    if total_margin_b > total_margin_a and abs_diff > args.threshold:
        decision = f'switch_to_{label_b}'
    else:
        decision = f'keep_{label_a}'
    
    # Write JSON
    output = {
        'assumptions': {
            'days_per_year': args.days_per_year,
            f'dispatches_per_year_{label_a}': dispatches_a,
            f'dispatches_per_year_{label_b}': dispatches_b,
            f'days_per_dispatch_{label_a}': args.cycle_a,
            f'days_per_dispatch_{label_b}': args.cycle_b,
            'switch_threshold_usd': args.threshold,
            'override_rule': 'highest approved revision with non-empty count, else default',
            'billing_rule': 'latest active cycle_tag per entity (alias match)'
        },
        'entities': results,
        'totals': {
            f'total_annual_margin_{label_a}_usd': total_margin_a,
            f'total_annual_margin_{label_b}_usd': total_margin_b,
            'absolute_difference_usd': abs_diff,
            'decision': decision
        }
    }
    
    json_path = os.path.join(args.output_dir, f'{args.output_prefix}_analysis.json')
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    # Write Markdown
    md_path = os.path.join(args.output_dir, f'{args.output_prefix}_summary.md')
    with open(md_path, 'w') as f:
        f.write(f'# Dispatch Cycle Analysis Summary\n\n')
        f.write(f'**Total {label_a.replace("_", "-")} margin:** ${total_margin_a:,.2f} USD\n')
        f.write(f'**Total {label_b.replace("_", "-")} margin:** ${total_margin_b:,.2f} USD\n')
        f.write(f'**Absolute margin difference:** ${abs_diff:,.2f} USD\n\n')
        f.write(f'**Decision:** {decision}\n\n')
        f.write(f'{len(results)} entities evaluated.')
    
    print(f'JSON: {json_path}')
    print(f'Summary: {md_path}')
    print(f'Decision: {decision}')

if __name__ == '__main__':
    main()