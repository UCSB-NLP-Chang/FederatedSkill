#!/usr/bin/env python3
"""
Calculate refill cycle margins from pharmacy cost/reimbursement data.

Usage: python3 calculate_margins.py [config.json]

Expects input files in working directory:
- acquisition_cost.csv
- packaging_cost.csv  
- reimbursement.csv

Outputs:
- cycle_margin_analysis.json (detailed results)
- cycle_margin_summary.md (human summary)
"""

import csv
import json
import sys
from pathlib import Path


def load_csv(path: str) -> list[dict]:
    """Load CSV, return list of dicts."""
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def build_packaging_map(packaging_data: list[dict]) -> dict:
    """Map canister_size_units -> packaging_cost_usd."""
    return {
        int(row['canister_size_units']): float(row['packaging_cost_usd'])
        for row in packaging_data
    }


def calculate_therapy_margins(
    therapy: dict,
    packaging_map: dict,
    config: dict
) -> dict:
    """Calculate margins for one therapy under both fill cycles."""
    
    # Extract values
    name = therapy['therapy']
    price_per_1000 = float(therapy['price_per_1000_doses_usd'])
    canister_size = int(therapy['canister_size_units'])
    reimbursement_per_fill = float(therapy['reimbursement_per_fill_240_patients_usd'])
    
    packaging_cost = packaging_map[canister_size]
    
    # Config constants
    patients = config['patients_per_therapy']
    fills_30 = config['fills_per_year_30_day']  # typically 12
    fills_90 = config['fills_per_year_90_day']  # typically 4
    doses_30 = config['doses_per_fill_30_day']   # typically 60
    doses_90 = config['doses_per_fill_90_day']   # typically 180
    
    # Annual doses (same for both cycles)
    annual_doses = doses_30 * fills_30  # = doses_90 * fills_90 = 720
    
    # Annual drug cost (same for both - based on total doses)
    annual_drug_cost = annual_doses * price_per_1000 / 1000 * patients
    
    # Annual packaging costs
    annual_packaging_30 = packaging_cost * fills_30 * patients
    annual_packaging_90 = packaging_cost * fills_90 * patients
    
    # Annual reimbursement
    annual_reimbursement_30 = reimbursement_per_fill * fills_30
    annual_reimbursement_90 = reimbursement_per_fill * fills_90
    
    # Annual margins
    margin_30 = annual_reimbursement_30 - annual_drug_cost - annual_packaging_30
    margin_90 = annual_reimbursement_90 - annual_drug_cost - annual_packaging_90
    
    return {
        'therapy': name,
        'price_per_1000_doses_usd': price_per_1000,
        'canister_size_units': canister_size,
        'packaging_cost_usd': packaging_cost,
        'reimbursement_per_fill_240_patients_usd': reimbursement_per_fill,
        'annual_drug_cost_30_day_usd': annual_drug_cost,
        'annual_drug_cost_90_day_usd': annual_drug_cost,  # Same
        'annual_packaging_cost_30_day_usd': annual_packaging_30,
        'annual_packaging_cost_90_day_usd': annual_packaging_90,
        'annual_reimbursement_30_day_usd': annual_reimbursement_30,
        'annual_reimbursement_90_day_usd': annual_reimbursement_90,
        'annual_margin_30_day_usd': margin_30,
        'annual_margin_90_day_usd': margin_90,
        'annual_margin_difference_90_minus_30_usd': margin_90 - margin_30
    }


def main():
    # Default configuration
    config = {
        'patients_per_therapy': 240,
        'fills_per_year_30_day': 12,
        'fills_per_year_90_day': 4,
        'doses_per_fill_30_day': 60,
        'doses_per_fill_90_day': 180,
        'switch_threshold_usd': 12000
    }
    
    # Override with config file if provided
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            config.update(json.load(f))
    
    # Load data
    therapies = load_csv('acquisition_cost.csv')
    packaging = load_csv('packaging_cost.csv')
    reimbursements = load_csv('reimbursement.csv')
    
    # Build packaging lookup
    packaging_map = build_packaging_map(packaging)
    
    # Merge reimbursement data into therapy records
    therapy_map = {t['therapy']: t for t in therapies}
    for r in reimbursements:
        name = r['therapy']
        if name in therapy_map:
            therapy_map[name]['reimbursement_per_fill_240_patients_usd'] = r['reimbursement_per_fill_240_patients_usd']
    
    # Calculate margins for each therapy
    results = []
    for therapy in therapies:
        result = calculate_therapy_margins(therapy, packaging_map, config)
        results.append(result)
    
    # Calculate totals
    total_30 = sum(r['annual_margin_30_day_usd'] for r in results)
    total_90 = sum(r['annual_margin_90_day_usd'] for r in results)
    abs_diff = abs(total_90 - total_30)
    
    # Decision
    recommendation = 'switch_to_90_day' if abs_diff >= config['switch_threshold_usd'] and total_90 > total_30 else 'keep_30_day'
    
    # Build output
    output = {
        'assumptions': config,
        'therapies': results,
        'totals': {
            'total_30_day_margin_usd': total_30,
            'total_90_day_margin_usd': total_90,
            'absolute_difference_usd': abs_diff
        },
        'recommendation': recommendation
    }
    
    # Write JSON output
    with open('cycle_margin_analysis.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    # Write markdown summary
    summary = f"""## Refill Cycle Margin Analysis Summary

- Total 30-day margin: ${total_30:,.2f} USD
- Total 90-day margin: ${total_90:,.2f} USD
- Absolute difference: ${abs_diff:,.2f} USD
- Final decision: `{recommendation}`

The analysis shows the financial impact of switching all therapies from 30-day to 90-day fill cycles.
"""
    with open('cycle_margin_summary.md', 'w') as f:
        f.write(summary)
    
    print(f"Files created successfully!")
    print(f"Total 30-day margin: ${total_30:,.2f}")
    print(f"Total 90-day margin: ${total_90:,.2f}")
    print(f"Absolute difference: ${abs_diff:,.2f}")
    print(f"Decision: {recommendation}")


if __name__ == '__main__':
    main()