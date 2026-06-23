#!/usr/bin/env python3
"""
Calculate logistics dispatch margins comparing frequency scenarios.

Usage: python3 calculate_dispatch_margins.py [config.json]

Expected input files:
- program_catalog.json (service_groups with programs)
- cooler_cost.csv (cooler_type, cooler_cost_usd)
- contract_payment.csv (program_label, payment_per_dispatch_per_site_usd)
- site_overrides.csv (program_code, version_no, approval_state, active_sites)

Outputs:
- dispatch_analysis.json (detailed results)
- dispatch_summary.md (human summary)
"""

import csv
import json
import sys
from pathlib import Path


def load_json(path: str) -> dict:
    """Load JSON file."""
    with open(path, 'r') as f:
        return json.load(f)


def load_csv(path: str) -> list[dict]:
    """Load CSV, return list of dicts."""
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def build_cooler_cost_map(cooler_cost_data: list[dict]) -> dict:
    """Map cooler_type -> cooler_cost_usd."""
    return {
        row['cooler_type']: float(row['cooler_cost_usd'])
        for row in cooler_cost_data
    }


def build_payment_map(payment_data: list[dict]) -> dict:
    """Build normalized payment lookup from program_label."""
    payment_map = {}
    for row in payment_data:
        label = row['program_label']
        payment = float(row['payment_per_dispatch_per_site_usd'])
        # Store original and normalized versions
        payment_map[label] = payment
        payment_map[label.lower()] = payment
        payment_map[label.replace('-', ' ').lower()] = payment
        payment_map[label.replace(' ', '').lower()] = payment
    return payment_map


def match_payment(program: dict, payment_map: dict) -> float | None:
    """Match payment using program_name and known_labels."""
    # Try program_name variations
    name = program.get('program_name', '')
    name_norm = name.lower().replace('-', ' ')
    if name_norm in payment_map:
        return payment_map[name_norm]
    if name.lower() in payment_map:
        return payment_map[name.lower()]
    
    # Try known_labels
    for label in program.get('known_labels', []):
        label_norm = label.lower().replace('-', ' ')
        if label_norm in payment_map:
            return payment_map[label_norm]
        if label.lower() in payment_map:
            return payment_map[label.lower()]
    
    return None


def resolve_sites(overrides: list[dict], program_code: str, default_sites: int) -> int:
    """Resolve site count using approval workflow."""
    # Filter to target program
    program_rows = [
        row for row in overrides
        if row.get('program_code') == program_code
    ]
    
    if not program_rows:
        return default_sites
    
    # Filter to approved only
    approved = [
        row for row in program_rows
        if row.get('approval_state') == 'approved'
    ]
    
    if not approved:
        return default_sites
    
    # Select highest version
    highest = max(approved, key=lambda r: int(r.get('version_no', 0)))
    
    return int(highest.get('active_sites', default_sites))


def extract_programs(catalog: dict) -> list[dict]:
    """Extract flat list of programs from service_groups."""
    programs = []
    for group in catalog.get('service_groups', []):
        for prog in group.get('programs', []):
            programs.append(prog)
    return programs


def calculate_program_margins(
    program: dict,
    cooler_cost_map: dict,
    payment_map: dict,
    overrides: list[dict],
    config: dict
) -> dict | None:
    """Calculate margins for one program under both dispatch frequencies."""
    
    # Filter by review_flag
    if program.get('review_flag') != 'review':
        return None
    
    # Extract values
    code = program['program_code']
    name = program['program_name']
    cost_per_1000 = float(program['acquisition_cost_per_1000_units_usd'])
    units_per_day = float(program['units_per_day'])
    cooler_type = program['cooler_type']
    default_sites = int(program['default_active_sites'])
    
    # Resolve sites
    sites = resolve_sites(overrides, code, default_sites)
    
    # Look up costs and payment
    cooler_cost = cooler_cost_map.get(cooler_type)
    if cooler_cost is None:
        raise ValueError(f"Unknown cooler_type: {cooler_type} for {code}")
    
    payment = match_payment(program, payment_map)
    if payment is None:
        raise ValueError(f"Could not match payment for {code} with labels: {program.get('known_labels', [])}")
    
    # Config constants
    dispatches_a = config['dispatches_per_year_a']  # e.g., 36 for 10-day
    dispatches_b = config['dispatches_per_year_b']  # e.g., 18 for 20-day
    
    # Annual units (constant across scenarios)
    annual_units = units_per_day * 365 * sites
    annual_drug_cost = annual_units * cost_per_1000 / 1000
    
    # Scenario A
    annual_cooler_a = cooler_cost * dispatches_a * sites
    annual_revenue_a = payment * dispatches_a * sites
    margin_a = annual_revenue_a - annual_drug_cost - annual_cooler_a
    
    # Scenario B
    annual_cooler_b = cooler_cost * dispatches_b * sites
    annual_revenue_b = payment * dispatches_b * sites
    margin_b = annual_revenue_b - annual_drug_cost - annual_cooler_b
    
    return {
        'program_code': code,
        'program_name': name,
        'cooler_type': cooler_type,
        'active_sites': sites,
        'acquisition_cost_per_1000_units_usd': cost_per_1000,
        'units_per_day': units_per_day,
        'payment_per_dispatch_per_site_usd': payment,
        'cooler_cost_per_dispatch_usd': cooler_cost,
        'annual_drug_cost_usd': annual_drug_cost,
        'annual_cooler_cost_a_usd': annual_cooler_a,
        'annual_cooler_cost_b_usd': annual_cooler_b,
        'annual_revenue_a_usd': annual_revenue_a,
        'annual_revenue_b_usd': annual_revenue_b,
        'annual_margin_a_usd': margin_a,
        'annual_margin_b_usd': margin_b,
        'annual_margin_difference_b_minus_a_usd': margin_b - margin_a
    }


