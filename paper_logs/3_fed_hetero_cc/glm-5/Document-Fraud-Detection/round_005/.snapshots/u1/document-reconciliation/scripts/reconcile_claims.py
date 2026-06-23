#!/usr/bin/env python3
"""
Template for multi-source document/claim validation.
Customize DATA_PATHS and RECORD_EXTRACTOR for your task.
"""

import json
import pandas as pd
from typing import Dict, List, Any, Optional

def load_entities(path: str, sheet_name: str = 0) -> Dict[str, Dict]:
    """Load entity directory from Excel."""
    df = pd.read_excel(path, sheet_name=sheet_name)
    entities = {}
    for _, row in df.iterrows():
        eid = str(row['employee_id']).strip()
        entities[eid] = {
            'name': str(row['employee_name']).strip(),
            'bank_account': str(row['bank_account']).strip(),
            'department': str(row.get('department_code', '')).strip()
        }
    return entities

def load_providers(path: str, sheet_name: str = 0) -> Dict[str, Dict]:
    """Load provider directory from Excel (for fleet/vendor validation)."""
    df = pd.read_excel(path, sheet_name=sheet_name)
    providers = {}
    for _, row in df.iterrows():
        pid = str(row['provider_id']).strip()
        providers[pid] = {
            'name': str(row['provider_name']).strip(),
            'payment_account': str(row['payment_account']).strip(),
            'depot_region': str(row.get('depot_region', '')).strip()
        }
    return providers

def load_aliases(path: str, sheet_name: str = 'aliases') -> Dict[str, str]:
    """Load alias table: alias_name -> entity_id."""
    try:
        df = pd.read_excel(path, sheet_name=sheet_name)
        aliases = {}
        for _, row in df.iterrows():
            alias_name = str(row['alias_name']).strip().lower()
            entity_id = str(row['provider_id' if 'provider_id' in row else 'contractor_id']).strip()
            aliases[alias_name] = entity_id
        return aliases
    except:
        return {}

def load_approvals(path: str) -> Dict[str, Dict]:
    """Load trip/approval records from CSV."""
    df = pd.read_csv(path)
    approvals = {}
    for _, row in df.iterrows():
        tid = str(row['trip_id']).strip()
        approvals[tid] = {
            'amount': float(row['approved_amount']),
            'employee_id': str(row['employee_id']).strip(),
            'status': str(row.get('status', 'active')).strip().lower()
        }
    return approvals

def load_nested_orders(path: str) -> Dict[str, Dict]:
    """Load orders from nested JSON structure (e.g., orders under depots)."""
    with open(path, 'r') as f:
        data = json.load(f)
    
    orders = {}
    # Flatten nested structure - adapt key names to your JSON
    for depot in data.get('depots', []):
        depot_code = depot.get('depot_code', '')
        for order in depot.get('orders', []):
            order_id = str(order['order_id']).strip()
            orders[order_id] = {
                'provider_id': str(order['provider_id']).strip(),
                'approved_charge': float(order['approved_charge']),
                'lifecycle': str(order.get('lifecycle', 'active')).strip().lower(),
                'depot_code': depot_code
            }
    return orders

def load_revisions(path: str) -> Dict[str, float]:
    """Load revision history and return highest approved amount per reference."""
    df = pd.read_csv(path)
    result = {}
    for wo_id in df['work_order_id'].unique():
        wo_revisions = df[(df['work_order_id'] == wo_id) & 
                          (df['approval_state'] == 'approved')]
        if len(wo_revisions) > 0:
            highest = wo_revisions.loc[wo_revisions['revision'].idxmax()]
            result[wo_id] = float(highest['revised_amount'])
    return result

def load_amendments(path: str) -> Dict[str, float]:
    """Load amendments and return approved amended amounts per order."""
    df = pd.read_csv(path)
    result = {}
    for order_id in df['order_id'].unique():
        order_amendments = df[(df['order_id'] == order_id) & 
                              (df['decision'] == 'approved')]
        if len(order_amendments) > 0:
            highest = order_amendments.loc[order_amendments['amendment_no'].idxmax()]
            result[order_id] = float(highest['amended_charge'])
    return result

def normalize_name(name: str) -> str:
    return name.lower().strip().replace('  ', ' ')

def edit_distance(s1: str, s2: str) -> int:
    """Levenshtein distance for fuzzy matching."""
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def find_entity_by_name(name: str, entities: Dict, aliases: Dict = None) -> Optional[str]:
    """Find entity_id by name with alias lookup and fuzzy matching."""
    norm = normalize_name(name)
    
    # 1. Check alias table first
    if aliases and norm in aliases:
        return aliases[norm]
    
    # 2. Exact match on legal names
    for eid, ent in entities.items():
        if normalize_name(ent['name']) == norm:
            return eid
    
    # 3. Fuzzy match
    best_match = None
    best_dist = float('inf')
    for eid, ent in entities.items():
        dist = edit_distance(norm, normalize_name(ent['name']))
        if dist < best_dist:
            best_dist = dist
            best_match = eid
    
    if best_dist <= 1 and len(norm) > 5:
        return best_match
    return None

