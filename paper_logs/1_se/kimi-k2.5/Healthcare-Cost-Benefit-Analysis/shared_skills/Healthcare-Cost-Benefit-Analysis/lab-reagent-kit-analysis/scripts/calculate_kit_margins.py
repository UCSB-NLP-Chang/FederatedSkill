#!/usr/bin/env python3
"""
Calculate reagent kit policy margins comparing small-kit vs bulk-kit scenarios.

Usage: python3 calculate_kit_margins.py [config.json]

Expected input files:
- assay_manifest.json (regions with assays)
- carrier_cost.csv (carrier_type, carrier_cost_usd)
- billing.csv (assay_label, effective_month, is_active, payment_per_run_per_lab_usd)
- lab_overrides.csv (assay_id, revision, status, active_labs)

Outputs:
- reagent_policy_analysis.json (detailed results)
- reagent_policy_summary.md (human summary)
"""

import csv
import json
import sys
from pathlib import Path
from datetime import datetime


def load_json(path: str) -> dict:
    """Load JSON file."""
    with open(path, 'r') as f:
        return json.load(f)


def load_csv(path: str) -> list[dict]:
    """Load CSV, return list of dicts."""
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def build_carrier_cost_map(carrier_cost_data: list[dict]) -> dict:
    """Map carrier_type -> carrier_cost_usd."""
    return {
        row['carrier_type']: float(row['carrier_cost_usd'])
        for row in carrier_cost_data
    }


def build_payment_map(billing_data: list[dict]) -> dict:
    """Build payment lookup with alias normalization."""
    # Group by normalized label, track effective_month for latest active
    payment_entries = []
    for row in billing_data:
        if row.get('is_active', 'true').lower() != 'true':
            continue
        entry = {
            'label': row['assay_label'],
            'label_norm': row['assay_label'].lower().replace('-', ' ').replace('_', ' '),
            'payment': float(row['payment_per_run_per_lab_usd']),
            'effective_month': row.get('effective_month', '1970-01')
        }
        payment_entries.append(entry)
    
    # Build normalized lookup (use latest effective_month)
    payment_map = {}
    for entry in sorted(payment_entries, key=lambda e: e['effective_month']):
        payment_map[entry['label_norm']] = entry['payment']
        payment_map[entry['label'].lower()] = entry['payment']
    
    return payment_map


def match_payment(assay: dict, payment_map: dict) -> float | None:
    """Match payment using assay_name and aliases."""
    # Try assay_name variations
    name = assay.get('assay_name', '')
    for variant in [name.lower(), name.lower().replace('-', ' ')]:
        if variant in payment_map:
            return payment_map[variant]
    
    # Try aliases
    for alias in assay.get('aliases', []):
        for variant in [alias.lower(), alias.lower().replace('-', ' ')]:
            if variant in payment_map:
                return payment_map[variant]
    
    return None


def resolve_labs(overrides: list[dict], assay_id: str, default_labs: int) -> int:
    """Resolve lab count using approval workflow."""
    # Filter to target assay
    assay_rows = [
        row for row in overrides
        if row.get('assay_id') == assay_id
    ]
    
    if not assay_rows:
        return default_labs
    
    # Filter to approved only
    approved = [
        row for row in assay_rows
        if row.get('status') == 'approved'
    ]
    
    if not approved:
        return default_labs
    
    # Select highest revision
    highest = max(approved, key=lambda r: int(r.get('revision', 0)))
    
    return int(highest.get('active_labs', default_labs))


def extract_assays(manifest: dict) -> list[dict]:
    """Extract flat list of assays from regions."""
    assays = []
    for region in manifest.get('regions', []):
        for assay in region.get('assays', []):
            assays.append(assay)
    return assays