def main():
    # Default configuration - ADAPT these to your task
    config = {
        'dispatches_per_year_a': 36,    # 10-day: 365/10
        'dispatches_per_year_b': 18,    # 20-day: 365/20
        'switch_threshold_usd': 10000,
        'scenario_a_name': '10_day',    # Used in output keys
        'scenario_b_name': '20_day',
        'recommendation_enum': {        # VERIFY from task schema
            'keep_a': 'keep_10_day',
            'switch_to_b': 'switch_to_20_day'
        }
    }
    
    # Override with config file if provided
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            config.update(json.load(f))
    
    # Load data
    catalog = load_json('program_catalog.json')
    cooler_costs = load_csv('cooler_cost.csv')
    payments = load_csv('contract_payment.csv')
    overrides = load_csv('site_overrides.csv')
    
    # Build lookups
    cooler_cost_map = build_cooler_cost_map(cooler_costs)
    payment_map = build_payment_map(payments)
    
    # Extract and process programs
    programs = extract_programs(catalog)
    
    results = []
    for prog in programs:
        try:
            result = calculate_program_margins(
                prog, cooler_cost_map, payment_map, overrides, config
            )
            if result:
                results.append(result)
        except ValueError as e:
            print(f"Warning: {e}", file=sys.stderr)
    
    if not results:
        print("No programs with review_flag='review' found", file=sys.stderr)
        sys.exit(1)
    
    # Calculate totals
    total_a = sum(r['annual_margin_a_usd'] for r in results)
    total_b = sum(r['annual_margin_b_usd'] for r in results)
    abs_diff = abs(total_b - total_a)
    
    # Decision - USE configured enum values, verify against task schema
    rec = config['recommendation_enum']
    if abs_diff >= config['switch_threshold_usd'] and total_b > total_a:
        recommendation = rec['switch_to_b']
    else:
        recommendation = rec['keep_a']
    
    # Build output with configurable keys
    a_key = config['scenario_a_name']
    b_key = config['scenario_b_name']
    
    output = {
        'assumptions': {
            f'dispatches_per_year_{a_key}': config['dispatches_per_year_a'],
            f'dispatches_per_year_{b_key}': config['dispatches_per_year_b'],
            'switch_threshold_usd': config['switch_threshold_usd']
        },
        'programs': results,
        'totals': {
            f'total_{a_key}_margin_usd': total_a,
            f'total_{b_key}_margin_usd': total_b,
            'absolute_difference_usd': abs_diff
        },
        'recommendation': recommendation
    }
    
    # Write outputs
    with open('dispatch_analysis.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    summary = f"""## Dispatch Analysis Summary

- **{a_key} model**: ${total_a:,.2f} USD annual margin
- **{b_key} model**: ${total_b:,.2f} USD annual margin
- **Absolute difference**: ${abs_diff:,.2f} USD
- **Decision**: `{recommendation}`

Threshold: ${config['switch_threshold_usd']:,.2f} USD
"""
    with open('dispatch_summary.md', 'w') as f:
        f.write(summary)
    
    print(f"Analysis complete!")
    print(f"{a_key} margin: ${total_a:,.2f}")
    print(f"{b_key} margin: ${total_b:,.2f}")
    print(f"Decision: {recommendation}")


if __name__ == '__main__':
    main()
