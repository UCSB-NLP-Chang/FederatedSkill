#!/usr/bin/env python3
"""
Resolve patient counts from override CSV with approval workflow.

Usage:
    from resolve_patients import load_overrides, resolve_patient_count
    
    overrides = load_overrides('patient_overrides.csv')
    count = resolve_patient_count(overrides, 'HINF-ALPHA')
"""

import csv
from typing import Optional


def load_overrides(path: str) -> list[dict]:
    """Load patient overrides CSV."""
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def resolve_patient_count(overrides: list[dict], therapy_code: str) -> Optional[int]:
    """
    Resolve patient count for therapy_code using approval workflow:
    - Filter to therapy_code
    - Filter to status='approved' only
    - Select highest revision number
    - Return active_patients as int
    
    Returns None if no approved entry found.
    """
    # Filter to target therapy
    therapy_rows = [
        row for row in overrides 
        if row.get('therapy_code') == therapy_code
    ]
    
    if not therapy_rows:
        return None
    
    # Filter to approved status only
    approved = [
        row for row in therapy_rows 
        if row.get('status') == 'approved'
    ]
    
    if not approved:
        return None
    
    # Select highest revision
    highest = max(approved, key=lambda r: int(r.get('revision', 0)))
    
    return int(highest.get('active_patients', 0))


def resolve_all_patients(overrides: list[dict], therapy_codes: list[str]) -> dict[str, Optional[int]]:
    """Resolve patient counts for multiple therapy codes."""
    return {
        code: resolve_patient_count(overrides, code) 
        for code in therapy_codes
    }


def main():
    """CLI: python3 resolve_patients.py <overrides.csv> <therapy_code>"""
    import sys
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <overrides.csv> <therapy_code>")
        sys.exit(1)
    
    overrides = load_overrides(sys.argv[1])
    count = resolve_patient_count(overrides, sys.argv[2])
    
    if count is None:
        print(f"No approved patient count found for {sys.argv[2]}")
        sys.exit(1)
    
    print(f"Resolved patients for {sys.argv[2]}: {count}")


if __name__ == '__main__':
    main()