def calculate_assay_margins(
    assay: dict,
    carrier_cost_map: dict,
    payment_map: dict,
    overrides: list[dict],
    config: dict
) -> dict | None:
    """Calculate margins for one assay under both kit policies."""
    
    # Filter by in_scope
    if not assay.get('in_scope', False):
        return None
    
    # Extract values
    assay_id = assay['assay_id']
    name = assay['assay_name']
    price_per_1000 = float(assay['reagent_price_per_1000_tests_usd'])
    carrier_type = assay['carrier_type']
    tests_small = int(assay['tests_per_lab_per_run_small'])
    tests_bulk = int(assay['tests_per_lab_per_run_bulk'])
    default_labs = int(assay['default_active_labs'])
    
    # Resolve labs
    labs = resolve_labs(overrides, assay_id, default_labs)
    
    # Look up costs and payment
    carrier_cost = carrier_cost_map.get(carrier_type)
    if carrier_cost is None:
        raise ValueError(f"Unknown carrier_type: {carrier_type} for {assay_id}")
    
    payment = match_payment(assay, payment_map)
    if payment is None:
        raise ValueError(f"Could not match payment for {assay_id} with aliases: {assay.get('aliases', [])}")
    
    # Config constants
    runs_small = config['runs_per_year_small']
    runs_bulk = config['runs_per_year_bulk']
    
    # Annual tests and reagent cost (constant across policies)
    annual_tests_small = tests_small * runs_small * labs
    annual_tests_bulk = tests_bulk * runs_bulk * labs
    
    # Verify: annual tests should be equal (same total volume)
    # If not, use small-kit as baseline
    annual_reagent_cost = annual_tests_small * price_per_1000 / 1000
    
    # Scenario calculations
    # Small-kit: more runs, fewer tests per run
    annual_carrier_small = carrier_cost * runs_small * labs
    annual_revenue_small = payment * runs_small * labs
    margin_small = annual_revenue_small - annual_reagent_cost - annual_carrier_small
    
    # Bulk-kit: fewer runs, more tests per run
    annual_carrier_bulk = carrier_cost * runs_bulk * labs
    annual_revenue_bulk = payment * runs_bulk * labs
    margin_bulk = annual_revenue_bulk - annual_reagent_cost - annual_carrier_bulk
    
    return {
        'assay_id': assay_id,
        'assay_name': name,
        'carrier_type': carrier_type,
        'active_labs': labs,
        'reagent_price_per_1000_tests_usd': price_per_1000,
        'tests_per_lab_per_run_small': tests_small,
        'tests_per_lab_per_run_bulk': tests_bulk,
        'payment_per_run_per_lab_usd': payment,
        'carrier_cost_usd': carrier_cost,
        'annual_reagent_cost_small_kit_usd': annual_reagent_cost,
        'annual_reagent_cost_bulk_kit_usd': annual_reagent_cost,  # Same
        'annual_carrier_cost_small_kit_usd': annual_carrier_small,
        'annual_carrier_cost_bulk_kit_usd': annual_carrier_bulk,
        'annual_revenue_small_kit_usd': annual_revenue_small,
        'annual_revenue_bulk_kit_usd': annual_revenue_bulk,
        'annual_margin_small_kit_usd': margin_small,
        'annual_margin_bulk_kit_usd': margin_bulk,
        'annual_margin_difference_bulk_minus_small_usd': margin_bulk - margin_small
    }


def main():
    # Default configuration - ADAPT to your task
    config = {
        'runs_per_year_small': 24,
        'runs_per_year_bulk': 12,
        'switch_threshold_usd': 7000,
        'scenario_a_name': 'small_kit',
        'scenario_b_name': 'bulk_kit',
        'recommendation_enum': {
            'keep_a': 'keep_small_kit',
            'switch_to_b': 'adopt_bulk_kit'
        }
    }
    
    # Override with config file if provided
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            config.update(json.load(f))
    
    # Load data
    manifest = load_json('assay_manifest.json')
    carrier_costs = load_csv('carrier_cost.csv')
    billing = load_csv('billing.csv')
    overrides = load_csv('lab_overrides.csv')
    
    # Build lookups
    carrier_cost_map = build_carrier_cost_map(carrier_costs)
    payment_map = build_payment_map(billing)
    
    # Extract and process assays
    assays = extract_assays(manifest)
    
    results = []
    for assay in assays:
        try:
            result = calculate_assay_margins(
                assay, carrier_cost_map, payment_map, overrides, config
            )
            if result:
                results.append(result)
        except ValueError as e:
            print(f"Warning: {e}", file=sys.stderr)
    
    if not results:
        print("No assays with in_scope=true found", file=sys.stderr)
        sys.exit(1)
    
    # Calculate totals
    total_small = sum(r['annual_margin_small_kit_usd'] for r in results)
    total_bulk = sum(r['annual_margin_bulk_kit_usd'] for r in results)
    abs_diff = abs(total_bulk - total_small)
    
    # Decision - USE configured enum values, verify against task schema
    rec = config['recommendation_enum']
    if abs_diff >= config['switch_threshold_usd'] and total_bulk > total_small:
        recommendation = rec['switch_to_b']
    else:
        recommendation = rec['keep_a']
    
    # Build output
    a_key = config['scenario_a_name']
    b_key = config['scenario_b_name']
    
    output = {
        'assumptions': {
            f'runs_per_year_{a_key}': config['runs_per_year_small'],
            f'runs_per_year_{b_key}': config['runs_per_year_bulk'],
            'switch_threshold_usd': config['switch_threshold_usd']
        },
        'assays': results,
        'totals': {
            f'total_{a_key}_margin_usd': total_small,
            f'total_{b_key}_margin_usd': total_bulk,
            'absolute_difference_usd': abs_diff
        },
        'recommendation': recommendation
    }
    
    # Write outputs
    with open('reagent_policy_analysis.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    summary = f"""## Reagent Policy Analysis Summary

- **{a_key} model**: ${total_small:,.2f} USD annual margin
- **{b_key} model**: ${total_bulk:,.2f} USD annual margin
- **Absolute difference**: ${abs_diff:,.2f} USD
- **Decision**: `{recommendation}`

Threshold: ${config['switch_threshold_usd']:,.2f} USD
"""
    with open('reagent_policy_summary.md', 'w') as f:
        f.write(summary)
    
    print(f"Analysis complete!")
    print(f"{a_key} margin: ${total_small:,.2f}")
    print(f"{b_key} margin: ${total_bulk:,.2f}")
    print(f"Decision: {recommendation}")


if __name__ == '__main__':
    main()
