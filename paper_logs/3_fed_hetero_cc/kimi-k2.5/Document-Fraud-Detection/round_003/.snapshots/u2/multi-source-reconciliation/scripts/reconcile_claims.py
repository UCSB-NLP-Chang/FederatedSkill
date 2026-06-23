#!/usr/bin/env python3
"""
Template for multi-source claim/request validation.
Customize DATA_PATHS and CLAIM_EXTRACTOR for your task.

Supports: expense claims, honorarium requests, shift claims, or any similar
cross-reference validation between registry, approvals, and request documents.

Handles both direct lookups and crosswalk/indirection patterns.
"""

import json
import pandas as pd
from typing import Dict, List, Any, Optional

def load_registry(path: str, id_col: str = 'employee_id', name_col: str = 'employee_name', 
                  account_col: str = 'bank_account') -> Dict[str, Dict]:
    """Load entity registry from Excel.
    
    Args:
        path: Path to Excel file
        id_col: Column name for entity ID (e.g., 'employee_id', 'speaker_id', 'clinician_id')
        name_col: Column name for entity name (e.g., 'employee_name', 'speaker_name', 'clinician_name')
        account_col: Column name for payment account (e.g., 'bank_account', 'payment_account', 'payout_account')
    """
    df = pd.read_excel(path)
    entities = {}
    for _, row in df.iterrows():
        eid = str(row[id_col]).strip()
        entities[eid] = {
            'name': str(row[name_col]).strip(),
            'account': str(row[account_col]).strip(),
        }
    return entities

def load_approvals(path: str, code_col: str = 'trip_id', amount_col: str = 'approved_amount',
                   entity_col: str = 'employee_id') -> Dict[str, Dict]:
    """Load approvals from CSV.
    
    Args:
        path: Path to CSV file
        code_col: Column name for approval code (e.g., 'trip_id', 'approval_code', 'shift_code_internal')
        amount_col: Column name for approved amount (e.g., 'approved_amount', 'approved_fee', 'approved_pay')
        entity_col: Column name for entity ID (e.g., 'employee_id', 'speaker_id', 'clinician_id')
    """
    df = pd.read_csv(path)
    approvals = {}
    for _, row in df.iterrows():
        code = str(row[code_col]).strip()
        approvals[code] = {
            'amount': float(row[amount_col]),
            'entity_id': str(row[entity_col]).strip()
        }
    return approvals

def load_crosswalk(path: str, external_col: str = 'shift_ref', 
                   internal_col: str = 'shift_code_internal') -> Dict[str, str]:
    """Load crosswalk mapping from CSV (optional, for indirection patterns).
    
    Args:
        path: Path to CSV file
        external_col: Column name for external/reference code (e.g., 'shift_ref', 'external_code')
        internal_col: Column name for internal/authorization code (e.g., 'shift_code_internal', 'internal_code')
    
    Returns:
        Dict mapping external_code -> internal_code
    """
    df = pd.read_csv(path)
    crosswalk = {}
    for _, row in df.iterrows():
        external = str(row[external_col]).strip()
        internal = str(row[internal_col]).strip()
        crosswalk[external] = internal
    return crosswalk

def normalize_name(name: str) -> str:
    """Normalize name for fuzzy matching."""
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

def find_entity_by_name(name: str, entities: Dict, max_dist: int = 1, min_len: int = 5) -> Optional[str]:
    """Find entity_id by name with fuzzy matching.
    
    Args:
        name: Name to search for
        entities: Entity registry dict
        max_dist: Maximum edit distance to accept (default 1)
        min_len: Minimum name length to apply fuzzy matching (default 5)
    """
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
    
    if best_dist <= max_dist and len(norm) > min_len:
        return best_match
    return None

def validate_request(request: Dict, entities: Dict, approvals: Dict,
                     crosswalk: Optional[Dict[str, str]] = None,
                     unknown_label: str = "Unknown Entity",
                     account_label: str = "Account Mismatch",
                     invalid_ref_label: str = "Invalid Reference",
                     invalid_internal_label: str = "Invalid Internal Code",
                     ownership_label: str = "Ownership Mismatch",
                     amount_label: str = "Amount Mismatch") -> Optional[str]:
    """
    Validate a request. Returns reason string if invalid, None if valid.
    
    Priority: Unknown Entity → Account Mismatch → Invalid Reference → Invalid Internal Code → Ownership Mismatch → Amount Mismatch
    
    Args:
        request: Dict with entity_name, requested_amount, account, approval_code (or external_code if crosswalk provided)
        entities: Registry dict from load_registry
        approvals: Approvals dict from load_approvals
        crosswalk: Optional external→internal code mapping
        *_label: Custom labels for violation types
    """
    entity_id = find_entity_by_name(request['entity_name'], entities)
    
    # 1. Unknown Entity
    if entity_id is None:
        return unknown_label
    
    entity = entities[entity_id]
    
    # 2. Account Mismatch
    if request.get('account') != entity['account']:
        return account_label
    
    external_code = request.get('approval_code')  # may be external code
    
    # 3. Invalid Reference (external code not in crosswalk)
    if crosswalk is not None:
        if external_code not in crosswalk:
            return invalid_ref_label
        internal_code = crosswalk[external_code]
    else:
        internal_code = external_code
    
    # 4. Invalid Internal Code
    if internal_code not in approvals:
        return invalid_internal_label if crosswalk else invalid_ref_label
    
    approval = approvals[internal_code]
    
    # 5. Ownership Mismatch (compare entity_ids, not names)
    if approval['entity_id'] != entity_id:
        return ownership_label
    
    # 6. Amount Mismatch (tolerance: $0.01)
    if abs(request.get('requested_amount', 0) - approval['amount']) > 0.01:
        return amount_label
    
    return None