def get_approved_amount(ref_id: str, approvals: Dict, revisions: Dict = None, amendments: Dict = None) -> tuple:
    """Get approved amount, considering revisions and amendments. Returns (amount, status)."""
    if ref_id not in approvals:
        return (None, None)
    
    ref = approvals[ref_id]
    status = ref.get('lifecycle', ref.get('status', 'active'))
    
    # Check for amendment override first (more recent)
    if amendments and ref_id in amendments:
        return (amendments[ref_id], status)
    
    # Check for revision override
    if revisions and ref_id in revisions:
        return (revisions[ref_id], status)
    
    return (ref['approved_charge' if 'approved_charge' in ref else 'amount'], status)

def validate_record(record: Dict, entities: Dict, approvals: Dict, 
                    aliases: Dict = None, revisions: Dict = None, 
                    amendments: Dict = None) -> Optional[str]:
    """
    Validate a record. Returns reason string if invalid, None if valid.

    Violation priority: Unknown Entity -> Account Mismatch -> Invalid Reference -> 
    Invalid Status -> Owner Mismatch -> Amount Mismatch
    """
    ent_id = find_entity_by_name(record['employee_name'], entities, aliases)

    # 1. Unknown Entity
    if ent_id is None:
        return "Unknown Employee"

    ent = entities[ent_id]

    # 2. Account Mismatch
    if record.get('bank_account') != ent['bank_account']:
        return "Account Mismatch"

    ref_id = record.get('trip_id') or record.get('order_id')

    # 3. Invalid Reference ID
    if ref_id not in approvals:
        return "Invalid Trip ID"
    
    approved_amount, status = get_approved_amount(ref_id, approvals, revisions, amendments)
    
    # 4. Invalid Reference Status
    if status not in ('active', 'approved'):
        return "Invalid Work Order"

    ref = approvals[ref_id]

    # 5. Owner Mismatch
    owner_field = 'provider_id' if 'provider_id' in ref else 'employee_id'
    if ref[owner_field] != ent_id:
        return "Traveler Mismatch"

    # 6. Amount Mismatch (tolerance: $0.01)
    claimed = record.get('claimed_amount') or record.get('chargeback_total', 0)
    if abs(claimed - approved_amount) > 0.01:
        return "Amount Mismatch"

    return None

def main():
    # CONFIGURE THESE PATHS
    DATA_PATHS = {
        'entities': '/root/employee_directory.xlsx',
        'aliases_sheet': 'aliases',  # Set to None if no alias sheet
        'approvals': '/root/trip_approvals.csv',
        'revisions': '/root/trip_revisions.csv',  # Set to None if no revisions
        'amendments': '/root/maintenance_adjustments.csv',  # Set to None if no amendments
        'orders_json': '/root/maintenance_orders.json',  # For nested JSON orders
        'records': '/root/expense_claims.pdf',  # Extract manually or with PDF parser
        'output': '/root/discrepancies.json'
    }

    # Load reference data
    entities = load_entities(DATA_PATHS['entities'])
    aliases = load_aliases(DATA_PATHS['entities'], DATA_PATHS['aliases_sheet']) if DATA_PATHS['aliases_sheet'] else {}
    
    # Choose based on data format
    if DATA_PATHS.get('orders_json'):
        approvals = load_nested_orders(DATA_PATHS['orders_json'])
    else:
        approvals = load_approvals(DATA_PATHS['approvals'])
    
    revisions = load_revisions(DATA_PATHS['revisions']) if DATA_PATHS.get('revisions') else {}
    amendments = load_amendments(DATA_PATHS['amendments']) if DATA_PATHS.get('amendments') else {}

    # TODO: Extract records from PDF - populate this list
    # Each record needs: employee_name/provider_name, claimed_amount/chargeback_total, 
    # bank_account/payment_account, trip_id/order_id, record_id/page_number
    records = []

    # Validate and collect violations
    violations = []
    for record in records:
        reason = validate_record(record, entities, approvals, aliases, revisions, amendments)
        if reason:
            violations.append({
                'claim_page_number': record.get('page_number'),
                'employee_name': record['employee_name'],
                'claimed_amount': record['claimed_amount'],
                'bank_account': record['bank_account'],
                'trip_id': record['trip_id'],
                'reason': reason
            })

    with open(DATA_PATHS['output'], 'w') as f:
        json.dump(violations, f, indent=2)

    print(f"Found {len(violations)} violations, written to {DATA_PATHS['output']}")

if __name__ == '__main__':
    main()
