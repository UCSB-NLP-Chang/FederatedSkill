#!/usr/bin/env python3
"""Calculate pharmacy dispensing margins from CSV inputs.

Configurable for different input schemas, fill sizes, and packaging models
(vial-based, blister card, or mailer-based).
"""

import argparse
import csv
import json
import re
from decimal import Decimal, ROUND_HALF_UP


def load_csv(filepath):
    """Load CSV file and return list of dicts."""
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)


def currency(value):
    """Round to 2 decimal places for currency."""
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def detect_column(headers, patterns, default=None):
    """Find column matching any pattern in patterns."""
    for h in headers:
        for p in patterns:
            if p.lower() in h.lower():
                return h
    return default


def extract_patient_count(column_name):
    """Extract patient count from column name like 'reimbursement_per_fill_300_patients_usd'."""
    match = re.search(r'(\d+)_patients', column_name)
    if match:
        return int(match.group(1))
    return None


def detect_packaging_model(acquisition_headers):
    """Detect whether this is vial-based, blister card, or mailer packaging."""
    for h in acquisition_headers:
        h_lower = h.lower()
        if any(p in h_lower for p in ['mailer_format', 'mailer']):
            return 'mailer'
        if any(p in h_lower for p in ['blister', 'card_count', 'cards_per']):
            return 'blister_card'
        if any(p in h_lower for p in ['vial_size', 'canister_size', 'dram']):
            return 'vial'
    return 'unknown'


