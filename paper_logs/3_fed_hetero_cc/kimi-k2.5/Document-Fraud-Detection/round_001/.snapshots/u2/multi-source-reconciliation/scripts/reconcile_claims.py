#!/usr/bin/env python3
"""
Template for multi-source claim validation.
Customize DATA_PATHS and CLAIM_EXTRACTOR for your task.
"""

import json
import pandas as pd
from typing import Dict, List, Any, Optional

def load_employees(path: str) -> Dict[str, Dict]:
    """Load employee directory from Excel."""
    df = pd.read_excel(path)
    employees = {}
    for _, row in df.iterrows():
        eid = str(row['employee_id']).strip()
        employees[eid] = {
            'name': str(row['employee_name']).strip(),
            'bank_account': str(row['bank_account']).strip(),
            'department': str(row.get('department_code', '')).strip()
        }
    return employees

def load_approvals(path: str) -> Dict[str, Dict]:
    """Load trip approvals from CSV."""
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

def find_employee_by_name(name: str, employees: Dict) -> Optional[str]:
    """Find employee_id by name with fuzzy matching (edit distance ≤ 1)."""
    norm = normalize_name(name)
    
    # Exact match first
    for eid, emp in employees.items():
        if normalize_name(emp['name']) == norm:
            return eid
    
    # Fuzzy match
    best_match = None
    best_dist = float('inf')
    for eid, emp in employees.items():
        dist = edit_distance(norm, normalize_name(emp['name']))
        if dist < best_dist:
            best_dist = dist
            best_match = eid
    
    if best_dist <= 1 and len(norm) > 5:
        return best_match
    return None

def validate_claim(claim: Dict, employees: Dict, approvals: Dict) -> Optional[str]:
    """
    Validate a claim. Returns reason string if invalid, None if valid.
    
    Violation priority: Unknown Employee → Account Mismatch → Invalid Trip → Traveler Mismatch → Amount Mismatch
    """
    emp_id = find_employee_by_name(claim['employee_name'], employees)
    
    # 1. Unknown Employee
    if emp_id is None:
        return "Unknown Employee"
    
    emp = employees[emp_id]
    
    # 2. Account Mismatch
    if claim.get('bank_account') != emp['bank_account']:
        return "Account Mismatch"
    
    trip_id = claim.get('trip_id')
    
    # 3. Invalid Trip ID
    if trip_id not in approvals:
        return "Invalid Trip ID"
    
    trip = approvals[trip_id]
    
    # 4. Traveler Mismatch
    if trip['employee_id'] != emp_id:
        return "Traveler Mismatch"
    
    # 5. Amount Mismatch (tolerance: $0.01)
    if abs(claim.get('claimed_amount', 0) - trip['amount']) > 0.01:
        return "Amount Mismatch"
    
    return None

def main():
    # CONFIGURE THESE PATHS
    DATA_PATHS = {
        'employees': '/root/employee_directory.xlsx',
        'approvals': '/root/trip_approvals.csv',
        'claims': '/root/expense_claims.pdf',  # Extract manually or with PDF parser
        'output': '/root/expense_alerts.json'
    }
    
    # Load reference data
    employees = load_employees(DATA_PATHS['employees'])
    approvals = load_approvals(DATA_PATHS['approvals'])
    
    # TODO: Extract claims from PDF - populate this list
    # Each claim needs: employee_name, claimed_amount, bank_account, trip_id, claim_page_number
    claims = []
    
    # Validate and collect violations
    violations = []
    for claim in claims:
        reason = validate_claim(claim, employees, approvals)
        if reason:
            violations.append({
                'claim_page_number': claim.get('page_number'),
                'employee_name': claim['employee_name'],
                'claimed_amount': claim['claimed_amount'],
                'bank_account': claim['bank_account'],
                'trip_id': claim['trip_id'],
                'reason': reason
            })
    
    with open(DATA_PATHS['output'], 'w') as f:
        json.dump(violations, f, indent=2)
    
    print(f"Found {len(violations)} violations, written to {DATA_PATHS['output']}")

if __name__ == '__main__':
    main()