def main():
    # CONFIGURE THESE FOR YOUR TASK
    
    # Example: Expense claims (direct lookup)
    EXPENSE_CONFIG = {
        'registry_path': '/root/employee_directory.xlsx',
        'approvals_path': '/root/trip_approvals.csv',
        'output_path': '/root/expense_alerts.json',
        'use_crosswalk': False,
        'entity_id_col': 'employee_id',
        'entity_name_col': 'employee_name',
        'account_col': 'bank_account',
        'approval_code_col': 'trip_id',
        'amount_col': 'approved_amount',
        'labels': {
            'unknown': 'Unknown Employee',
            'account': 'Account Mismatch',
            'invalid': 'Invalid Trip ID',
            'ownership': 'Traveler Mismatch',
            'amount': 'Amount Mismatch'
        }
    }
    
    # Example: Honorarium requests (direct lookup)
    HONORARIUM_CONFIG = {
        'registry_path': '/root/speaker_registry.xlsx',
        'approvals_path': '/root/session_approvals.csv',
        'output_path': '/root/honorarium_flags.json',
        'use_crosswalk': False,
        'entity_id_col': 'speaker_id',
        'entity_name_col': 'speaker_name',
        'account_col': 'payment_account',
        'approval_code_col': 'approval_code',
        'amount_col': 'approved_fee',
        'labels': {
            'unknown': 'Unknown Speaker',
            'account': 'Account Mismatch',
            'invalid': 'Invalid Approval Code',
            'ownership': 'Speaker Mismatch',
            'amount': 'Fee Mismatch'
        }
    }
    
    # Example: Shift claims (with crosswalk indirection)
    SHIFT_CONFIG = {
        'registry_path': '/root/clinician_directory.xlsx',
        'crosswalk_path': '/root/shift_crosswalk.csv',  # maps SHIFT-A1 -> INT-5101
        'approvals_path': '/root/shift_authorizations.csv',  # INT-5101 -> {pay, clinician_id}
        'output_path': '/root/shift_claim_flags.json',
        'use_crosswalk': True,
        'entity_id_col': 'clinician_id',
        'entity_name_col': 'clinician_name',
        'account_col': 'payout_account',
        'external_code_col': 'shift_ref',  # in crosswalk
        'internal_code_col': 'shift_code_internal',  # in crosswalk and approvals
        'approval_code_col': 'shift_code_internal',  # in approvals
        'amount_col': 'approved_pay',
        'labels': {
            'unknown': 'Unknown Clinician',
            'account': 'Payout Account Mismatch',
            'invalid': 'Invalid Shift Code',
            'invalid_internal': 'Invalid Internal Code',
            'ownership': 'Clinician Mismatch',
            'amount': 'Pay Amount Mismatch'
        }
    }
    
    # SELECT CONFIG
    CONFIG = EXPENSE_CONFIG  # or HONORARIUM_CONFIG or SHIFT_CONFIG
    
    # Load reference data
    entities = load_registry(
        CONFIG['registry_path'],
        id_col=CONFIG['entity_id_col'],
        name_col=CONFIG['entity_name_col'],
        account_col=CONFIG['account_col']
    )
    approvals = load_approvals(
        CONFIG['approvals_path'],
        code_col=CONFIG['approval_code_col'],
        amount_col=CONFIG['amount_col'],
        entity_col=CONFIG['entity_id_col']
    )
    
    crosswalk = None
    if CONFIG.get('use_crosswalk'):
        crosswalk = load_crosswalk(
            CONFIG['crosswalk_path'],
            external_col=CONFIG['external_code_col'],
            internal_col=CONFIG['internal_code_col']
        )
    
    # TODO: Extract requests from PDF - populate this list
    # Each request needs: entity_name, requested_amount, account, approval_code (external_code if crosswalk), page_number
    requests = []
    
    # Validate and collect violations
    violations = []
    for req in requests:
        reason = validate_request(req, entities, approvals,
                                  crosswalk=crosswalk,
                                  unknown_label=CONFIG['labels']['unknown'],
                                  account_label=CONFIG['labels']['account'],
                                  invalid_ref_label=CONFIG['labels']['invalid'],
                                  invalid_internal_label=CONFIG['labels'].get('invalid_internal', CONFIG['labels']['invalid']),
                                  ownership_label=CONFIG['labels']['ownership'],
                                  amount_label=CONFIG['labels']['amount'])
        if reason:
            violations.append({
                'page_number': req.get('page_number'),
                'entity_name': req['entity_name'],
                'requested_amount': req['requested_amount'],
                'account': req['account'],
                'approval_code': req['approval_code'],
                'reason': reason
            })
    
    with open(CONFIG['output_path'], 'w') as f:
        json.dump(violations, f, indent=2)
    
    print(f"Found {len(violations)} violations, written to {CONFIG['output_path']}")

if __name__ == '__main__':
    main()
