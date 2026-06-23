#!/usr/bin/env python3
"""
Template for multi-source document/claim validation.
Customize DATA_PATHS and RECORD_EXTRACTOR for your task.
"""

import json
import pandas as pd
from typing import Dict, List, Any, Optional

def load_entities(path: str) -> Dict[str, Dict]:
    """Load entity directory from Excel."""
    df = pd.read_excel(path)
    entities = {}
    for _, row in df.iterrows():
        eid = str(row['employee_id']).strip()
        entities[eid] = {
            'name': str(row['employee_name']).strip(),
            'bank_account': str(row['bank_account']).strip(),
            'department': str(row.get('department_code', '')).strip()
        }
    return entities

def load_approvals(path: str) -> Dict[str, Dict]:
    """Load trip/approval records from CSV."""
    df = pd.read_csv(path)
    approvals = {}
    for _, row in df.iterrows():
        tid = str(row['trip_id']).strip()
        approvals[tid] = {
            'amount': float(row['approved_amount']),
            'employee_id': str(row['employee_id']).strip()
        }
    return approvals

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

def find_entity_by_name(name: str, entities: Dict) -> Optional[str]:
    """Find entity_id by name with fuzzy matching (edit distance <= 1)."""
    norm = normalize_name(name)

    # Exact match first
    for eid, ent in entities.items():
        if normalize_name(ent['name']) == norm:
            return eid

    # Fuzzy match
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

def validate_record(record: Dict, entities: Dict, approvals: Dict) -> Optional[str]:
    """
    Validate a record. Returns reason string if invalid, None if valid.

    Violation priority: Unknown Entity -> Account Mismatch -> Invalid Reference -> Owner Mismatch -> Amount Mismatch
    """
    ent_id = find_entity_by_name(record['employee_name'], entities)

    # 1. Unknown Entity
    if ent_id is None:
        return "Unknown Employee"

    ent = entities[ent_id]

    # 2. Account Mismatch
    if record.get('bank_account') != ent['bank_account']:
        return "Account Mismatch"

    ref_id = record.get('trip_id')

    # 3. Invalid Reference ID
    if ref_id not in approvals:
        return "Invalid Trip ID"

    ref = approvals[ref_id]

    # 4. Owner Mismatch
    if ref['employee_id'] != ent_id:
        return "Traveler Mismatch"

    # 5. Amount Mismatch (tolerance: $0.01)
    if abs(record.get('claimed_amount', 0) - ref['amount']) > 0.01:
        return "Amount Mismatch"

    return None

def main():
    # CONFIGURE THESE PATHS
    DATA_PATHS = {
        'entities': '/root/employee_directory.xlsx',
        'approvals': '/root/trip_approvals.csv',
        'records': '/root/expense_claims.pdf',  # Extract manually or with PDF parser
        'output': '/root/discrepancies.json'
    }

    # Load reference data
    entities = load_entities(DATA_PATHS['entities'])
    approvals = load_approvals(DATA_PATHS['approvals'])

    # TODO: Extract records from PDF - populate this list
    # Each record needs: employee_name, claimed_amount, bank_account, trip_id, record_id/page_number
    records = []

    # Validate and collect violations
    violations = []
    for record in records:
        reason = validate_record(record, entities, approvals)
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