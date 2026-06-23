#!/usr/bin/env python3
"""
Calculate mailer program margins comparing fill cycle scenarios.

Usage: python3 calculate_mailer_margins.py [config.json]

Expected input files:
- compound_cost.csv (medication, price_per_1000_doses_usd, mailer_format)
- mailer_cost.csv (mailer_format, mailer_cost_usd)
- base_payment.csv (medication, base_payment_per_fill_N_patients_usd)
- service_fee.csv (medication, service_fee_per_fill_N_patients_usd)

Outputs:
- mailer_policy_analysis.json (detailed results)
- mailer_policy_summary.md (human summary)
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


def build_mailer_cost_map(mailer_cost_data: list[dict]) -> dict:
    """Map mailer_format -> mailer_cost_usd."""
    return {
        row['mailer_format']: float(row['mailer_cost_usd'])
        for row in mailer_cost_data
    }


def parse_medication_data(
    compound_data: list[dict],
    base_payment_data: list[dict],
    service_fee_data: list[dict],
    mailer_cost_map: dict,
    config: dict
) -> list[dict]:
    """Parse and enrich medication records with costs and payments."""
    
    # Build lookup maps
    base_map = {r['medication']: float(r[f'base_payment_per_fill_{config["patients_per_medication"]}_patients_usd']) 
                for r in base_payment_data}
    fee_map = {r['medication']: float(r[f'service_fee_per_fill_{config["patients_per_medication"]}_patients_usd']) 
               for r in service_fee_data}
    
    results = []
    for row in compound_data:
        med = row['medication']
        mailer_format = row['mailer_format']
        
        result = {
            'medication': med,
            'price_per_1000_doses_usd': float(row['price_per_1000_doses_usd']),
            'mailer_format': mailer_format,
            'mailer_cost_usd': mailer_cost_map[mailer_format],
            'base_payment_per_fill_usd': base_map[med],
            'service_fee_per_fill_usd': fee_map[med],
            'total_payment_per_fill_usd': base_map[med] + fee_map[med]
        }
        results.append(result)
    
    return results


def calculate_scenario_margins(
    medications: list[dict],
    config: dict
) -> tuple[list[dict], dict]:
    """Calculate margins for both scenarios. Returns (per-medication results, totals)."""
    
    patients = config['patients_per_medication']
    fills_a = config['fills_per_year_45_day']  # 8
    fills_b = config['fills_per_year_90_day']  # 4
    
    results = []
    for med in medications:
        # Unpack
        price_per_1000 = med['price_per_1000_doses_usd']
        mailer_cost = med['mailer_cost_usd']
        total_payment = med['total_payment_per_fill_usd']
        
        # Annual doses (assume 1 dose/day)
        annual_doses = 1 * 365 * patients  # 54750 for 150 patients
        annual_drug_cost = annual_doses * price_per_1000 / 1000
        
        # Scenario A (45-day): 8 fills/year
        annual_mailer_a = mailer_cost * fills_a * patients
        annual_revenue_a = total_payment * fills_a
        margin_a = annual_revenue_a - annual_drug_cost - annual_mailer_a
        
        # Scenario B (90-day): 4 fills/year
        annual_mailer_b = mailer_cost * fills_b * patients
        annual_revenue_b = total_payment * fills_b
        margin_b = annual_revenue_b - annual_drug_cost - annual_mailer_b
        
        results.append({
            'medication': med['medication'],
            'price_per_1000_doses_usd': price_per_1000,
            'mailer_format': med['mailer_format'],
            'mailer_cost_usd': mailer_cost,
            'base_payment_per_fill_usd': med['base_payment_per_fill_usd'],
            'service_fee_per_fill_usd': med['service_fee_per_fill_usd'],
            'total_payment_per_fill_usd': total_payment,
            'annual_drug_cost_usd': annual_drug_cost,  # Same for both
            'annual_mailer_cost_45_day_usd': annual_mailer_a,
            'annual_mailer_cost_90_day_usd': annual_mailer_b,
            'annual_revenue_45_day_usd': annual_revenue_a,
            'annual_revenue_90_day_usd': annual_revenue_b,
            'annual_margin_45_day_usd': margin_a,
            'annual_margin_90_day_usd': margin_b,
            'annual_margin_difference_90_minus_45_usd': margin_b - margin_a
        })
    
    # Totals
    total_a = sum(r['annual_margin_45_day_usd'] for r in results)
    total_b = sum(r['annual_margin_90_day_usd'] for r in results)
    
    totals = {
        'total_45_day_margin_usd': total_a,
        'total_90_day_margin_usd': total_b,
        'absolute_difference_usd': abs(total_b - total_a)
    }
    
    return results, totals


def main():
    # Default configuration
    config = {
        'patients_per_medication': 150,
        'fills_per_year_45_day': 8,   # 365/45 ≈ 8
        'fills_per_year_90_day': 4,   # 365/90 ≈ 4
        'switch_threshold_usd': 8500
    }
    
    # Override with config file if provided
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            config.update(json.load(f))
    
    # Load data
    compound = load_csv('compound_cost.csv')
    mailer_costs = load_csv('mailer_cost.csv')
    base_payments = load_csv('base_payment.csv')
    service_fees = load_csv('service_fee.csv')
    
    # Build lookups
    mailer_cost_map = build_mailer_cost_map(mailer_costs)
    
    # Parse and enrich
    medications = parse_medication_data(
        compound, base_payments, service_fees, mailer_cost_map, config
    )
    
    # Calculate
    results, totals = calculate_scenario_margins(medications, config)
    
    # Decision - VERIFY enum values match task requirements
    abs_diff = totals['absolute_difference_usd']
    total_45 = totals['total_45_day_margin_usd']
    total_90 = totals['total_90_day_margin_usd']
    
    # Common patterns: keep_45_day / switch_to_90_day OR keep_45_day_cycle / switch_to_90_day_cycle
    if abs_diff >= config['switch_threshold_usd'] and total_90 > total_45:
        recommendation = 'switch_to_90_day'
    else:
        recommendation = 'keep_45_day'
    
    # Build output
    output = {
        'assumptions': {
            'patients_per_medication': config['patients_per_medication'],
            'fills_per_year_45_day': config['fills_per_year_45_day'],
            'fills_per_year_90_day': config['fills_per_year_90_day'],
            'switch_threshold_usd': config['switch_threshold_usd']
        },
        'medications': results,
        'totals': totals,
        'recommendation': recommendation
    }
    
    # Write outputs
    with open('mailer_policy_analysis.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    summary = f"""## Mailer Policy Analysis Summary

- **45-day model**: ${total_45:,.2f} USD annual margin
- **90-day model**: ${total_90:,.2f} USD annual margin
- **Absolute difference**: ${abs_diff:,.2f} USD
- **Decision**: `{recommendation}`

Threshold: ${config['switch_threshold_usd']:,.2f} USD
"""
    with open('mailer_policy_summary.md', 'w') as f:
        f.write(summary)
    
    print(f"Analysis complete!")
    print(f"45-day margin: ${total_45:,.2f}")
    print(f"90-day margin: ${total_90:,.2f}")
    print(f"Decision: {recommendation}")


if __name__ == '__main__':
    main()
