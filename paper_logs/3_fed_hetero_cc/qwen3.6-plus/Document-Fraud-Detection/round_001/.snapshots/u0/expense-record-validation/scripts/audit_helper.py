#!/usr/bin/env python3
"""Reusable helper for cross-referencing expense claims against directories and approvals."""
import pandas as pd
import json
import sys
from difflib import SequenceMatcher

def fuzzy_match(name, candidates, threshold=0.85):
    """Return best match if similarity >= threshold, else None."""
    best_score, best_match = 0, None
    for c in candidates:
        score = SequenceMatcher(None, str(name).lower(), str(c).lower()).ratio()
        if score > best_score:
            best_score, best_match = score, c
    return best_match if best_score >= threshold else None

def run_audit(claims_df, dir_df, approvals_df, output_path="flagged_claims.json"):
    """
    Validates claims against directory and approvals.
    Expects columns:
      claims: ['page', 'name', 'amount', 'account', 'trip_id']
      dir: ['employee_id', 'employee_name', 'bank_account']
      approvals: ['trip_id', 'approved_amount', 'employee_id']
    """
    dir_map = {row['employee_name']: row for _, row in dir_df.iterrows()}
    dir_names = list(dir_map.keys())
    appr_map = {row['trip_id']: row for _, row in approvals_df.iterrows()}

    flagged = []
    for _, claim in claims_df.iterrows():
        match_name = fuzzy_match(claim['name'], dir_names)
        if not match_name:
            flagged.append({**claim.to_dict(), 'reason': 'Unknown Employee'})
            continue

        emp = dir_map[match_name]
        if str(claim['account']).strip() != str(emp['bank_account']).strip():
            flagged.append({**claim.to_dict(), 'reason': 'Account Mismatch'})
            continue

        trip = appr_map.get(str(claim['trip_id']).strip())
        if not trip:
            flagged.append({**claim.to_dict(), 'reason': 'Invalid Trip ID'})
            continue

        if abs(float(claim['amount']) - float(trip['approved_amount'])) > 0.01:
            flagged.append({**claim.to_dict(), 'reason': 'Amount Mismatch'})
            continue

        if str(trip['employee_id']).strip() != str(emp['employee_id']).strip():
            flagged.append({**claim.to_dict(), 'reason': 'Traveler Mismatch'})
            continue

    with open(output_path, 'w') as f:
        json.dump(flagged, f, indent=2)
    print(f"Flagged {len(flagged)} claims. Saved to {output_path}")
    return flagged

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: audit_helper.py <claims_csv> <dir_xlsx> <approvals_csv> [output_json]")
        sys.exit(1)

    claims = pd.read_csv(sys.argv[1])
    directory = pd.read_excel(sys.argv[2])
    approvals = pd.read_csv(sys.argv[3])
    out = sys.argv[4] if len(sys.argv) > 4 else "flagged_claims.json"

    run_audit(claims, directory, approvals, out)