def calculate_margins(acquisition_path, packaging_path, reimbursement_paths,
                      fill_days_a=90, fill_days_b=100,
                      patients_per_medication=None,
                      col_medication=None, col_price=None, col_packaging_indicator=None,
                      col_packaging_cost=None, col_reimbursement=None,
                      additional_revenue_cols=None):
    """
    Calculate annual margins for two dispensing cycle options.
    
    Supports vial-based, blister card, and mailer packaging models.
    Supports multiple revenue components (base_payment + service_fee).
    
    Args:
        acquisition_path: Path to acquisition/wholesale price CSV
        packaging_path: Path to packaging/vial/card/mailer price CSV
        reimbursement_paths: Path or list of paths to reimbursement/payment CSVs
        fill_days_a: First cycle size in days
        fill_days_b: Second cycle size in days
        patients_per_medication: Patients per medication (auto-detected if not specified)
        col_medication: Column name for medication
        col_price: Column name for price per 1000
        col_packaging_indicator: Column name for packaging indicator
        col_packaging_cost: Column name for packaging cost
        col_reimbursement: Column name for primary reimbursement
        additional_revenue_cols: List of additional revenue column names to sum
    
    Returns dict with per-medication and total margins.
    """
    acquisition = load_csv(acquisition_path)
    packaging = load_csv(packaging_path)
    
    # Handle single path or list of paths for reimbursement
    if isinstance(reimbursement_paths, str):
        reimbursement_paths = [reimbursement_paths]
    
    reimbursement_data = {}
    for path in reimbursement_paths:
        data = load_csv(path)
        for row in data:
            med = row.get(col_medication) or row.get(list(row.keys())[0])
            if med not in reimbursement_data:
                reimbursement_data[med] = {}
            reimbursement_data[med].update(row)
    
    # Auto-detect columns if not specified
    acq_headers = list(acquisition[0].keys()) if acquisition else []
    pkg_headers = list(packaging[0].keys()) if packaging else []
    reimb_headers = list(reimbursement_data.values())[0].keys() if reimbursement_data else []
    
    # Detect medication column
    col_medication = col_medication or detect_column(acq_headers, ['medication', 'therapy', 'drug'])
    
    # Detect price column
    col_price = col_price or detect_column(acq_headers, ['price_per_1000', 'price'], 
                                           acq_headers[1] if len(acq_headers) > 1 else None)
    
    # Detect packaging model and appropriate columns
    packaging_model = detect_packaging_model(acq_headers)
    if col_packaging_indicator is None:
        if packaging_model == 'mailer':
            col_packaging_indicator = detect_column(acq_headers, ['mailer_format', 'mailer'])
        elif packaging_model == 'blister_card':
            col_packaging_indicator = detect_column(acq_headers, ['blister', 'card_count', 'cards_per'])
        else:
            col_packaging_indicator = detect_column(acq_headers, ['vial_size', 'canister_size', 'container_size', 'dram'])
    
    # Detect packaging cost column
    col_packaging_cost = col_packaging_cost or detect_column(pkg_headers, ['cost', 'price'])
    
    # Detect packaging indicator in packaging file
    col_pkg_indicator = detect_column(pkg_headers, ['mailer_format', 'mailer', 'blister', 'card_count', 'cards_per', 'vial_size', 'canister_size', 'size', 'dram'])
    
    # Detect reimbursement columns
    col_reimbursement = col_reimbursement or detect_column(reimb_headers, ['base_payment', 'reimbursement'])
    
    # Detect additional revenue columns (service_fee, etc.)
    if additional_revenue_cols is None:
        additional_revenue_cols = []
        for h in reimb_headers:
            if 'service_fee' in h.lower() or ('fee' in h.lower() and 'per_fill' in h.lower()):
                additional_revenue_cols.append(h)
    
    # Extract patient count from reimbursement column if not specified
    if patients_per_medication is None and col_reimbursement:
        patients_per_medication = extract_patient_count(col_reimbursement) or 240
    
    # Index packaging by indicator value (string for mailer, int for others)
    pkg_by_indicator = {}
    for row in packaging:
        indicator_key = None
        for h in pkg_headers:
            h_lower = h.lower()
            if any(p in h_lower for p in ['mailer_format', 'mailer', 'blister', 'card_count', 'cards_per', 'vial_size', 'canister_size', 'size', 'dram']):
                indicator_key = row[h]
                # Try to convert to int for numeric indicators
                try:
                    indicator_key = int(float(row[h]))
                except (ValueError, TypeError):
                    pass  # Keep as string for mailer format
            elif 'cost' in h_lower or 'price' in h_lower:
                if indicator_key is not None:
                    pkg_by_indicator[indicator_key] = float(row[h])
    
    # Calculate fills per year
    fills_a = round(365 / fill_days_a, 2)
    fills_b = round(365 / fill_days_b, 2)
    
    results = {
        'assumptions': {
            'patients_per_medication': patients_per_medication,
            'packaging_model': packaging_model,
            f'fills_per_year_{fill_days_a}_day': fills_a,
            f'fills_per_year_{fill_days_b}_day': fills_b
        },
        'medications': {},
        'totals': {f'{fill_days_a}_day': 0.0, f'{fill_days_b}_day': 0.0}
    }
    
    for row in acquisition:
        med = row[col_medication]
        price_per_1000 = float(row[col_price])
        
        # Get packaging indicator value
        pkg_indicator = row[col_packaging_indicator]
        try:
            pkg_indicator = int(float(pkg_indicator))
        except (ValueError, TypeError):
            pass  # Keep as string for mailer format
        
        # Cost per unit dose
        cost_per_dose = price_per_1000 / 1000
        
        # Per-fill acquisition cost (assume 1 dose per day)
        acq_cost_a = cost_per_dose * fill_days_a
        acq_cost_b = cost_per_dose * fill_days_b
        
        # Packaging cost
        pkg_cost = pkg_by_indicator.get(pkg_indicator, 0)
        
        # Total reimbursement (sum all revenue components)
        reimb_data = reimbursement_data.get(med, {})
        reimb = float(reimb_data.get(col_reimbursement, 0))
        for add_col in additional_revenue_cols:
            reimb += float(reimb_data.get(add_col, 0))
        
        # Per-fill margins
        margin_a_per_fill = reimb - acq_cost_a - pkg_cost
        margin_b_per_fill = reimb - acq_cost_b - pkg_cost
        
        # Annual margins
        annual_margin_a = margin_a_per_fill * fills_a * patients_per_medication
        annual_margin_b = margin_b_per_fill * fills_b * patients_per_medication
        
        results['medications'][med] = {
            f'margin_{fill_days_a}_day': currency(annual_margin_a),
            f'margin_{fill_days_b}_day': currency(annual_margin_b),
            'difference': currency(annual_margin_a - annual_margin_b)
        }
        
        results['totals'][f'{fill_days_a}_day'] += annual_margin_a
        results['totals'][f'{fill_days_b}_day'] += annual_margin_b
    
    results['totals'][f'{fill_days_a}_day'] = currency(results['totals'][f'{fill_days_a}_day'])
    results['totals'][f'{fill_days_b}_day'] = currency(results['totals'][f'{fill_days_b}_day'])
    results['totals']['difference'] = currency(results['totals'][f'{fill_days_a}_day'] - results['totals'][f'{fill_days_b}_day'])
    
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate pharmacy dispensing margins')
    parser.add_argument('acquisition_csv', help='Path to acquisition/wholesale price CSV')
    parser.add_argument('packaging_csv', help='Path to packaging/vial/card/mailer price CSV')
    parser.add_argument('reimbursement_csv', nargs='+', help='Path to reimbursement/payment CSV(s)')
    parser.add_argument('--fill-days-a', type=int, default=90, help='First cycle size in days')
    parser.add_argument('--fill-days-b', type=int, default=100, help='Second cycle size in days')
    parser.add_argument('--patients', type=int, help='Patients per medication (auto-detected if not specified)')
    args = parser.parse_args()
    
    results = calculate_margins(
        args.acquisition_csv, args.packaging_csv, args.reimbursement_csv,
        fill_days_a=args.fill_days_a, fill_days_b=args.fill_days_b,
        patients_per_medication=args.patients
    )
    print(json.dumps(results, indent=2))
